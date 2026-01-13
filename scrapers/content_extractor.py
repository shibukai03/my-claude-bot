"""HTML/PDFコンテンツ抽出"""

import requests
import logging
from bs4 import BeautifulSoup
from typing import Dict, Optional
import io

logger = logging.getLogger(__name__)


class ContentExtractor:
    """コンテンツ抽出クラス"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def extract(self, url: str) -> Optional[Dict]:
        """URLからコンテンツを抽出"""
        logger.info(f"コンテンツ抽出: {url}")
        
        if url.lower().endswith('.pdf'):
            return self._extract_pdf(url)
        else:
            return self._extract_html(url)
    
    def _extract_html(self, url: str) -> Optional[Dict]:
        """HTMLから情報抽出"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # タイトル取得
            title = ''
            if soup.title and soup.title.string:
                title = soup.title.string.strip()
            elif soup.h1:
                title = soup.h1.get_text().strip()
            
            # 不要タグ除去
            for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            
            text_content = soup.get_text(separator='\n', strip=True)
            
            # PDFリンク収集
            pdf_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.lower().endswith('.pdf'):
                    from urllib.parse import urljoin
                    pdf_links.append(urljoin(url, href))
            
            return {
                'url': url,
                'title': title,
                'content': text_content,
                'file_type': 'html',
                'pdf_links': pdf_links
            }
            
        except Exception as e:
            logger.error(f"HTML抽出エラー: {url} - {e}")
            return None
    
    def _extract_pdf(self, url: str) -> Optional[Dict]:
        """PDFからテキスト抽出"""
        try:
            import PyPDF2
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            pdf_file = io.BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text_parts = []
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            
            full_text = '\n'.join(text_parts)
            title = url.split('/')[-1]
            
            return {
                'url': url,
                'title': title,
                'content': full_text,
                'file_type': 'pdf',
                'pdf_links': []
            }
            
        except ImportError:
            logger.error("PyPDF2 が利用できません")
            return None
        except Exception as e:
            logger.error(f"PDF抽出エラー: {url} - {e}")
            return None
