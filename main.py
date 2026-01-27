import logging
import os
import json
import time
import re
import unicodedata
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor # 🆕 並列処理の司令塔
from analyzer.ai_analyzer import AIAnalyzer
from database.sheets_manager import SheetsManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- 🆕 作業員（1件の案件を徹底的に調べる関数） ---
def process_task(task, extractor, analyzer, today):
    url = task['url']
    title_raw = task['title']
    pref = task['pref']

    # 🛡️ 門番1：SNS除外 ＆ タイトルの「冷徹な排除」
    if re.search(r"youtube\.com|youtu\.be|facebook\.com|instagram\.com|x\.com|twitter\.com", url): return None
    if re.search(r"決定|公表|選定|落札|結果|審査|報告|実績|成功|達成|公開|完了|制作しました|放映中|配信中|終了", title_raw):
        return None
    if re.search(r"採用|職員|薬剤師|警察|教員|看護|医師|試験|相談|個人|講習", title_raw):
        return None

    # 🛡️ 門番2：クリエイティブ案件キーワード（これがないとAIに送らない）
    if not re.search(r"募集|委託|入札|プロポーザル|コンペ|公募|企画提案|制作|作成|撮影|業務|動画|PR|プロモーション", title_raw):
        return None

    # ページ内容の取得
    content_data = extractor.extract(url)
    if not content_data: return None
    
    # 全角半角の正規化
    normalized_text = unicodedata.normalize('NFKC', content_data['content'])

    # 🛡️ 門番3：年度検閲（令和8年度を救済）
    if not re.search(r"令和[789]|R[789]|202[567]", normalized_text):
        return None

    # AI解析 (Haiku 4.5)
    analysis = analyzer.analyze_single(title_raw, normalized_text, url)
    if not analysis: return None
    
    # 🛡️ 門番4：AI回答の最終精査
    if analysis.get('label') not in ["A", "B"]: return None
    
    # ① 期限切れチェック (ゾンビ案件を数学的に除外)
    dates_to_check = []
    for key in ['deadline_apply', 'deadline_prop']:
        d_str = analysis.get(key, '不明')
        if d_str and d_str != "不明":
            m = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', d_str)
            if m: dates_to_check.append(datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date())
    
    if dates_to_check and all(d < today for d in dates_to_check):
        # logger.info(f"⌛ 期限切れ除外: {title_raw}") # 並列時はログが混ざるので抑制
        return None

    # ② 令和8年度(2026)の案件であることを最終確認
    evidence = analysis.get('evidence','')
    memo = analysis.get('memo','')
    full_ans = f"{title_raw} {evidence} {memo}"
    if re.search(r"令和7年度?の案件|令和7年度予算のみ", memo) and "令和8" not in full_ans:
        return None

    # すべての関門を突破！
    analysis.update({'prefecture': pref})
    return analysis

# --- メインエンジン ---
def main():
    logger.info("=" * 60)
    logger.info("映像案件スクレイピング v1.29 [並列高速・全門番継承版]")
    logger.info("=" * 60)
    
    try:
        from scrapers.direct_scraper import search_all_prefectures_direct
        from scrapers.content_extractor import ContentExtractor
        
        analyzer = AIAnalyzer()
        sheets_manager = SheetsManager(os.environ["SPREADSHEET_ID"], json.loads(os.environ["GCP_SERVICE_ACCOUNT"]))
        extractor = ContentExtractor()
        jst = timezone(timedelta(hours=9))
        today = datetime.now(jst).date()

        logger.info("【ステップ1】全国自治体サイトから最新リンクを収集...")
        prefecture_results = search_all_prefectures_direct()
        all_tasks = [{"pref": p, **r} for p, rs in prefecture_results.items() for r in rs]
        
        logger.info(f"【ステップ2】案件選別（10件並列実行中... / 全 {len(all_tasks)}件）")
        
        final_projects = []
        seen_titles = set()

        # 🆕 並列実行の魔法：10人の作業員が同時に process_task を実行します
        with ThreadPoolExecutor(max_workers=10) as executor:
            # mapやsubmitを使って一気に仕事を投げる
            futures = [executor.submit(process_task, task, extractor, analyzer, today) for task in all_tasks]
            
            for future in futures:
                result = future.result()
                if result:
                    title = result.get('title', '無題')
                    if title not in seen_titles:
                        final_projects.append(result)
                        seen_titles.add(title)
                        logger.info(f"🎯 真の案件を捕捉: {title}")

        if final_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v16")
            sheets_manager.append_projects(sheets_manager.prepare_v12_sheet(sheet_name), final_projects)
            logger.info(f"✨ 完了！ 真の有効案件 {len(final_projects)}件を追加しました")
        else:
            logger.warning("⚠️ 現在募集中の有効案件は見つかりませんでした")
            
    except Exception as e:
        logger.error(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
