"""
行政映像案件スクレイピングシステム
メインエントリーポイント（総数表示 ＋ 日本時間修正版）
"""

import logging
import sys
from datetime import datetime, timezone, timedelta

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 60)
    logger.info("映像案件スクレイピング開始（日本時間 ＋ 発見総数表示版）")
    logger.info("=" * 60)
    
    try:
        from scrapers.direct_scraper import search_all_prefectures_direct
        from scrapers.content_extractor import ContentExtractor
        from analyzer.ai_analyzer import AIAnalyzer
        from database.sheets_manager import SheetsManager
        
        extractor = ContentExtractor()
        analyzer = AIAnalyzer()
        sheets_manager = SheetsManager()
        
        # --- 1. 日本時間 (JST) の取得設定 ---
        jst = timezone(timedelta(hours=9))
        now_jst = datetime.now(jst)
        now_str = now_jst.strftime('%Y-%m-%d %H:%M')
        today = now_jst.date()
        
        sheet_name = sheets_manager.create_monthly_sheet()
        sheets_manager.open_sheet(sheet_name)
        
        # --- 2. 調査の実行 ---
        prefecture_results = search_all_prefectures_direct()
        
        # 全リンクをひとつのリストにまとめる
        all_urls = [r for results in prefecture_results.values() for r in results]
        
        # --- 【追加】発見した総件数をログに表示 ---
        logger.info(f"全国47都道府県の調査が完了しました。")
        logger.info(f">>> 発見した総リンク数: {len(all_urls)} 件")
        logger.info(f"このうち上位100件をAIで精査します。")
        # ----------------------------------------
        
        final_valid_projects = []
        processed_urls = set()
        
        # 解析（上位100件）
        for url_data in all_urls[:100]:
            url = url_data['url']
            if url in processed_urls: continue
            processed_urls.add(url)
            
            content = extractor.extract(url)
            if not content: continue
            
            analysis = analyzer.analyze_project(content)
            
            if analysis:
                deadline = analysis.get('deadline', '不明')
                is_valid = False
                if deadline == "不明":
                    is_valid = True
                else:
                    try:
                        deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()
                        if deadline_date >= today:
                            is_valid = True
                    except:
                        is_valid = True
                
                if is_valid:
                    final_data = {
                        'date': now_str, # 日本時間での記録
                        'prefecture': analysis['prefecture'],
                        'title': analysis['title'],
                        'summary': analysis['summary'],
                        'deadline': deadline,
                        'source_url': url,
                        'application_url': analysis['application_url']
                    }
                    final_valid_projects.append(final_data)
                    logger.info(f"✅ 合格: [{analysis['prefecture']}] {analysis['title']}")

        if final_valid_projects:
            added = sheets_manager.append_projects(final_valid_projects)
            logger.info(f"✓ 完了: {added} 件の新規案件をスプレッドシートに保存しました")
        else:
            logger.info("保存対象の新しい案件は見つかりませんでした")
            
    except Exception as e:
        logger.error(f"システムエラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
