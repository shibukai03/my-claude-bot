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
    logger.info("映像案件スクレイピング v1.2 [本番運用モード：期限フィルターON]")
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

        # 日本時間を基準にする
        jst = timezone(timedelta(hours=9))
        now = datetime.now(jst)
        today = now.date()
        sheet_name = now.strftime("映像案件_%Y年%m月")

        # シートの準備（v1.2用のヘッダー）
        worksheet = sheets_manager.prepare_v12_sheet(sheet_name)

        # 全47都道府県の巡回（direct_scraper.py で設定した複数URLをスキャン）
        prefecture_results = search_all_prefectures_direct()
        
        # フラットなリストに変換
        all_urls = []
        for pref, results in prefecture_results.items():
            for res in results:
                res['pref'] = pref
                all_urls.append(res)
        
        total_found = len(all_urls)
        logger.info(f">>> 総リンク数 {total_found} 件のディープ解析を開始します。")

        final_valid_projects = []
        processed_count = 0
        added_count = 0

        for url_data in all_urls:
            url = url_data['url']
            processed_count += 1
            
            # 進捗ログ
            if processed_count % 5 == 0:
                logger.info(f"--- 進捗報告: {processed_count} / {total_found} 件完了 ---")

            try:
                # 1. コンテンツ抽出（HTML + PDF最大30ページ）
                content = extractor.extract(url)
                if not content:
                    continue
                
                # 2. AIによる深層解析
                analysis = analyzer.analyze_project(content)
                
                # 3. 判定フィルター
                if analysis and analysis.get('label') in ["A", "B"]:
                    
                    # 【重要】期限切れフィルター：今日以前の締切は除外
                    d_app = analysis.get('deadline_app')
                    if d_app and d_app != "不明":
                        try:
                            deadline_date = datetime.strptime(d_app, '%Y-%m-%d').date()
                            if deadline_date < today:
                                logger.info(f"⏩ 期限切れにつき除外: {analysis['title']} (締切:{d_app})")
                                continue
                        except Exception:
                            pass # 日付形式エラーの場合は念のため残す
                    
                    # 有効な案件として追加
                    analysis['source_url'] = url
                    analysis['prefecture'] = url_data.get('pref', '不明')
                    final_valid_projects.append(analysis)
                    added_count += 1
                    logger.info(f"✅ 検知: {analysis['title']} (判定:{analysis['label']} / 締切:{d_app or '不明'})")
                    
                    # 5件溜まったらスプレッドシートへ書き出し（タイムアウト対策）
                    if len(final_valid_projects) >= 5:
                        sheets_manager.append_projects(worksheet, final_valid_projects)
                        final_valid_projects = []
                
            except Exception as e:
                logger.error(f"解析エラー(スキップ): {url} - {e}")
                continue

        # 残りの案件を書き出し
        if final_valid_projects:
            sheets_manager.append_projects(worksheet, final_valid_projects)
        
        logger.info("=" * 60)
        logger.info("✨ 深層解析パトロール完了 ✨")
        logger.info(f"精査数: {processed_count} 件 / スプレッドシート追加: {added_count} 件")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"システム致命的エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
