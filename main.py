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
    logger.info("映像案件スクレイピング v1.4 [Batch API ＋ 判定基準拡大版]")
    logger.info("=" * 60)

    try:
        from scrapers.direct_scraper import search_all_prefectures_direct
        from scrapers.content_extractor import ContentExtractor
        
        analyzer = AIAnalyzer()
        sheets_manager = SheetsManager(os.environ["SPREADSHEET_ID"], json.loads(os.environ["GCP_SERVICE_ACCOUNT"]))
        extractor = ContentExtractor()

        # 日本時間を取得
        jst = timezone(timedelta(hours=9))
        today = datetime.now(jst).date()

        # 1. リンク収集（ページネーション対応）
        prefecture_results = search_all_prefectures_direct()
        all_tasks = []
        for pref, results in prefecture_results.items():
            for res in results:
                res['pref'] = pref
                all_tasks.append(res)
        
        logger.info(f">>> {len(all_tasks)} 件のリンクを収集しました。")

        # 2. コンテンツ抽出とBatchリクエストの作成
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

        # 3. AnthropicにBatchを送信（50% OFF）
        logger.info(f"Anthropic Batch APIへ {len(batch_requests)} 件送信します...")
        batch = analyzer.client.beta.messages.batches.create(requests=batch_requests)
        batch_id = batch.id
        
        # 4. 完了まで待機ループ
        logger.info(f"解析中... (Batch ID: {batch_id})")
        while True:
            status_check = analyzer.client.beta.messages.batches.retrieve(batch_id)
            if status_check.status == "ended": break
            logger.info(f"進行状況: {status_check.request_counts.completed} / {len(batch_requests)} 件完了")
            time.sleep(60)

        # 5. 結果の回収と超厳格フィルター
        logger.info("結果を回収し、期限と内容を最終チェックします。")
        final_valid_projects = []
        
        for result in analyzer.client.beta.messages.batches.results(batch_id):
            if result.result.type == "message":
                res_text = result.result.message.content[0].text
                try:
                    match = re.search(r'\{.*\}', res_text, re.DOTALL)
                    if not match: continue
                    analysis = json.loads(match.group(0))
                    
                    if analysis.get('label') in ["A", "B"]:
                        d_prop = analysis.get('deadline_prop', "不明")
                        
                        # 期限不明または過去なら除外（お宝を守るための安全策）
                        if d_prop == "不明":
                            continue
                        
                        date_match = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', d_prop)
                        if date_match:
                            y, m, d = map(int, date_match.groups())
                            if datetime(y, m, d).date() < today:
                                continue # 期限切れ
                        else:
                            continue # 形式不明

                        # 合格案件の整理
                        orig = url_map[result.custom_id]
                        analysis['source_url'] = orig['url']
                        analysis['prefecture'] = orig['pref']
                        final_valid_projects.append(analysis)
                except: continue

        # 6. 書き込み
        if final_valid_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_Batch")
            worksheet = sheets_manager.prepare_v12_sheet(sheet_name)
            sheets_manager.append_projects(worksheet, final_valid_projects)
            logger.info(f"✨ 完了！ {len(final_valid_projects)} 件をシートに追加しました。")
        else:
            logger.info("有効な最新案件は見つかりませんでした。")

    except Exception as e:
        logger.error(f"システム致命的エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
