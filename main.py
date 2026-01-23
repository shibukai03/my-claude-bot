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
    logger.info("映像案件スクレイピング v1.8 [再開・重複排除・参加申込対応]")
    logger.info("=" * 60)
    
    try:
        from scrapers.direct_scraper import search_all_prefectures_direct
        from scrapers.content_extractor import ContentExtractor
        
        analyzer = AIAnalyzer()
        sheets_manager = SheetsManager(os.environ["SPREADSHEET_ID"], json.loads(os.environ["GCP_SERVICE_ACCOUNT"]))
        extractor = ContentExtractor()
        jst = timezone(timedelta(hours=9))
        today = datetime.now(jst).date()

        # 🆕 【救済】未完了バッチがないか確認
        batch_id = None
        url_map = {} 
        existing_batches = analyzer.client.beta.messages.batches.list(limit=5)
        for b in existing_batches.data:
            if b.processing_status != "ended" or (datetime.now(timezone.utc) - b.created_at).total_seconds() < 14400:
                logger.info(f"🔄 救済対象バッチを発見: {b.id}")
                batch_id = b.id; break

        if not batch_id:
            # 1. リンク収集
            logger.info("【ステップ1】全国リンク収集開始")
            prefecture_results = search_all_prefectures_direct()
            all_tasks = [{"pref": p, **r} for p, rs in prefecture_results.items() for r in rs]
            logger.info(f"✅ {len(all_tasks)}件のリンクを取得")
            
            # 2. コンテンツ抽出
            logger.info("【ステップ2】重要コンテンツ抽出開始")
            batch_requests = []
            for i, task in enumerate(all_tasks, 1):
                if i % 20 == 0: logger.info(f"進捗: {i}/{len(all_tasks)}")
                content_data = extractor.extract(task['url'])
                if not content_data: continue
                
                cid = f"req_{i}"
                url_map[cid] = task
                # 🆕 AIにURLも渡す
                batch_requests.append(analyzer.make_batch_request(cid, task['title'], content_data['content'], task['url']))
            
            # 3. Batch送信
            logger.info(f"【ステップ3】Anthropic送信 ({len(batch_requests)}件)")
            batch = analyzer.client.beta.messages.batches.create(requests=batch_requests)
            batch_id = batch.id
        else:
            logger.info("⏭️ 収集ステップをスキップし、解析結果の処理へ進みます")

        # 4. 完了待機
        logger.info("【ステップ4】AI解析待ち...")
        while True:
            try:
                b_status = analyzer.client.beta.messages.batches.retrieve(batch_id)
                logger.info(f"⏳ {b_status.processing_status}: {b_status.request_counts.succeeded}件完了")
                if b_status.processing_status == "ended": break
                time.sleep(60)
            except Exception as e:
                logger.warning(f"⚠️ 5分待機... ({e})"); time.sleep(300)
        
        # 5. 結果解析
        logger.info("【ステップ5】結果解析中...")
        final_projects, stats = [], {"A": 0, "B": 0, "C": 0}
        seen_titles = set() # 🆕 重複排除用

        for res in analyzer.client.beta.messages.batches.results(batch_id):
            if res.result.type == "succeeded":
                try:
                    analysis = json.loads(re.search(r'\{.*\}', res.result.message.content[0].text, re.DOTALL).group(0))
                    label = analysis.get('label', 'C')
                    stats[label] = stats.get(label, 0) + 1
                    t = analysis.get('title', '無題')
                    
                    if t in seen_titles: continue # 🆕 重複はスキップ

                    if label in ["A", "B"]:
                        # 最終検閲
                        if re.search(r"令和[5-7]|R[5-7]|202[3-5]", t) and "令和8" not in t: continue
                        dp = analysis.get('deadline_prop', '不明')
                        if dp != "不明":
                            m = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', dp)
                            if m and datetime(*map(int, m.groups())).date() < today: continue

                        logger.info(f"✅ 合格判定({label}): {t}")
                        seen_titles.add(t) # 🆕 記録
                        
                        # URL復元ロジック
                        if res.custom_id in url_map:
                            analysis.update({'prefecture': url_map[res.custom_id]['pref']})
                        
                        final_projects.append(analysis)
                except: continue
        
        # 6. シート書き込み
        if final_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v16")
            sheets_manager.append_projects(sheets_manager.prepare_v12_sheet(sheet_name), final_projects)
            logger.info(f"✨ 完了！ {len(final_projects)}件を追加 (A:{stats['A']}, B:{stats['B']})")
        else: logger.warning("⚠️ 新着案件なし")
        
    except Exception as e: logger.error(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
