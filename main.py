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
    start_time = time.time()
    logger.info("=" * 60)
    logger.info("映像案件スクレイピング v1.11 [完全検閲・ハイブリッド救済版]")
    logger.info("=" * 60)
    
    try:
        from scrapers.direct_scraper import search_all_prefectures_direct
        from scrapers.content_extractor import ContentExtractor
        
        analyzer = AIAnalyzer()
        sheets_manager = SheetsManager(os.environ["SPREADSHEET_ID"], json.loads(os.environ["GCP_SERVICE_ACCOUNT"]))
        extractor = ContentExtractor()
        jst = timezone(timedelta(hours=9))
        today = datetime.now(jst).date()

        # 1. 救済チェック（未完了のバッチがあるか確認）
        batch_id, url_map = None, {} 
        existing_batches = analyzer.client.beta.messages.batches.list(limit=5)
        for b in existing_batches.data:
            if b.processing_status != "ended" or (datetime.now(timezone.utc) - b.created_at).total_seconds() < 14400:
                logger.info(f"🔄 救済対象バッチを発見: {b.id}")
                batch_id = b.id; break

        if not batch_id:
            # 新規実行：リンク収集とコンテンツ抽出
            logger.info("【ステップ1】全国リンク収集開始")
            prefecture_results = search_all_prefectures_direct()
            all_tasks = [{"pref": p, **r} for p, rs in prefecture_results.items() for r in rs]
            logger.info(f"✅ {len(all_tasks)}件のリンクを取得")
            
            logger.info("【ステップ2】重要コンテンツ抽出開始")
            batch_requests = []
            for i, task in enumerate(all_tasks, 1):
                if i % 20 == 0: logger.info(f"進捗: {i}/{len(all_tasks)}")
                content_data = extractor.extract(task['url'])
                if content_data:
                    cid = f"req_{i}"
                    # 救済用に content も保持
                    url_map[cid] = {**task, 'content': content_data['content']}
                    batch_requests.append(analyzer.make_batch_request(cid, task['title'], content_data['content'], task['url']))
            
            logger.info(f"【ステップ3】Anthropic Batch送信 ({len(batch_requests)}件)")
            batch = analyzer.client.beta.messages.batches.create(requests=batch_requests)
            batch_id = batch.id
        else:
            logger.info("⏭️ 収集ステップをスキップし、解析結果の待機へ進みます")

        # 4. 完了待機 ＋ 5時間救済タイマー
        logger.info("【ステップ4】AI解析待ち...")
        use_fallback = False
        while True:
            try:
                b_status = analyzer.client.beta.messages.batches.retrieve(batch_id)
                if b_status.processing_status == "ended": break
                
                # 5時間経過チェック
                if (time.time() - start_time) > 18000:
                    logger.warning("⚠️ 5時間経過してもBatchが完了しません。救済モードに切り替えます。")
                    use_fallback = True; break
                
                logger.info(f"⏳ {b_status.processing_status}: {b_status.request_counts.succeeded}件完了")
                time.sleep(60)
            except: time.sleep(300)
        
        # --- 共通検閲ロジック関数の定義 ---
        final_projects, seen_titles = [], set()

        def is_valid_project(analysis):
            """救済モードとBatchモード共通の厳重フィルター"""
            label = analysis.get('label', 'C')
            if label not in ["A", "B"]: return False
            
            t = analysis.get('title', '無題')
            if t in seen_titles: return False
            
            # 年度チェック: 2025年以前を排除 (令和8年/2026年以降のみ許可)
            if re.search(r"令和[5-7]|R[5-7]|202[3-5]", t) and "令和8" not in t:
                return False
            
            # 期限チェック: 今日より前を排除
            dp = analysis.get('deadline_prop', '不明')
            if dp != "不明":
                m = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', dp)
                if m and datetime(*map(int, m.groups())).date() < today:
                    return False
            return True

        # 5. 結果解析
        logger.info("【ステップ5】結果解析中...")
        if use_fallback:
            # 救済モード：通常APIで即時解析
            for cid, task in url_map.items():
                analysis = analyzer.analyze_single(task['title'], task['content'], task['url'])
                if analysis and is_valid_project(analysis):
                    analysis.update({'prefecture': task['pref']})
                    final_projects.append(analysis)
                    seen_titles.add(analysis['title'])
                    logger.info(f"✨ 救済合格: {analysis['title']}")
                time.sleep(0.5)
        else:
            # 通常モード：Batch結果を取得
            for res in analyzer.client.beta.messages.batches.results(batch_id):
                if res.result.type == "succeeded":
                    try:
                        analysis = json.loads(re.search(r'\{.*\}', res.result.message.content[0].text, re.DOTALL).group(0))
                        if is_valid_project(analysis):
                            if res.custom_id in url_map:
                                analysis.update({'prefecture': url_map[res.custom_id]['pref']})
                            final_projects.append(analysis)
                            seen_titles.add(analysis['title'])
                            logger.info(f"✅ 合格: {analysis['title']}")
                    except: continue

        # 6. シート書き込み
        if final_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v16")
            sheets_manager.append_projects(sheets_manager.prepare_v12_sheet(sheet_name), final_projects)
            logger.info(f"✨ 完了！ {len(final_projects)}件を追加しました")
        else:
            logger.warning("⚠️ 有効な新着案件なし")
        
    except Exception as e: logger.error(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
