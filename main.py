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
    logger.info("映像案件スクレイピング v1.21 [長野県案件復活・完全版]")
    logger.info("=" * 60)
    
    try:
        from scrapers.direct_scraper import search_all_prefectures_direct
        from scrapers.content_extractor import ContentExtractor
        
        analyzer = AIAnalyzer()
        sheets_manager = SheetsManager(os.environ["SPREADSHEET_ID"], json.loads(os.environ["GCP_SERVICE_ACCOUNT"]))
        extractor = ContentExtractor()
        jst = timezone(timedelta(hours=9))
        today = datetime.now(jst).date()

        logger.info("【ステップ1】全国リンク収集...")
        prefecture_results = search_all_prefectures_direct()
        all_tasks = [{"pref": p, **r} for p, rs in prefecture_results.items() for r in rs]
        
        final_projects = []
        seen_titles = set()
        
        logger.info("【ステップ2】案件の極限選別（100%令和8年度・募集中のみ）...")
        for i, task in enumerate(all_tasks, 1):
            url = task['url']
            title_raw = task['title']

            # --- 🛡️ 門番1：ドメイン遮断 ---
            if re.search(r"youtube\.com|youtu\.be|facebook\.com|instagram\.com|x\.com|twitter\.com", url):
                continue

            # --- 🛡️ 門番2：タイトルによる「絶対除外」ルール ---
            if re.search(r"決定しました|選定結果|選定しました|落札|入札結果|審査結果|候補者の決定|公表|事後報告|更新しました|放映中|配信中", title_raw):
                continue
            if re.search(r"採用|職員|薬剤師|警察官|教員|看護師|ガイダンス|試験|相談会", title_raw):
                continue
            if re.search(r"令和[4-7]|R[4-7]|202[2-5]", title_raw) and "令和8" not in title_raw:
                continue

            # --- 🛡️ 門番3：【改善】長野県案件を拾うためのキーワード緩和 ---
            # 「制作」「撮影」「業務」も入り口として認めます
            if not re.search(r"募集|委託|入札|プロポーザル|コンペ|公募|企画提案|制作|撮影|業務", title_raw):
                continue

            if i % 20 == 0: logger.info(f"進捗: {i}/{len(all_tasks)} 件完了")
            
            content_data = extractor.extract(url)
            if not content_data: continue
            
            analysis = analyzer.analyze_single(title_raw, content_data['content'], url)
            if not analysis: continue
            
            # --- 🛡️ 門番4：AI回答検閲 ---
            if analysis.get('label') not in ["A", "B"]: continue
            title = analysis.get('title', '無題')
            if title in seen_titles: continue

            full_text = f"{title} {analysis.get('evidence','')} {analysis.get('memo','')}"

            if re.search(r"ではありません|ではない|過去の案件|終了しています|選定済|令和7年度?の案件", full_text):
                continue

            # 令和8年度(2026)の証拠チェック
            if "令和8" not in full_text and "2026" not in full_text:
                continue

            # 期限切れチェック
            deadline_str = analysis.get('deadline_prop', '不明')
            if deadline_str == "不明": deadline_str = analysis.get('deadline_apply', '不明')
            if deadline_str != "不明":
                match = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', deadline_str)
                if match:
                    d_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3))).date()
                    if d_date < today: continue

            # --- ✨ 最終合格 ---
            analysis.update({'prefecture': task['pref']})
            final_projects.append(analysis)
            seen_titles.add(title)
            logger.info(f"🎯 厳選案件を捕捉: {title}")
            time.sleep(0.1)

        if final_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v16")
            sheets_manager.append_projects(sheets_manager.prepare_v12_sheet(sheet_name), final_projects)
            logger.info(f"✨ 完了！ 真の有効案件 {len(final_projects)}件を追加しました")
        else:
            logger.warning("⚠️ 現在募集中の有効な案件は見つかりませんでした")
            
    except Exception as e:
        logger.error(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
