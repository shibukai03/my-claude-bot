"""
行政映像案件スクレイピングシステム
メインエントリーポイント（直接スクレイピング版）
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
    logger.info("映像案件スクレイピング開始（直接スクレイピング方式）")
    logger.info("=" * 60)
    
    try:
        # モジュールインポート
        from scrapers.direct_scraper import search_all_prefectures_direct
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
        
        # ステップ1: 直接スクレイピング
        logger.info("【ステップ1】都道府県サイトから直接スクレイピング")
        prefecture_results = search_all_prefectures_direct()
        
        # URLリストを平坦化
        all_urls = []
        for pref_name, results in prefecture_results.items():
            for result in results:
                result['prefecture'] = pref_name
                all_urls.append(result)
        
        logger.info(f"合計 {len(all_urls)} 件のURLを発見")
        
        # ステップ2: コンテンツ抽出
        logger.info("【ステップ2】コンテンツ抽出開始")
        
        all_contents = []
        for idx, url_data in enumerate(all_urls[:50], 1):
            logger.info(f"抽出進捗: {idx}/{min(50, len(all_urls))}")
            
            extracted = extractor.extract(url_data['url'])
            
            if extracted:
                extracted['prefecture'] = url_data['prefecture']
                all_contents.append(extracted)
                logger.info(f"✓ {extracted['title'][:50]}")
        
        logger.info(f"コンテンツ抽出完了: {len(all_contents)}件")
        
        # ステップ3: AI解析
        if all_contents:
            logger.info("【ステップ3】AI解析開始")
            analyzed_results = analyzer.batch_analyze(all_contents)
            logger.info(f"映像案件抽出: {len(analyzed_results)}件")
        else:
            logger.warning("抽出されたコンテンツがありません")
            analyzed_results = []
        
        # ステップ4: スプレッドシートに保存
        if analyzed_results:
            logger.info("【ステップ4】スプレッドシート保存開始")
            added = sheets_manager.append_projects(analyzed_results)
            logger.info(f"✓ 保存完了: {added}件追加")
        else:
            logger.warning("保存する映像案件がありません")
        
        # サマリー
        logger.info("=" * 60)
        logger.info("実行完了")
        logger.info(f"発見URL数: {len(all_urls)}件")
        logger.info(f"コンテンツ抽出: {len(all_contents)}件")
        logger.info(f"映像案件: {len(analyzed_results)}件")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"エラー発生: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
