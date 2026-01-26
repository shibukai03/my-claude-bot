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
    logger.info("=" * 60)
    logger.info("映像案件スクレイピング v1.12 [Claude 3 Haiku・最速完走版]")
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
        logger.info("【ステップ1】全国自治体サイトから最新リンクを収集開始...")
        prefecture_results = search_all_prefectures_direct()
        all_tasks = [{"pref": p, **r} for p, rs in prefecture_results.items() for r in rs]
        logger.info(f"✅ {len(all_tasks)}件のリンクを収集しました")
        
        # 2. 解析と書き込みリストの作成
        final_projects = []
        seen_titles = set()
        
        logger.info("【ステップ2】サイト内容の抽出とAI解析（リアルタイム）を開始...")
        for i, task in enumerate(all_tasks, 1):
            if i % 10 == 0:
                logger.info(f"進捗: {i}/{len(all_tasks)} 件完了")
            
            # 内容抽出
            content_data = extractor.extract(task['url'])
            if not content_data: continue
            
            # AI解析 (Haiku)
            analysis = analyzer.analyze_single(task['title'], content_data['content'], task['url'])
            if not analysis: continue
            
            # 厳重フィルター (ラベル・年度・期限)
            if analysis.get('label') not in ["A", "B"]: continue
            title = analysis.get('title', '無題')
            if title in seen_titles: continue
            
            # 2025年以前の古い案件を排除
            if re.search(r"令和[5-7]|R[5-7]|202[3-5]", title) and "令和8" not in title: continue
            
            # 期限切れ排除
            dp = analysis.get('deadline_prop', '不明')
            if dp != "不明":
                m = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', dp)
                if m and datetime(*map(int, m.groups())).date() < today: continue

            # 合格！
            analysis.update({'prefecture': task['pref']})
            final_projects.append(analysis)
            seen_titles.add(title)
            logger.info(f"✨ 新着合格: {title}")
            time.sleep(0.3) # API負荷軽減

        # 3. シート書き込み
        if final_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v16")
            sheets_manager.append_projects(sheets_manager.prepare_v12_sheet(sheet_name), final_projects)
            logger.info(f"✨ 完了！ {len(final_projects)}件をシートに追加しました")
        else:
            logger.warning("⚠️ 条件に合う新着案件は見つかりませんでした")
            
    except Exception as e:
        logger.error(f"❌ 予期せぬエラーが発生しました: {e}")

if __name__ == "__main__":
    main()
