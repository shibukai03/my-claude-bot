import logging
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
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("映像案件スクレイピング v1.11 [Haiku・ハイブリッド・完全検閲版]")
    logger.info("=" * 60)
    
    try:
        from scrapers.direct_scraper import search_all_prefectures_direct
        from scrapers.content_extractor import ContentExtractor
        
        analyzer = AIAnalyzer()
        sheets_manager = SheetsManager(os.environ["SPREADSHEET_ID"], json.loads(os.environ["GCP_SERVICE_ACCOUNT"]))
        extractor = ContentExtractor()
        jst = timezone(timedelta(hours=9))
        today = datetime.now(jst).date()

        # 1. 救済チェック
        batch_id, url_map = None, {} 
        existing_batches = analyzer.client.beta.messages.batches.list(limit=5)
        for b in existing_batches.data:
            if b.processing_status != "ended" or (datetime.now(timezone.utc) - b.created_at).total_seconds() < 14400:
                logger.info(f"🔄 進行中のバッチを継続監視: {b.id}")
                batch_id = b.id; break

        if not batch_id:
            logger.info("【ステップ1】全国リンク収集開始")
            prefecture_results = search_all_prefectures_direct()
            all_tasks = [{"pref": p, **r} for p, rs in prefecture_results.items() for r in rs]
            
            logger.info("【ステップ2】重要コンテンツ抽出開始")
            batch_requests = []
            for i, task in enumerate(all_tasks, 1):
                content_data = extractor.extract(task['url'])
                if content_data:
                    cid = f"req_{i}"
                    url_map[cid] = {**task, 'content': content_data['content']}
                    batch_requests.append(analyzer.make_batch_request(cid, task['title'], content_data['content'], task['url']))
            
            logger.info(f"【ステップ3】Anthropic Batch送信 ({len(batch_requests)}件)")
            batch = analyzer.client.beta.messages.batches.create(requests=batch_requests)
            batch_id = batch.id
        
        # 4. 待機 ＋ 5時間タイマー
        logger.info("【ステップ4】AI解析待ち...")
        use_fallback = False
        while True:
            try:
                b_status = analyzer.client.beta.messages.batches.retrieve(batch_id)
                if b_status.processing_status == "ended": break
                if (time.time() - start_time) > 10800:
                    logger.warning("⚠️ 5時間経過。Haikuリアルタイム解析に切り替えます")
                    use_fallback = True; break
                logger.info(f"⏳ {b_status.processing_status}: {b_status.request_counts.succeeded}件完了")
                time.sleep(60)
            except: time.sleep(300)
        
        # 5. 結果解析 (共通検閲ロジック)
        final_projects, seen_titles = [], set()

        def is_valid_project(analysis):
            if analysis.get('label') not in ["A", "B"]: return False
            t = analysis.get('title', '無題')
            if t in seen_titles: return False
            if re.search(r"令和[5-7]|R[5-7]|202[3-5]", t) and "令和8" not in t: return False
            dp = analysis.get('deadline_prop', '不明')
            if dp != "不明":
                m = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', dp)
                if m and datetime(*map(int, m.groups())).date() < today: return False
            return True

        if use_fallback:
            for cid, task in url_map.items():
                analysis = analyzer.analyze_single(task['title'], task['content'], task['url'])
                if analysis and is_valid_project(analysis):
                    analysis.update({'prefecture': task['pref']})
                    final_projects.append(analysis); seen_titles.add(analysis['title'])
                    logger.info(f"✨ 救済合格: {analysis['title']}")
                time.sleep(0.5)
        else:
            for res in analyzer.client.beta.messages.batches.results(batch_id):
                if res.result.type == "succeeded":
                    try:
                        analysis = json.loads(re.search(r'\{.*\}', res.result.message.content[0].text, re.DOTALL).group(0))
                        if is_valid_project(analysis):
                            if res.custom_id in url_map:
                                analysis.update({'prefecture': url_map[res.custom_id]['pref']})
                            final_projects.append(analysis); seen_titles.add(analysis['title'])
                            logger.info(f"✅ 合格: {analysis['title']}")
                    except: continue

        # 6. 書き込み
        if final_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v16")
            sheets_manager.append_projects(sheets_manager.prepare_v12_sheet(sheet_name), final_projects)
            logger.info(f"✨ 完了！ {len(final_projects)}件を追加しました")
        else: logger.warning("⚠️ 有効な新着なし")
        
    except Exception as e: logger.error(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
