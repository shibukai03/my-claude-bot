"""
行政映像案件スクレイピングシステム
メインエントリーポイント（県名ねじれ解消 + 日付フィルタ：不明案件キープ版）
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
    """メイン実行"""
    logger.info("=" * 60)
    logger.info("映像案件スクレイピング開始（精度向上・不明案件キープ版）")
    logger.info("=" * 60)
    
    try:
        # モジュールインポート
        from scrapers.direct_scraper import search_all_prefectures_direct
        from scrapers.content_extractor import ContentExtractor
        from analyzer.ai_analyzer import AIAnalyzer
        from database.sheets_manager import SheetsManager
        
        # 本日の日付（過去案件の判定用）
        today = datetime.now().date()
        
        # 初期化
        extractor = ContentExtractor()
        analyzer = AIAnalyzer()
        sheets_manager = SheetsManager()
        
        logger.info("初期化完了")
        
        # スプレッドシート準備
        sheet_name = sheets_manager.create_monthly_sheet()
        sheets_manager.open_sheet(sheet_name)
        
        # ステップ1: スクレイピング実行
        logger.info("【ステップ1】データ収集開始")
        prefecture_results = search_all_prefectures_direct()
        
        all_urls = []
        for pref_name, results in prefecture_results.items():
            for result in results:
                # 検索時のラベル（都道府県）を一旦セット
                result['search_label'] = pref_name
                all_urls.append(result)
        
        logger.info(f"合計 {len(all_urls)} 件のURLを発見")
        
        # ステップ2 & 3: 解析とフィルタリング
        logger.info("【ステップ2/3】解析・フィルタリング開始（最大100件）")
        
        final_valid_projects = []
        processed_urls = set()
        
        # AI費用と時間のバランスのため100件に制限
        max_process = min(100, len(all_urls))
        
        for idx, url_data in enumerate(all_urls[:max_process], 1):
            url = url_data['url']
            if url in processed_urls: continue
            processed_urls.add(url)
            
            # コンテンツ抽出
            extracted = extractor.extract(url)
            if not extracted: continue
            
            # AI解析（正しい県名と締切をAIに判断させる）
            # ※ analyzer.analyze_project は、映像案件でなければ None を返します
            analysis_result = analyzer.analyze_project(extracted)
            
            if analysis_result:
                deadline_str = analysis_result.get('deadline', '不明')
                
                # --- 日付フィルタの適用 ---
                is_valid_date = False
                
                # 1. 締切が「不明」なら、チャンスを逃さないためキープ！
                if deadline_str == "不明":
                    logger.info(f"✅ 不明案件をキープ: [{analysis_result.get('prefecture', '不明')}] {analysis_result['title']}")
                    is_valid_date = True
                
                # 2. 日付がある場合、今日以降ならキープ、過去なら捨てる
                else:
                    try:
                        deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d').date()
                        if deadline_date >= today:
                            logger.info(f"✨ 有効案件発見: [{analysis_result.get('prefecture', '不明')}] {analysis_result['title']} (締切:{deadline_str})")
                            is_valid_date = True
                        else:
                            logger.info(f"⏭️ 過去案件のため除外: {analysis_result['title']} (締切:{deadline_str})")
                    except:
                        # 日付の形式が読み取れない場合も、念のため残す
                        logger.info(f"✅ 形式不明につきキープ: {analysis_result['title']}")
                        is_valid_date = True

                if is_valid_date:
                    # AIが特定した正しい県名をスプレッドシートに書き込むため、データを保持
                    # 以前のコードと互換性を持たせるためにurlをセット
                    analysis_result['url'] = url
                    final_valid_projects.append(analysis_result)

        # ステップ4: スプレッドシートに保存
        if final_valid_projects:
            logger.info(f"【ステップ4】スプレッドシート保存開始 ({len(final_valid_projects)}件)")
            # 重複除外機能付きの append_projects を使用
            added = sheets_manager.append_projects(final_valid_projects)
            logger.info(f"✓ 保存完了: {added}件を新規追加しました")
        else:
            logger.warning("本日保存すべき有効な案件は見つかりませんでした")
            
        # サマリー
        logger.info("=" * 60)
        logger.info("全工程終了")
        logger.info(f"発見: {len(all_urls)}件 / 解析対象: {max_process}件 / 採用: {len(final_valid_projects)}件")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"システムエラー発生: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
