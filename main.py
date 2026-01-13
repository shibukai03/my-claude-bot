"""
行政映像案件スクレイピングシステム
メインエントリーポイント
"""

import logging
import sys
import os

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """メイン実行"""
    logger.info("=" * 60)
    logger.info("映像案件スクレイピング開始")
    logger.info("=" * 60)
    
    try:
        # モジュールインポート
        from config.prefectures import PREFECTURES
        from config.keywords import PRIMARY_KEYWORDS, RELATED_KEYWORDS
        from scrapers.search_engine import search_prefecture_projects
        from scrapers.content_extractor import ContentExtractor
        from analyzer.ai_analyzer import AIAnalyzer
        from database.sheets_manager import SheetsManager
        
        logger.info("モジュール読み込み完了")
        
        # 初期化
        extractor = ContentExtractor()
        analyzer = AIAnalyzer()
        sheets_manager = SheetsManager()
        
        logger.info("初期化完了")
        
        # スプレッドシートを開く
        sheet_name = sheets_manager.create_monthly_sheet()
        sheets_manager.open_sheet(sheet_name)
        
        logger.info(f"スプレッドシート準備完了: {sheet_name}")
        
        # 収集結果
        all_results = []
        analyzed_results = []
        processed_urls = set()
        
        # 各都道府県をスクレイピング（最初の5県のみテスト）
        test_prefectures = list(PREFECTURES.items())[:5]
        
        for pref_name, pref_data in test_prefectures:
            logger.info(f"--- {pref_name} スクレイピング開始 ---")
            
            domain = pref_data['domain']
            keywords = PRIMARY_KEYWORDS[:2]  # 最初の2キーワードのみ
            
            # URL検索
            search_results = search_prefecture_projects(domain, keywords, max_results=3)
            
            if not search_results:
                logger.info(f"{pref_name}: 検索結果なし")
                continue
            
            # コンテンツ抽出
            for result in search_results[:2]:  # 最大2件
                url = result['url']
                
                if url in processed_urls:
                    continue
                
                processed_urls.add(url)
                
                extracted = extractor.extract(url)
                
                if extracted:
                    extracted['prefecture'] = pref_name
                    all_results.append(extracted)
                    logger.info(f"✓ 抽出成功: {extracted['title'][:50]}")
        
        logger.info(f"スクレイピング完了: {len(all_results)}件")
        
        # AI解析
        if all_results:
            logger.info("AI解析開始")
            analyzed_results = analyzer.batch_analyze(all_results)
            logger.info(f"映像案件抽出: {len(analyzed_results)}件")
        
        # スプレッドシートに保存
        if analyzed_results:
            logger.info("スプレッドシート保存開始")
            added = sheets_manager.append_projects(analyzed_results)
            logger.info(f"✓ 保存完了: {added}件追加")
        
        # サマリー
        logger.info("=" * 60)
        logger.info("実行完了")
        logger.info(f"スクレイピング: {len(all_results)}件")
        logger.info(f"映像案件: {len(analyzed_results)}件")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"エラー発生: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
