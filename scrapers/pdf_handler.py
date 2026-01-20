import requests
import fitz  # PyMuPDFのライブラリ名
import logging
import io

logger = logging.getLogger(__name__)

class PDFHandler:
    def __init__(self, max_pages=30):
        # APIコストが爆発しないよう、1つのPDFにつき最大30ページまでに設定
        self.max_pages = max_pages

    def extract_text_from_url(self, pdf_url):
        """URLからPDFを読み込み、全ページのテキストを抽出する"""
        if not pdf_url or not pdf_url.lower().endswith('.pdf'):
            return ""

        try:
            logger.info(f"📄 PDF深層解析を開始: {pdf_url}")
            response = requests.get(pdf_url, timeout=30)
            response.raise_for_status()

            # メモリ上でPDFを展開
            pdf_data = io.BytesIO(response.content)
            doc = fitz.open(stream=pdf_data, filetype="pdf")
            
            full_text = []
            # 指定した最大ページ数まで読み込む
            page_count = min(len(doc), self.max_pages)
            
            for page_num in range(page_count):
                page = doc.load_page(page_num)
                text = page.get_text()
                if text.strip():
                    full_text.append(f"--- Page {page_num + 1} ---")
                    full_text.append(text)
            
            doc.close()
            combined_text = "\n".join(full_text)
            
            if combined_text:
                logger.info(f"✅ PDF抽出成功: {len(combined_text)}文字取得 ({page_count}ページ分)")
            else:
                logger.warning("⚠️ PDFからテキストが検出されませんでした（画像形式の可能性があります）")
                
            return combined_text

        except Exception as e:
            logger.error(f"❌ PDF解析失敗 ({pdf_url}): {e}")
            return ""
