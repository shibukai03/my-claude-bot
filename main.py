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
    logger.info("映像案件スクレイピング v1.5 [Batch API 最終完成版]")
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
        logger.info("【ステップ1】リンク収集開始")
        prefecture_results = search_all_prefectures_direct()
        
        all_tasks = []
        for pref, results in prefecture_results.items():
            for res in results:
                res['pref'] = pref
                all_tasks.append(res)
        
        logger.info(f"✅ {len(all_tasks)} 件のリンクを収集")
        
        # 🧪 テストモード: 最初の10件のみ処理 (本番はここを False に)
        TEST_MODE = False
        if TEST_MODE:
            all_tasks = all_tasks[:10]
            logger.info(f"🧪 テストモード: {len(all_tasks)}件のみ処理")
        
        # 2. コンテンツ抽出
        logger.info("【ステップ2】コンテンツ抽出開始")
        batch_requests = []
        url_map = {}
        
        for i, task in enumerate(all_tasks, 1):
            logger.info(f"抽出中 ({i}/{len(all_tasks)}): {task['title'][:30]}...")
            content_data = extractor.extract(task['url'])
            
            if not content_data:
                logger.warning(f"⚠️ 抽出失敗: {task['url']}")
                continue
            
            custom_id = f"req_{i}"
            url_map[custom_id] = task
            req = analyzer.make_batch_request(custom_id, task['title'], content_data.get('content', ''))
            batch_requests.append(req)
        
        if not batch_requests:
            logger.warning("❌ 解析対象のデータがありません")
            return
        
        # 3. Batch送信
        logger.info(f"【ステップ3】Anthropic Batch API送信 ({len(batch_requests)}件)")
        batch = analyzer.client.beta.messages.batches.create(requests=batch_requests)
        batch_id = batch.id
        logger.info(f"✅ Batch送信完了 (ID: {batch_id})")
        
        # 4. 完了待機
        logger.info("【ステップ4】処理完了を待機中...")
        while True:
            batch_status = analyzer.client.beta.messages.batches.retrieve(batch_id)
            status = batch_status.processing_status
            counts = batch_status.request_counts
            total = counts.succeeded + counts.errored + counts.canceled + counts.expired
            
            logger.info(f"⏳ {status}: {total}/{len(batch_requests)}件完了 (成功:{counts.succeeded}, 失敗:{counts.errored})")
            if status == "ended": break
            time.sleep(30)
        
        # 5. 結果解析
        logger.info("【ステップ5】結果取得・解析開始")
        stats = {"A": 0, "B": 0, "C": 0, "errors": 0}
        label_c_reasons = []
        final_valid_projects = []
        
        results_response = analyzer.client.beta.messages.batches.results(batch_id)
        
        for result in results_response:
            custom_id = result.custom_id
            if result.result.type == "succeeded":
                try:
                    res_text = result.result.message.content[0].text
                    match = re.search(r'\{.*\}', res_text, re.DOTALL)
                    if not match: continue
                    analysis = json.loads(match.group(0))
                    label = analysis.get('label', 'C')
                    
                    # 統計
                    stats[label] = stats.get(label, 0) + 1
                    if label == "C":
                        label_c_reasons.append({"title": analysis.get('title', '不明'), "evidence": analysis.get('evidence', '理由不明')})
                    
                    if label in ["A", "B"]:
                        d_prop = analysis.get('deadline_prop', "不明")
                        # 日付チェック
                        if d_prop and d_prop != "不明":
                            date_match = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', d_prop)
                            if date_match:
                                y, m, d = map(int, date_match.groups())
                                if datetime(y, m, d).date() < today:
                                    logger.info(f"⏩ 期限切れにつき除外: {analysis.get('title')}")
                                    continue
                        
                        orig = url_map[custom_id]
                        analysis['source_url'] = orig['url']
                        analysis['prefecture'] = orig['pref']
                        final_valid_projects.append(analysis)
                        logger.info(f"✅ 合格: {analysis.get('title')}")
                except: stats["errors"] += 1
        
        # デバッグ情報の表示
        logger.info("=" * 60)
        logger.info(f"📊 判定統計 - A:{stats['A']}件, B:{stats['B']}件, C:{stats['C']}件")
        if label_c_reasons:
            logger.info("🔍 除外された理由（最初の5件）:")
            for r in label_c_reasons[:5]:
                logger.info(f"  - {r['title']}: {r['evidence']}")
        logger.info("=" * 60)

        # 6. スプレッドシート書き込み
        if final_valid_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v15")
            worksheet = sheets_manager.prepare_v12_sheet(sheet_name)
            sheets_manager.append_projects(worksheet, final_valid_projects)
            logger.info(f"✨ 完了！ {len(final_valid_projects)}件をシートに追加")
        else:
            logger.warning("⚠️ 適合する案件はありませんでした")
        
    except Exception as e:
        logger.error(f"❌ システムエラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
