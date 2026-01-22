import requests
import logging
import io
import re
import pdfplumber
from bs4 import BeautifulSoup
from typing import Dict, Optional
from urllib.parse import urljoin
import urllib3

# SSLエラー対策
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)

class ContentExtractor:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.verify = False 

    def extract(self, url: str) -> Optional[Dict]:
        try:
            response = self.session.get(url, timeout=30, verify=self.verify)
            response.encoding = response.apparent_encoding
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            
            # Webページ本文
            main_text = f"【Web本文】\n{soup.get_text(separator=' ', strip=True)[:3000]}\n"
            
            # PDFリンクの抽出と選別
            combined_pdf_text = ""
            for link in soup.find_all('a', href=True):
                href = link['href']
                link_text = link.get_text()
                
                if href.lower().endswith('.pdf'):
                    # 🆕 ノイズPDF（結果、回答、様式など）は読み飛ばす
                    if any(x in link_text for x in ['質問', '回答', '結果', '落札', '様式', '記入例', '名簿']):
                        continue
                        
                    pdf_url = urljoin(url, href)
                    combined_pdf_text += self._extract_future_pages(pdf_url)
                    
                    if len(main_text + combined_pdf_text) > 12000: break

            return {'url': url, 'content': main_text + combined_pdf_text}
        except Exception as e:
            logger.error(f"抽出失敗: {url} - {e}")
            return None

    def _extract_future_pages(self, pdf_url):
        """PDF全ページを走査し、2026年(R8)以降の記述やスケジュールがあるページを抜粋"""
        try:
            res = self.session.get(pdf_url, timeout=20, verify=self.verify)
            extracted = f"\n--- PDF: {pdf_url.split('/')[-1]} ---\n"
            with pdfplumber.open(io.BytesIO(res.content)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    # 🆕 2026年以降、令和8年以降、またはスケジュール単語を検索
                    future_yr = re.search(r"(202[6-9]|20[3-9][0-9]|令和[8-9]|令和[1-2][0-9]|R[8-9]|R[1-2][0-9])", text)
                    is_sch = any(k in text for k in ["スケジュール", "期間", "期限", "締切", "提出", "実施"])
                    if future_yr or is_sch:
                        extracted += text + "\n"
                        if len(extracted) > 4000: break
            return extracted
        except: return ""
