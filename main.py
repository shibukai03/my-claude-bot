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
    logger.info("映像案件スクレイピング v1.5 [デバッグ強化版]")
    logger.info("=" * 60)
    
    try:
        from scrapers.direct_scraper import search_all_prefectures_direct
        from scrapers.content_extractor import ContentExtractor
        
        analyzer = AIAnalyzer()
        sheets_manager = SheetsManager(os.environ["SPREADSHEET_ID"], json.loads(os.environ["GCP_SERVICE_ACCOUNT"]))
        extractor = ContentExtractor()
        jst = timezone(timedelta(hours=9))
        today = datetime.now(jst).date()
        today_str = today.strftime("%Y-%m-%d")
        
        # 1. リンク収集
        logger.info("【ステップ1】リンク収集開始")
        prefecture_results = search_all_prefectures_direct()
        
        all_tasks = []
        for pref, results in prefecture_results.items():
            for res in results:
                res['pref'] = pref
                all_tasks.append(res)
        
        logger.info(f"✅ {len(all_tasks)} 件のリンクを収集")
        
        # テストモード: 最初の10件のみ処理
        TEST_MODE = True
        if TEST_MODE:
            all_tasks = all_tasks[:10]
            logger.info(f"🧪 テストモード: {len(all_tasks)}件のみ処理")
        
        # 2. コンテンツ抽出
        logger.info("【ステップ2】コンテンツ抽出開始")
        batch_requests = []
        url_map = {}
        
        for i, task in enumerate(all_tasks, 1):
            logger.info(f"抽出進捗: {i}/{len(all_tasks)} - {task['title'][:50]}")
            content_data = extractor.extract(task['url'])
            
            if not content_data:
                logger.warning(f"⚠️ 抽出失敗: {task['url']}")
                continue
            
            # 抽出されたテキストの最初の部分をログ出力（最初の3件のみ）
            if i <= 3:
                logger.info(f"--- サンプル {i} ---")
                logger.info(f"タイトル: {task['title']}")
                logger.info(f"テキスト冒頭: {content_data.get('content', '')[:300]}...")
                logger.info("-" * 60)
            
            custom_id = f"req_{i}"
            url_map[custom_id] = task
            req = analyzer.make_batch_request(custom_id, task['title'], content_data.get('content', ''))
            batch_requests.append(req)
        
        if not batch_requests:
            logger.warning("❌ 解析対象のデータがありません")
            return
        
        logger.info(f"✅ {len(batch_requests)}件のコンテンツ抽出完了")
        
        # 3. Batch APIリクエストファイルを作成
        logger.info("【ステップ3】Batch APIリクエスト作成")
        batch_file = "/tmp/batch_requests.jsonl"
        
        with open(batch_file, 'w', encoding='utf-8') as f:
            for req in batch_requests:
                f.write(json.dumps(req, ensure_ascii=False) + '\n')
        
        logger.info(f"✅ リクエストファイル作成: {batch_file}")
        
        # 4. Batch送信
        logger.info("【ステップ4】Anthropic Batch API送信")
        
        batch = analyzer.client.beta.messages.batches.create(requests=batch_file)
        
        batch_id = batch.id
        logger.info(f"✅ Batch送信完了 (ID: {batch_id})")
        
        # 5. 完了待機
        logger.info("【ステップ5】処理完了を待機中...")
        
        wait_count = 0
        while True:
            batch_status = analyzer.client.beta.messages.batches.retrieve(batch_id)
            status = batch_status.processing_status
            counts = batch_status.request_counts
            
            total = counts.succeeded + counts.errored + counts.canceled + counts.expired
            
            logger.info(f"⏳ {status}: {total}/{len(batch_requests)}件処理済み (成功:{counts.succeeded}, エラー:{counts.errored})")
            
            if status == "ended":
                break
            
            wait_count += 1
            if wait_count > 60:
                logger.error("⏰ タイムアウト: 60分経過しても完了しませんでした")
                return
            
            time.sleep(60)
        
        # 6. 結果取得
        logger.info("【ステップ6】結果取得・解析")
        
        # 統計情報
        stats = {
            "label_a": 0,
            "label_b": 0,
            "label_c": 0,
            "errors": 0
        }
        
        label_c_reasons = []
        final_valid_projects = []
        
        # 結果取得
        results_response = analyzer.client.beta.messages.batches.results(batch_id)
        
        for result in results_response:
            custom_id = result.custom_id
            
            if result.result.type == "succeeded":
                try:
                    message = result.result.message
                    res_text = message.content[0].text
                    
                    # JSONを抽出
                    match = re.search(r'\{.*\}', res_text, re.DOTALL)
                    if not match:
                        logger.warning(f"⚠️ JSON抽出失敗: {custom_id}")
                        stats["errors"] += 1
                        continue
                    
                    analysis = json.loads(match.group(0))
                    label = analysis.get('label', 'C')
                    
                    # 統計を記録
                    if label == "A":
                        stats["label_a"] += 1
                    elif label == "B":
                        stats["label_b"] += 1
                    else:
                        stats["label_c"] += 1
                        # Label Cの理由を記録
                        orig_task = url_map.get(custom_id, {})
                        label_c_reasons.append({
                            "title": analysis.get('title', orig_task.get('title', '不明'))[:100],
                            "evidence": analysis.get('evidence', '理由不明')[:200],
                            "memo": analysis.get('memo', '')[:100],
                            "deadline": analysis.get('deadline_prop', '不明')
                        })
                    
                    # Label AまたはBの場合は保存候補
                    if label in ["A", "B"]:
                        d_prop = analysis.get('deadline_prop', "不明")
                        
                        # 締切チェック
                        if d_prop and d_prop != "不明":
                            date_match = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', d_prop)
                            if date_match:
                                y, m, d = map(int, date_match.groups())
                                deadline_date = datetime(y, m, d).date()
                                
                                if deadline_date < today:
                                    logger.info(f"⏩ 締切超過のため除外: {analysis.get('title')} (締切:{d_prop})")
                                    continue
                        
                        # 合格
                        orig = url_map[custom_id]
                        analysis['source_url'] = orig['url']
                        analysis['prefecture'] = orig['pref']
                        final_valid_projects.append(analysis)
                        
                        logger.info(f"✅ 合格 [Label {label}]: {analysis.get('title')} (締切:{d_prop})")
                
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON解析エラー ({custom_id}): {e}")
                    stats["errors"] += 1
                except Exception as e:
                    logger.error(f"❌ 処理エラー ({custom_id}): {e}")
                    stats["errors"] += 1
            
            elif result.result.type == "errored":
                logger.error(f"❌ API error: {custom_id}")
                stats["errors"] += 1
        
        # 詳細な統計とデバッグ情報を出力
        logger.info("=" * 60)
        logger.info("📊 判定結果の統計")
        logger.info("=" * 60)
        logger.info(f"Label A (最優先): {stats['label_a']}件")
        logger.info(f"Label B (通常): {stats['label_b']}件")
        logger.info(f"Label C (除外): {stats['label_c']}件")
        logger.info(f"エラー: {stats['errors']}件")
        logger.info(f"合格案件: {len(final_valid_projects)}件")
        logger.info("=" * 60)
        
        # Label Cの理由を出力（最大10件）
        if label_c_reasons:
            logger.info("🔍 除外された案件の理由（サンプル10件）")
            logger.info("=" * 60)
            for i, reason in enumerate(label_c_reasons[:10], 1):
                logger.info(f"{i}. タイトル: {reason['title']}")
                logger.info(f"   締切: {reason['deadline']}")
                logger.info(f"   証拠: {reason['evidence']}")
                logger.info(f"   メモ: {reason['memo']}")
                logger.info("-" * 60)
        
        # 7. スプレッドシート書き込み
        if final_valid_projects:
            logger.info("【ステップ7】スプレッドシート書き込み")
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v15")
            worksheet = sheets_manager.prepare_v12_sheet(sheet_name)
            sheets_manager.append_projects(worksheet, final_valid_projects)
            logger.info(f"✨ 完了！ {len(final_valid_projects)}件をシートに追加")
        else:
            logger.warning("⚠️ 応募可能な映像案件は見つかりませんでした")
            logger.info("💡 上記の除外理由を確認してください")
        
    except Exception as e:
        logger.error(f"❌ システムエラー: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
