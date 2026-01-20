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
    logger.info("映像案件スクレイピング v1.2（判定ロジック強化版）")
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

        worksheet = sheets_manager.prepare_v12_sheet(sheet_name)

        prefecture_results = search_all_prefectures_direct()
        all_urls = [r for results in prefecture_results.values() for r in results]
        
        total_found = len(all_urls)
        logger.info(f">>> 発見した総リンク数: {total_found} 件。AI精査を開始します。")

        final_valid_projects = []
        processed_urls = set()

        for url_data in all_urls:
            url = url_data['url']
            if url in processed_urls: continue
            processed_urls.add(url)
            
            content = extractor.extract(url)
            if not content:
                # 抽出失敗のログ
                continue
            
            analysis = analyzer.analyze_project(content)
            
            if analysis:
                label = analysis.get('label', 'C')
                if label in ["A", "B"]:
                    # ゲート判定
                    d_app = analysis.get('deadline_app')
                    if d_app and d_app != "不明":
                        try:
                            if datetime.strptime(d_app, '%Y-%m-%d').date() < today:
                                logger.info(f"⏩ 期限切れにつき除外: {analysis['title']}")
                                continue
                        except: pass
                    
                    analysis['source_url'] = url
                    final_valid_projects.append(analysis)
                    logger.info(f"✅ 合格[{label}]: {analysis['title']}")
                else:
                    # Cラベルの場合も、何が除外されたか軽くログに出す（確認用）
                    logger.info(f"➖ 除外[C]: {analysis.get('title', url[:30])}")
            else:
                logger.info(f"➖ スキップ(解析不能): {url[:30]}...")

        # 書き込み
        if final_valid_projects:
            added = sheets_manager.append_projects(worksheet, final_valid_projects)
            logger.info(f"スプレッドシートに {added} 件追加しました。")
        
        logger.info("=" * 60)
        logger.info("✨ 全ての行程が完了しました ✨")
        logger.info(f"最終追加件数: {len(final_valid_projects)} 件")

    except Exception as e:
        logger.error(f"システムエラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
