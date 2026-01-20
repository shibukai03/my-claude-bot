import logging
import sys
import os
import json
from datetime import datetime, timezone, timedelta
from analyzer.ai_analyzer import AIAnalyzer
from database.sheets_manager import SheetsManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 60)
    logger.info("映像案件スクレイピング v1.2（指示書完全準拠版）")
    logger.info("=" * 60)

    try:
        # スクリーパー等のインポート
        from scrapers.direct_scraper import search_all_prefectures_direct
        from scrapers.content_extractor import ContentExtractor
        
        analyzer = AIAnalyzer()
        # 環境変数から設定取得
        spreadsheet_id = os.environ["SPREADSHEET_ID"]
        # 環境変数名が設定により異なる可能性があるため注意
        creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON") or os.environ.get("GCP_SERVICE_ACCOUNT_JSON")
        creds = json.loads(creds_json)
        
        sheets_manager = SheetsManager(spreadsheet_id, creds)
        extractor = ContentExtractor()

        jst = timezone(timedelta(hours=9))
        now_jst = datetime.now(jst)
        today = now_jst.date()
        # 新しい項目名でシートを作成
        sheet_name = now_jst.strftime("映像案件_%Y年%m月_v12")

        # 1. シートの準備
        worksheet = sheets_manager.prepare_v12_sheet(sheet_name)
        if not worksheet:
            logger.error("シートの作成に失敗しました")
            return

        # 2. 全リンクの収集
        prefecture_results = search_all_prefectures_direct()
        all_urls = [r for results in prefecture_results.values() for r in results]
        
        total_found = len(all_urls)
        logger.info(f">>> 発見した総リンク数: {total_found} 件。全件精査を開始します。")

        final_valid_projects = []
        processed_urls = set()

        # 3. 全件解析ループ
        for url_data in all_urls:
            url = url_data['url']
            if url in processed_urls: continue
            processed_urls.add(url)
            
            content = extractor.extract(url)
            if not content: continue
            
            analysis = analyzer.analyze_project(content)
            
            if analysis and analysis.get('label') in ["A", "B"]:
                # 指示書3.3項に基づく「募集中（ゲート判定）」
                d_app = analysis.get('deadline_app')
                if d_app and d_app != "不明":
                    try:
                        if datetime.strptime(d_app, '%Y-%m-%d').date() < today:
                            logger.info(f"⏩ 期限切れにつき除外: {analysis['title']}")
                            continue
                    except: pass
                
                analysis['source_url'] = url
                final_valid_projects.append(analysis)
                logger.info(f"✅ 合格[{analysis['label']}]: {analysis['title']}")

        # 4. 書き込みとサマリー
        added = sheets_manager.append_projects(worksheet, final_valid_projects)
        
        logger.info("=" * 60)
        logger.info("✨ 調査完了サマリー ✨")
        logger.info(f"1. 発見した総リンク数: {total_found} 件")
        logger.info(f"2. AI精査数: {len(processed_urls)} 件")
        logger.info(f"3. スプレッドシート追加: {added} 件")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"システムエラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
