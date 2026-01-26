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
    logger.info("映像案件スクレイピング v1.14 [Haiku・2026年以降～未来対応版]")
    logger.info("=" * 60)
    
    try:
        from scrapers.direct_scraper import search_all_prefectures_direct
        from scrapers.content_extractor import ContentExtractor
        
        analyzer = AIAnalyzer()
        sheets_manager = SheetsManager(os.environ["SPREADSHEET_ID"], json.loads(os.environ["GCP_SERVICE_ACCOUNT"]))
        extractor = ContentExtractor()
        jst = timezone(timedelta(hours=9))
        today = datetime.now(jst).date()

        # 1. リンク収集
        logger.info("【ステップ1】全国リンク収集開始...")
        prefecture_results = search_all_prefectures_direct()
        all_tasks = [{"pref": p, **r} for p, rs in prefecture_results.items() for r in rs]
        logger.info(f"✅ {len(all_tasks)}件のリンクを取得")
        
        # 2. 解析
        final_projects = []
        seen_titles = set()
        
        logger.info("【ステップ2】重要コンテンツ抽出とAI解析（リアルタイム）を開始...")
        for i, task in enumerate(all_tasks, 1):
            if i % 10 == 0: logger.info(f"進捗: {i}/{len(all_tasks)} 件完了")
            
            content_data = extractor.extract(task['url'])
            if not content_data: continue
            
            analysis = analyzer.analyze_single(task['title'], content_data['content'], task['url'])
            if not analysis: continue
            
            # --- 🛡️ 強化版：未来対応フィルター ---
            
            # 1. ラベルチェック
            if analysis.get('label') not in ["A", "B"]: continue
            
            title = analysis.get('title', '無題')
            if title in seen_titles: continue

            # 2. 年度検閲 (AIの回答すべてを繋げてスキャン)
            evidence = analysis.get('evidence', '')
            memo = analysis.get('memo', '')
            full_check_text = f"{title} {evidence} {memo}"
            
            # 【重要】令和8年(2026)以降の文字があるか？（9年、10年、2027年もOK）
            is_future_year = re.search(r"令和([8-9]|[1-9]\d)|202[6-9]|20[3-9]\d", full_check_text)
            # 【重要】過去の年度が含まれているか？
            is_past_year = re.search(r"令和[4-7]|R[4-7]|202[2-5]", full_check_text)
            
            # 過去の年度が書いてあり、かつ未来の年度が「併記されていない」場合は除外
            # (R7の振り返り動画などを弾き、R7〜R8にまたがる案件は残すため)
            if is_past_year and not is_future_year:
                logger.info(f"⏩ 過去案件として除外: {title}")
                continue

            # 3. 期限切れ排除 (今日以前の日付なら捨てる)
            deadline_str = analysis.get('deadline_prop', '不明')
            if deadline_str == "不明": deadline_str = analysis.get('deadline_apply', '不明')

            if deadline_str != "不明":
                match = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', deadline_str)
                if match:
                    deadline_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3))).date()
                    if deadline_date < today:
                        logger.info(f"⌛ 期限切れ除外 ({deadline_date}): {title}")
                        continue

            # --- ✨ 合格 ---
            analysis.update({'prefecture': task['pref']})
            final_projects.append(analysis)
            seen_titles.add(title)
            logger.info(f"✨ 合格案件: {title}")
            time.sleep(0.2)

        # 3. 書き込み
        if final_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v16")
            sheets_manager.append_projects(sheets_manager.prepare_v12_sheet(sheet_name), final_projects)
            logger.info(f"✨ 完了！ {len(final_projects)}件をシートに追加")
        else:
            logger.warning("⚠️ 条件に合う新着案件なし")
            
    except Exception as e: logger.error(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
