import logging
import sys
import os
import json
import time
from datetime import datetime, timezone, timedelta
from analyzer.ai_analyzer import AIAnalyzer
from database.sheets_manager import SheetsManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 60)
    logger.info("映像案件スクレイピング v1.2 [動作確認モード：期限フィルターOFF]")
    logger.info("=" * 60)

    try:
        from scrapers.direct_scraper import search_all_prefectures_direct
        from scrapers.content_extractor import ContentExtractor
        
        analyzer = AIAnalyzer()
        spreadsheet_id = os.environ.get("SPREADSHEET_ID")
        creds_json = os.environ.get("GCP_SERVICE_ACCOUNT")
        creds = json.loads(creds_json)
        sheets_manager = SheetsManager(spreadsheet_id, creds)
        extractor = ContentExtractor()

        jst = timezone(timedelta(hours=9))
        sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_検証")

        worksheet = sheets_manager.prepare_v12_sheet(sheet_name)

        prefecture_results = search_all_prefectures_direct()
        all_urls = [r for results in prefecture_results.values() for r in results]
        
        total_found = len(all_urls)
        logger.info(f">>> 総リンク数 {total_found} 件の解析を開始します。")

        final_valid_projects = []
        processed_count = 0
        added_count = 0

        for url_data in all_urls:
            url = url_data['url']
            processed_count += 1
            
            if processed_count % 5 == 0:
                logger.info(f"--- 進捗: {processed_count} / {total_found} ---")

            try:
                content = extractor.extract(url)
                if not content: continue
                
                analysis = analyzer.analyze_project(content)
                
                # AまたはB判定なら、期限に関わらず一旦すべて保存する（検証のため）
                if analysis and analysis.get('label') in ["A", "B"]:
                    analysis['source_url'] = url
                    final_valid_projects.append(analysis)
                    added_count += 1
                    logger.info(f"✅ 検知: {analysis['title']} (判定:{analysis['label']})")
                    
                    if len(final_valid_projects) >= 3: # 3件ごとに書き込み
                        sheets_manager.append_projects(worksheet, final_valid_projects)
                        final_valid_projects = []
                
            except Exception as e:
                logger.error(f"解析スキップ: {url} - {e}")
                continue

        if final_valid_projects:
            sheets_manager.append_projects(worksheet, final_valid_projects)
        
        logger.info(f"精査数: {processed_count} 件 / シート追加: {added_count} 件")

    except Exception as e:
        logger.error(f"システムエラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
