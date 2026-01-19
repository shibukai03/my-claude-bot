"""HTML/PDFコンテンツ抽出（ハイブリッド・深掘り解析版）"""

import requests
import logging
from bs4 import BeautifulSoup
from typing import Dict, Optional
import io
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

class ContentExtractor:
    """コンテンツ抽出クラス"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        # 自治体サイトのSSLエラー対策
        self.verify = False 

    def extract(self, url: str) -> Optional[Dict]:
        """URLからコンテンツを抽出（PDFなら直接、HTMLなら中のPDFも探す）"""
        logger.info(f"コンテンツ抽出開始: {url}")
        
        # 1. 最初からURLがPDFを指している場合
        if url.lower().endswith('.pdf'):
            return self._extract_pdf(url)
        
        # 2. HTMLページの場合（ハイブリッド解析）
        return self._extract_html_with_pdf_peek(url)

    def _extract_html_with_pdf_peek(self, url: str) -> Optional[Dict]:
        """HTMLを解析し、関連PDFがあればその中身も合流させる"""
        try:
            # SSL検証を無効にしてアクセス（verify=False）
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            response = self.session.get(url, timeout=30, verify=self.verify)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # タイトルの取得
            title = soup.title.string.strip() if soup.title else url
            
            # 不要なタグ（ナビゲーションやヘッダーなど）を除去して本文を抽出
            for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            main_text = soup.get_text(separator='\n', strip=True)
            
            # --- ハイブリッド機能：重要なPDFリンクを1つだけ深掘りする ---
            extra_pdf_text = ""
            for link in soup.find_all('a', href=True):
                href = link['href']
                link_text = link.get_text()
                
                # 「要領」「募集」「仕様」など、締切が書いてありそうなPDFを探す
                if href.lower().endswith('.pdf') and any(k in link_text for k in ['要領', '募集', '概要', '仕様', '指針']):
                    pdf_url = urljoin(url, href)
                    logger.info(f"重要PDFを発見しました。中身をのぞき見します: {link_text}")
                    
                    pdf_data = self._extract_pdf(pdf_url)
                    if pdf_data and pdf_data['content']:
                        extra_pdf_text = f"\n\n--- 付属資料PDF({link_text})より抽出 ---\n{pdf_data['content'][:3000]}"
                        break # 最も重要そうな1つを見つけたら解析終了（効率化のため）

            return {
                'url': url,
                'title': title,
                'content': (main_text + extra_pdf_text)[:6000], # AIへの送信上限を考慮
                'file_type': 'html'
            }
            
        except Exception as e:
            logger.error(f"HTML抽出エラー: {url} - {e}")
            return None

    def _extract_pdf(self, url: str) -> Optional[Dict]:
        """PDFからテキストを抽出する（すでに導入済みのPyPDF2を使用）"""
        try:
            import PyPDF2
            response = self.session.get(url, timeout=30, verify=self.verify)
            response.raise_for_status()
            
            pdf_file = io.BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # 最初の5ページ分を読み込む（締切情報は通常冒頭にあります）
            text_parts = []
            for i in range(min(len(pdf_reader.pages), 5)):
                page_text = pdf_reader.pages[i].extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            full_text = '\n'.join(text_parts)
            return {
                'url': url,
                'title': url.split('/')[-1],
                'content': full_text,
                'file_type': 'pdf'
            }
        except Exception as e:
            logger.error(f"PDF抽出エラー: {url} - {e}")
            return None
