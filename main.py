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
    logger.info("映像案件スクレイピング v1.4 [Batch API 最終調整版]")
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
        prefecture_results = search_all_prefectures_direct()
        all_tasks = []
        for pref, results in prefecture_results.items():
            for res in results:
                res['pref'] = pref
                all_tasks.append(res)
        
        logger.info(f">>> {len(all_tasks)} 件のリンクを収集しました。")

        # 2. Batchリクエストの作成
        batch_requests = []
        url_map = {}
        for i, task in enumerate(all_tasks):
            content_data = extractor.extract(task['url'])
            if not content_data: continue
            
            custom_id = f"req_{i}"
            url_map[custom_id] = task
            req = analyzer.make_batch_request(custom_id, task['title'], content_data.get('content', ''))
            batch_requests.append(req)

        if not batch_requests:
            logger.info("解析対象のデータがありませんでした。")
            return

        # 3. AnthropicにBatchを送信
        logger.info(f"Anthropic Batch APIへ {len(batch_requests)} 件送信します...")
        batch = analyzer.client.beta.messages.batches.create(requests=batch_requests)
        batch_id = batch.id
        
        # 4. 完了まで待機ループ（属性名を succeeded に修正）
        logger.info(f"解析中... (Batch ID: {batch_id})")
        
        while True:
            batch_status = analyzer.client.beta.messages.batches.retrieve(batch_id)
            status = batch_status.processing_status 
            
            # ステータスごとの件数を集計して進捗を表示
            counts = batch_status.request_counts
            finished = counts.succeeded + counts.errored + counts.canceled + counts.expired
            
            logger.info(f"現在のステータス: {status} ({finished} / {len(batch_requests)} 件処理済み)")
            
            if status == "ended":
                break
            
            # 1分おきにチェック
            time.sleep(60)

        # 5. 結果の回収と超厳格フィルター
        logger.info("解析完了。結果をダウンロードして最終チェックを行います。")
        final_valid_projects = []
        
        for result in analyzer.client.beta.messages.batches.results(batch_id):
            custom_id = result.custom_id
            if result.result.type == "message":
                res_text = result.result.message.content[0].text
                try:
                    match = re.search(r'\{.*\}', res_text, re.DOTALL)
                    if not match: continue
                    analysis = json.loads(match.group(0))
                    
                    if analysis.get('label') in ["A", "B"]:
                        d_prop = analysis.get('deadline_prop', "不明")
                        
                        if not d_prop or d_prop == "不明":
                            continue
                        
                        date_match = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', d_prop)
                        if date_match:
                            y, m, d = map(int, date_match.groups())
                            if datetime(y, m, d).date() < today:
                                continue 
                        else:
                            continue

                        orig = url_map[custom_id]
                        analysis['source_url'] = orig['url']
                        analysis['prefecture'] = orig['pref']
                        final_valid_projects.append(analysis)
                except: continue

        # 6. 書き込み
        if final_valid_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_Batch")
            worksheet = sheets_manager.prepare_v12_sheet(sheet_name)
            sheets_manager.append_projects(worksheet, final_valid_projects)
            logger.info(f"✨ パトロール完了！ {len(final_valid_projects)} 件をシートに追加しました。")
        else:
            logger.info("現在応募可能な映像案件は見つかりませんでした。")

    except Exception as e:
        logger.error(f"システム致命的エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
