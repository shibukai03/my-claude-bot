import logging
import sys
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
    logger.info("映像案件スクレイピング v1.3 [超厳格モード：期限切れ・不明案件を完全遮断]")
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

        # シートの準備
        worksheet = sheets_manager.prepare_v12_sheet(sheet_name)

        # 全47都道府県の巡回
        prefecture_results = search_all_prefectures_direct()
        
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
            
            if processed_count % 5 == 0:
                logger.info(f"--- 進捗報告: {processed_count} / {total_found} 件完了 ---")

            try:
                # 1. コンテンツ抽出（HTML + PDF）
                content = extractor.extract(url)
                if not content: continue
                
                # 2. AIによる解析
                analysis = analyzer.analyze_project(content)
                
                # 3. 判定フィルター（超厳格判定ロジック）
                if analysis and analysis.get('label') in ["A", "B"]:
                    
                    # 期限の取得
                    d_prop = analysis.get('deadline_prop', "不明")
                    
                    # 【厳格化1】日付が「不明」のものは、古い情報やすでに終了した情報の可能性が高いため除外
                    if d_prop == "不明" or not d_prop:
                        logger.info(f"⏩ 期限不明のため安全策として除外: {analysis['title']}")
                        continue

                    # 【厳格化2】日付が今日より前（過去）なら除外
                    try:
                        # 数字を抽出して日付を正規化 (YYYY-MM-DD)
                        date_match = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', d_prop)
                        if date_match:
                            y, m, d = map(int, date_match.groups())
                            deadline_date = datetime(y, m, d).date()
                            
                            if deadline_date < today:
                                logger.info(f"⏩ 期限切れにつき除外: {analysis['title']} (締切:{d_prop})")
                                continue
                        else:
                            # 日付形式が読み取れない特殊な場合も、リスク回避のため除外
                            logger.info(f"⏩ 不正な日付形式のため除外: {analysis['title']}")
                            continue
                    except Exception as e:
                        logger.warning(f"日付判定エラーのため除外: {analysis['title']} - {e}")
                        continue
                    
                    # 全ての厳格なチェックを通過したものだけを保存
                    analysis['source_url'] = url
                    analysis['prefecture'] = url_data.get('pref', '不明')
                    final_valid_projects.append(analysis)
                    added_count += 1
                    logger.info(f"✅ 【合格】: {analysis['title']} (締切:{d_prop})")
                    
                    # 3件溜まったら書き出し（より頻繁に保存して安全性を高める）
                    if len(final_valid_projects) >= 3:
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
