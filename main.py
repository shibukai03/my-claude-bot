import logging
import os
import json
import time
import re
import unicodedata
from datetime import datetime, timezone, timedelta
from analyzer.ai_analyzer import AIAnalyzer
from database.sheets_manager import SheetsManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 60)
    logger.info("映像案件スクレイピング v1.28 [ゾンビ案件・完全封殺版]")
    logger.info("=" * 60)
    
    try:
        from scrapers.direct_scraper import search_all_prefectures_direct
        from scrapers.content_extractor import ContentExtractor
        
        analyzer = AIAnalyzer()
        sheets_manager = SheetsManager(os.environ["SPREADSHEET_ID"], json.loads(os.environ["GCP_SERVICE_ACCOUNT"]))
        extractor = ContentExtractor()
        jst = timezone(timedelta(hours=9))
        today = datetime.now(jst).date()

        logger.info("【ステップ1】全国リンク収集開始...")
        prefecture_results = search_all_prefectures_direct()
        all_tasks = [{"pref": p, **r} for p, rs in prefecture_results.items() for r in rs]
        
        final_projects = []
        seen_titles = set()
        
        logger.info("【ステップ2】案件選別（Haiku 4.5 × 日付自動検閲）...")
        for i, task in enumerate(all_tasks, 1):
            url = task['url']
            title_raw = task['title']

            if re.search(r"youtube\.com|youtu\.be|facebook\.com|instagram\.com|x\.com|twitter\.com", url): continue

            # --- 🛡️ 門番1：タイトルの「冷徹な排除」 ---
            if re.search(r"決定|公表|選定|落札|結果|審査|報告|実績|成功|達成|公開|完了|制作しました|放映中|配信中|終了", title_raw):
                continue
            if re.search(r"採用|職員|薬剤師|警察|教員|看護|医師|試験|相談|個人|講習", title_raw):
                continue

            # --- 🛡️ 門番2：許可キーワード ---
            if not re.search(r"募集|委託|入札|プロポーザル|コンペ|公募|企画提案|制作|作成|撮影|業務|動画|PR|プロモーション", title_raw):
                continue

            if i % 20 == 0: logger.info(f"進捗: {i}/{len(all_tasks)} 件完了")
            
            content_data = extractor.extract(url)
            if not content_data: continue
            
            # 全角半角の正規化
            normalized_text = unicodedata.normalize('NFKC', content_data['content'])

            # --- 🛡️ 門番3：年度検閲 ---
            if not re.search(r"令和[789]|R[789]|202[567]", normalized_text):
                continue

            # AI解析 (Haiku 4.5)
            analysis = analyzer.analyze_single(title_raw, normalized_text, url)
            if not analysis: continue
            
            # --- 🛡️ 門番4：AI回答の最終精査 ---
            if analysis.get('label') not in ["A", "B"]: continue
            title = analysis.get('title', '無題')
            if title in seen_titles: continue

            # ① 期限切れチェック (プログラムによる数学的除外)
            # AIが「仕事の納期」を締切に入れてきても、今日より前なら落とす
            dates_to_check = []
            for key in ['deadline_apply', 'deadline_prop']:
                d_str = analysis.get(key, '不明')
                if d_str and d_str != "不明":
                    m = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', d_str)
                    if m: dates_to_check.append(datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date())
            
            # 全ての日付が過去なら「期限切れ」とみなす
            if dates_to_check and all(d < today for d in dates_to_check):
                logger.info(f"⌛ 期限切れ除外: {title}")
                continue

            # ② 令和8年度(2026)の案件であることを最終確認
            evidence = analysis.get('evidence','')
            memo = analysis.get('memo','')
            full_ans = f"{title} {evidence} {memo}"
            if re.search(r"令和7年度?の案件|令和7年度予算のみ", memo) and "令和8" not in full_ans:
                continue

            # --- ✨ 最終合格 ---
            analysis.update({'prefecture': task['pref']})
            final_projects.append(analysis)
            seen_titles.add(title)
            logger.info(f"🎯 真の案件を捕捉: {title}")
            time.sleep(0.1)

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
