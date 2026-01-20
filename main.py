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
    logger.info("映像案件スクレイピング v1.2 [Step 3: 深層解析・長時間稼働版]")
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
        today = datetime.now(jst).date()
        sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v12")

        # シートの準備
        worksheet = sheets_manager.prepare_v12_sheet(sheet_name)

        # 1. 全リンクの収集
        prefecture_results = search_all_prefectures_direct()
        all_urls = [r for results in prefecture_results.values() for r in results]
        
        total_found = len(all_urls)
        logger.info(f">>> 総リンク数 {total_found} 件のディープ解析を開始します。")
        logger.info("※ 1件ずつPDFを全ページ精査するため、完了まで約1〜2時間かかります。")

        final_valid_projects = []
        processed_count = 0
        added_count = 0

        # 2. 全件解析ループ
        for url_data in all_urls:
            url = url_data['url']
            processed_count += 1
            
            # 進捗ログ（10件ごとに報告）
            if processed_count % 10 == 0:
                logger.info(f"--- 進捗報告: {processed_count} / {total_found} 件完了 ---")

            try:
                content = extractor.extract(url)
                if not content: continue
                
                analysis = analyzer.analyze_project(content)
                
                if analysis and analysis.get('label') in ["A", "B"]:
                    # ゲート判定（申込期限切れを弾く）
                    d_app = analysis.get('deadline_app')
                    if d_app and d_app != "不明":
                        try:
                            if datetime.strptime(d_app, '%Y-%m-%d').date() < today:
                                logger.info(f"⏩ 期限切れにつき除外: {analysis['title']}")
                                continue
                        except: pass
                    
                    analysis['source_url'] = url
                    final_valid_projects.append(analysis)
                    added_count += 1
                    logger.info(f"✅ 合格[{analysis['label']}]: {analysis['title']}")
                    
                    # 万が一のクラッシュに備え、5件溜まるごとにシートへ書き込む（堅牢化）
                    if len(final_valid_projects) >= 5:
                        sheets_manager.append_projects(worksheet, final_valid_projects)
                        final_valid_projects = [] # リストを空にする
                
            except Exception as e:
                logger.error(f"案件スキップ（個別エラー）: {url} - {e}")
                continue

        # 3. 残りのデータを書き込み
        if final_valid_projects:
            sheets_manager.append_projects(worksheet, final_valid_projects)
        
        logger.info("=" * 60)
        logger.info("✨ 深層解析パトロール完了 ✨")
        logger.info(f"精査数: {processed_count} 件 / スプレッドシート追加: {added_count} 件")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"システムエラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
