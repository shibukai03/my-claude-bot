import logging
import sys
import os
from datetime import datetime, timezone, timedelta
from analyzer.ai_analyzer import AIAnalyzer
from database.sheets_manager import SheetsManager
# ※ scrapersモジュール等は既存のものを使用

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 60)
    logger.info("映像案件スクレイピング v1.2（Sonnet全件精査版）")
    logger.info("=" * 60)

    try:
        # 既存スクレイパー等のインポート
        from scrapers.direct_scraper import search_all_prefectures_direct
        from scrapers.content_extractor import ContentExtractor
        
        analyzer = AIAnalyzer()
        # 環境変数から情報を取得
        creds = json.loads(os.environ["GOOGLE_CREDENTIALS_JSON"]) # 設定に合わせて調整
        sheets_manager = SheetsManager(os.environ["SPREADSHEET_ID"], creds)
        extractor = ContentExtractor()

        jst = timezone(timedelta(hours=9))
        today = datetime.now(jst).date()
        sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v12")

        # 1. シートのリセットと準備
        worksheet = sheets_manager.prepare_v12_sheet(sheet_name)

        # 2. 全都道府県からリンクを収集
        prefecture_results = search_all_prefectures_direct()
        all_urls = [r for results in prefecture_results.values() for r in results]
        
        total_found = len(all_urls)
        logger.info(f">>> 発見した総リンク数: {total_found} 件。全件精査を開始します。")

        final_valid_projects = []
        processed_urls = set()

        # 3. 解析ループ（全件）
        for url_data in all_urls:
            url = url_data['url']
            if url in processed_urls: continue
            processed_urls.add(url)
            
            content = extractor.extract(url)
            if not content: continue
            
            analysis = analyzer.analyze_project(content)
            
            if analysis and analysis['label'] in ["A", "B"]:
                # ゲート判定（参加申込締切が過ぎていないか）
                d_app = analysis.get('deadline_app')
                if d_app and d_app != "不明":
                    try:
                        if datetime.strptime(d_app, '%Y-%m-%d').date() < today:
                            logger.info(f"⏩ 期限切れ(申込終了)のため除外: {analysis['title']}")
                            continue
                    except: pass
                
                analysis['source_url'] = url
                final_valid_projects.append(analysis)
                logger.info(f"✅ 合格[{analysis['label']}]: {analysis['title']}")

        # 4. 保存と集計
        added = sheets_manager.append_projects(worksheet, final_valid_projects)
        
        logger.info("=" * 60)
        logger.info("✨ 調査完了サマリー ✨")
        logger.info(f"1. 総発見リンク: {total_found} 件")
        logger.info(f"2. AI精査数: {len(processed_urls)} 件")
        logger.info(f"3. スプレッドシート追加: {added} 件")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"システムエラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
