"""
行政映像案件スクレイピングシステム
メインエントリーポイント（ねじれ解消 + 日付フィルタ版）
"""

import logging
import sys
import os
from datetime import datetime

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 60)
    logger.info("映像案件スクレイピング開始（ねじれ解消 + 日付フィルタ版）")
    logger.info("=" * 60)
    
    try:
        from scrapers.direct_scraper import search_all_prefectures_direct
        from scrapers.content_extractor import ContentExtractor
        from analyzer.ai_analyzer import AIAnalyzer
        from database.sheets_manager import SheetsManager
        
        extractor = ContentExtractor()
        analyzer = AIAnalyzer()
        sheets_manager = SheetsManager()
        
        # 本日の日付（比較用）
        today = datetime.now().date()
        
        # スプレッドシート準備
        sheet_name = sheets_manager.create_monthly_sheet()
        sheets_manager.open_sheet(sheet_name)
        
        # ステップ1: スクレイピング実行（Google検索救済付き）
        logger.info("【ステップ1】データ収集開始")
        prefecture_results = search_all_prefectures_direct()
        
        all_urls = []
        for pref_name, results in prefecture_results.items():
            for result in results:
                # 検索時のラベル（pref_name）を一応保持
                result['search_label'] = pref_name
                all_urls.append(result)
        
        # ステップ2 & 3: 抽出とAI解析の統合
        logger.info(f"【ステップ2/3】解析開始（最大100件）")
        
        final_valid_projects = []
        processed_urls = set()
        
        for idx, url_data in enumerate(all_urls[:100], 1):
            url = url_data['url']
            if url in processed_urls: continue
            processed_urls.add(url)
            
            # コンテンツ抽出
            extracted = extractor.extract(url)
            if not extracted: continue
            
            # AI解析（正しい県名と締切をAIに判断させる）
            analysis_result = analyzer.analyze_project(extracted)
            
            if analysis_result:
                deadline_str = analysis_result.get('deadline')
                
                # --- 日付フィルタ: 不明なもの、過去のものはスキップ ---
                if not deadline_str or deadline_str == "不明":
                    logger.info(f"⏭️ 締切不明のためスキップ: {analysis_result['title']}")
                    continue
                
                try:
                    deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d').date()
                    if deadline_date < today:
                        logger.info(f"⏭️ 期限切れのため除外 ({deadline_str}): {analysis_result['title']}")
                        continue
                        
                    # すべてのフィルタを通過した案件のみ採用
                    # 県名は検索時のラベルではなく、AIが特定した「prefecture」を使用
                    final_valid_projects.append(analysis_result)
                    logger.info(f"✅ 有効案件を発見!: [{analysis_result['prefecture']}] {analysis_result['title']}")
                    
                except Exception as e:
                    logger.warning(f"日付処理エラー ({deadline_str}): {e}")
                    continue
        
        # ステップ4: スプレッドシートに保存
        if final_valid_projects:
            logger.info(f"【ステップ4】スプレッドシート保存 ({len(final_valid_projects)}件)")
            added = sheets_manager.append_projects(final_valid_projects)
            logger.info(f"✓ 保存完了: {added}件追加（重複は自動除外）")
        else:
            logger.info("本日保存すべき新規案件はありませんでした。")
            
        logger.info("=" * 60)
        logger.info(f"全工程終了 / 発見: {len(all_urls)}件 / 有効採用: {len(final_valid_projects)}件")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"システムエラー: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
