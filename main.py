import logging
import os
import json
import time
import re
from datetime import datetime, timezone, timedelta
from analyzer.ai_analyzer import AIAnalyzer
from database.sheets_manager import SheetsManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 60)
    logger.info("映像案件スクレイピング v1.26 [ゾンビ案件排除・最終完成版]")
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
        
        logger.info("【ステップ2】案件選別（応募期限を厳格にチェック）...")
        for i, task in enumerate(all_tasks, 1):
            url = task['url']
            title_raw = task['title']

            if re.search(r"youtube\.com|youtu\.be|facebook\.com|instagram\.com|x\.com|twitter\.com", url): continue

            # --- 🛡️ 門番1：タイトルの「冷徹な排除」 (決定・終了の気配を察知) ---
            if re.search(r"決定|公表|選定|落札|結果|審査|報告|実績|成功|達成|公開|完了|制作しました|放映中|配信中|終了", title_raw):
                continue
            if re.search(r"採用|職員|薬剤師|警察|教員|看護|医師|試験|相談|個人|講習", title_raw):
                continue

            # --- 🛡️ 門番2：【救済】本物を逃さないキーワード ---
            if not re.search(r"募集|委託|入札|プロポーザル|コンペ|公募|企画提案|制作|作成|撮影|業務|動画|PR|プロモーション", title_raw):
                continue

            if i % 20 == 0: logger.info(f"進捗: {i}/{len(all_tasks)} 件完了")
            
            content_data = extractor.extract(url)
            if not content_data: continue
            raw_text = content_data['content']

            # --- 🛡️ 門番3：本文の年度検閲 (2026年または令和8年の気配を確認) ---
            # 1月現在なので、令和7年度の予算で「令和8年の仕事」を募集しているケースも多いため、R7とR8の両方を視野に入れます
            if not re.search(r"令和[78]|R[78]|202[56]", raw_text):
                continue

            analysis = analyzer.analyze_single(title_raw, raw_text, url)
            if not analysis: continue
            
            # --- 🛡️ 門番4：AI回答の「期限」を徹底検閲 ---
            if analysis.get('label') not in ["A", "B"]: continue
            title = analysis.get('title', '無題')
            if title in seen_titles: continue

            evidence = analysis.get('evidence','')
            memo = analysis.get('memo','')
            full_ans = f"{title} {evidence} {memo}"

            # ① AIが「期限切れ」や「募集終了」を認めている場合
            if re.search(r"終了しています|期限が過ぎて|過去の案件", full_ans):
                continue

            # ② 応募締切の厳格チェック (ゾンビ案件対策)
            # 参加申込と提案書のどちらか一方が今日以降であること
            deadline_date = None
            d1 = analysis.get('deadline_apply', '不明')
            d2 = analysis.get('deadline_prop', '不明')
            
            dates_to_check = []
            for d_str in [d1, d2]:
                if d_str and d_str != "不明":
                    m = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', d_str)
                    if m:
                        dates_to_check.append(datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date())
            
            if dates_to_check:
                # 見つかったすべての日付が今日より前なら「期限切れ」として捨てる
                if all(d < today for d in dates_to_check):
                    logger.info(f"⌛ 期限切れ(ゾンビ)除外: {title}")
                    continue
            else:
                # 日付が一切不明で、かつ本文に「令和8年」の募集の気配がないものも怪しいので捨てる
                if "令和8" not in full_ans and "2026" not in full_ans:
                    continue

            # --- ✨ 最終合格：2026年に向けた「今、応募できる」真の案件 ---
            analysis.update({'prefecture': task['pref']})
            final_projects.append(analysis)
            seen_titles.add(title)
            logger.info(f"🎯 有効案件を捕捉: {title}")
            time.sleep(0.1)

        if final_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v16")
            sheets_manager.append_projects(sheets_manager.prepare_v12_sheet(sheet_name), final_projects)
            logger.info(f"✨ 完了！ 真の有効案件 {len(final_projects)}件を追加しました")
        else:
            logger.warning("⚠️ 募集中の有効案件は見つかりませんでした")
            
    except Exception as e:
        logger.error(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
