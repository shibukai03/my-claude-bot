"""
行政映像案件スクレイピングシステム
メインエントリーポイント（県名ねじれ解消 + 日付フィルタ：不明案件キープ版）
"""

import logging
import sys
from datetime import datetime

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 60)
    logger.info("映像案件スクレイピング開始（要件完全準拠版）")
    logger.info("=" * 60)
    
    try:
        from scrapers.direct_scraper import search_all_prefectures_direct
        from scrapers.content_extractor import ContentExtractor
        from analyzer.ai_analyzer import AIAnalyzer
        from database.sheets_manager import SheetsManager
        
        # 準備
        extractor = ContentExtractor()
        analyzer = AIAnalyzer()
        sheets_manager = SheetsManager()
        today = datetime.now().date() # 2026-01-16
        today_str = today.strftime('%Y-%m-%d')
        
        # スプレッドシートを開く
        sheet_name = sheets_manager.create_monthly_sheet()
        sheets_manager.open_sheet(sheet_name)
        
        # 1. データ収集
        prefecture_results = search_all_prefectures_direct()
        all_urls = [r for results in prefecture_results.values() for r in results]
        logger.info(f"合計 {len(all_urls)} 件の候補URLを発見")
        
        final_valid_projects = []
        processed_urls = set()
        
        # 2. 解析と選別（最大100件）
        for url_data in all_urls[:100]:
            url = url_data['url']
            if url in processed_urls: continue
            processed_urls.add(url)
            
            content = extractor.extract(url)
            if not content: continue
            
            # AI判定
            analysis = analyzer.analyze_project(content)
            
            if analysis:
                deadline = analysis.get('deadline', '不明')
                
                # --- 日付フィルタロジック ---
                is_valid = False
                if deadline == "不明":
                    is_valid = True # 要件：不明案件も残す
                else:
                    try:
                        # 締切日が今日以降なら有効
                        deadline_date = datetime.strptime(deadline, '%Y-%m-%d').date()
                        if deadline_date >= today:
                            is_valid = True
                        else:
                            logger.info(f"⏭️ 過去案件除外: {analysis['title']} ({deadline})")
                    except:
                        is_valid = True # 日付形式が異常な場合も念のため残す
                
                if is_valid:
                    # 要件2：[取得日, 都道府県, 案件名, 要約, 期限, 元URL, 申込URL] の形に整理
                    final_data = {
                        'date': today_str,
                        'prefecture': analysis['prefecture'],
                        'title': analysis['title'],
                        'summary': analysis['summary'],
                        'deadline': deadline,
                        'source_url': url,
                        'application_url': analysis['application_url']
                    }
                    final_valid_projects.append(final_data)
                    logger.info(f"✅ 合格: [{analysis['prefecture']}] {analysis['title']}")

        # 3. スプレッドシート保存
        if final_valid_projects:
            # 重複URLチェックは sheets_manager 側で実行
            added = sheets_manager.append_projects(final_valid_projects)
            logger.info(f"✓ 完了: {added} 件の新着案件を保存しました")
        else:
            logger.info("保存対象の案件はありませんでした")
            
    except Exception as e:
        logger.error(f"システムエラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
