"""
行政映像案件スクレイピングシステム
メインエントリーポイント
"""

import logging
from typing import List, Dict

from config.prefectures import PREFECTURES
from config.keywords import PRIMARY_KEYWORDS, RELATED_KEYWORDS
from scrapers.search_engine import search_prefecture_projects
from scrapers.content_extractor import ContentExtractor
from scrapers.url_validator import URLValidator
from analyzer.ai_analyzer import AIAnalyzer
from database.sheets_manager import SheetsManager
from utils.logger import setup_logger

logger = setup_logger()


class ProjectScraper:
    """案件スクレイピングメインクラス"""
    
    def __init__(self):
        self.extractor = ContentExtractor()
        self.validator = URLValidator()
        self.analyzer = AIAnalyzer()
        self.sheets_manager = SheetsManager()
        self.raw_results = []
        self.analyzed_results = []
    
    def run_full_pipeline(self):
        """完全なパイプラインを実行"""
        logger.info("=" * 60)
        logger.info("映像案件スクレイピング開始")
        logger.info("=" * 60)
        
        # ステップ1: スクレイピング
        self.scrape_all_prefectures()
        
        # ステップ2: AI解析
        if self.raw_results:
            self.analyze_all_projects()
        
        # ステップ3: スプレッドシートに保存
        if self.analyzed_results:
            self.save_to_spreadsheet()
        
        self.print_summary()
    
    def scrape_all_prefectures(self):
        """全都道府県をスクレイピング"""
        logger.info("【ステップ1】スクレイピング開始")
        
        for pref_name, pref_data in PREFECTURES.items():
            logger.info(f"--- {pref_name} スクレイピング ---")
            self.scrape_prefecture(pref_data)
        
        logger.info(f"スクレイピング完了: {len(self.raw_results)}件取得")
    
    def scrape_prefecture(self, pref_data: Dict):
        """単一都道府県をスクレイピング"""
        domain = pref_data['domain']
        pref_name = pref_data['name']
        
        keywords = PRIMARY_KEYWORDS + RELATED_KEYWORDS
        
        # URL検索
        search_results = search_prefecture_projects(domain, keywords, max_results=5)
        
        if not search_results:
            return
        
        # URL重複チェック
        urls = [result['url'] for result in search_results]
        valid_urls = self.validator.filter_new_urls(urls)
        
        # コンテンツ抽出
        for url in valid_urls[:3]:  # 最大3件
            extracted = self.extractor.extract(url)
            
            if extracted:
                extracted['prefecture'] = pref_name
                self.raw_results.append(extracted)
                self.validator.mark_as_processed(url)
    
    def analyze_all_projects(self):
        """全案件をAI解析"""
        logger.info("【ステップ2】AI解析開始")
        self.analyzed_results = self.analyzer.batch_analyze(self.raw_results)
        logger.info(f"映像案件抽出: {len(self.analyzed_results)}件")
    
    def save_to_spreadsheet(self):
        """スプレッドシートに保存"""
        logger.info("【ステップ3】スプレッドシート保存")
        
        sheet_name = self.sheets_manager.create_monthly_sheet()
        self.sheets_manager.open_sheet(sheet_name)
        added = self.sheets_manager.append_projects(self.analyzed_results)
        
        logger.info(f"保存完了: {added}件追加")
    
    def print_summary(self):
        """実行サマリー"""
        logger.info("=" * 60)
        logger.info("実行完了")
        logger.info(f"スクレイピング: {len(self.raw_results)}件")
        logger.info(f"映像案件: {len(self.analyzed_results)}件")
        logger.info("=" * 60)


def main():
    """メイン実行"""
    scraper = ProjectScraper()
    scraper.run_full_pipeline()


if __name__ == "__main__":
    main()
