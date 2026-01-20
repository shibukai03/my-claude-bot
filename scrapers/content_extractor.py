"""HTML/PDFコンテンツ抽出（PyMuPDF深層解析エンジン連結版）"""

import requests
import logging
from bs4 import BeautifulSoup
from typing import Dict, Optional
from urllib.parse import urljoin
import urllib3
from scrapers.pdf_handler import PDFHandler  # 新エンジンをインポート

# SSLエラー対策
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class ContentExtractor:
    """コンテンツ抽出クラス"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.verify = False 
        # Step 1 で作成したPDF深層解析エンジンを初期化（最大30ページ）
        self.pdf_handler = PDFHandler(max_pages=30)

    def extract(self, url: str) -> Optional[Dict]:
        """URLからコンテンツを抽出（PDFなら深層解析、HTMLなら中のPDFも深掘り）"""
        logger.info(f"コンテンツ抽出開始: {url}")
        
        # 1. URL自体がPDFを指している場合
        if url.lower().endswith('.pdf'):
            return self._extract_pdf_deep(url)
        
        # 2. HTMLページの場合（ページ内の重要PDFも深掘りする）
        return self._extract_html_with_deep_peek(url)

    def _extract_pdf_deep(self, url: str) -> Optional[Dict]:
        """新エンジンを使用してPDFを最大30ページまで解析する"""
        text = self.pdf_handler.extract_text_from_url(url)
        if not text:
            return None
            
        return {
            'url': url,
            'title': url.split('/')[-1],
            'content': text, # ここではカットせず、AIに渡す直前で制御します
            'file_type': 'pdf'
        }

    def _extract_html_with_deep_peek(self, url: str) -> Optional[Dict]:
        """HTMLを解析し、関連PDFがあれば新エンジンで全ページ解析して合流させる"""
        try:
            response = self.session.get(url, timeout=30, verify=self.verify)
            response.raise_for_status()
            # 文字化け対策
            response.encoding = response.apparent_encoding
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # タイトルの取得
            title = soup.title.string.strip() if soup.title else url
            
            # 不要なタグを除去
            for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            main_text = soup.get_text(separator='\n', strip=True)
            
            # --- 深掘り機能：重要なPDFリンクを1つだけ「全ページ」解析する ---
            extra_pdf_text = ""
            for link in soup.find_all('a', href=True):
                href = link['href']
                link_text = link.get_text()
                
                # キーワードに合致するPDFを探す
                if href.lower().endswith('.pdf') and any(k in link_text for k in ['要領', '募集', '概要', '仕様', '指針']):
                    pdf_url = urljoin(url, href)
                    logger.info(f"🔍 重要資料PDFを深層解析します: {link_text}")
                    
                    # 以前の5ページ制限を撤廃した新エンジンで解析
                    pdf_data = self._extract_pdf_deep(pdf_url)
                    if pdf_data and pdf_data['content']:
                        extra_pdf_text = f"\n\n--- 付属資料PDF({link_text})の全容 ---\n{pdf_data['content']}"
                        break # 最も重要な1つを深掘りしたら終了

            return {
                'url': url,
                'title': title,
                'content': main_text + extra_pdf_text,
                'file_type': 'html'
            }
            
        except Exception as e:
            logger.error(f"HTML抽出エラー: {url} - {e}")
            return None
