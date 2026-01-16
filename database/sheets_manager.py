"""Googleスプレッドシート操作（7項目・要件完全準拠版）"""

import logging
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timezone, timedelta
from typing import List, Dict
import os

logger = logging.getLogger(__name__)

class SheetsManager:
    """Googleスプレッドシート管理クラス"""
    
    # 要件2に基づいたカラム構成（7項目）
    COLUMNS = [
        "取得日", "都道府県", "案件名", "要約", "期限", "元URL", "申込URL"
    ]
    
    def __init__(self):
        self.spreadsheet_id = os.getenv('SPREADSHEET_ID')
        self.credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        
        if not self.spreadsheet_id:
            raise ValueError("SPREADSHEET_ID が設定されていません")
        
        if not os.path.exists(self.credentials_file):
            raise FileNotFoundError(f"認証ファイルが見つかりません: {self.credentials_file}")
        
        self.client = self._authenticate()
        self.worksheet = None
        logger.info("SheetsManager初期化完了")
    
    def _authenticate(self):
        """Google Sheets APIで認証"""
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        credentials = Credentials.from_service_account_file(
            self.credentials_file,
            scopes=scopes
        )
        return gspread.authorize(credentials)
    
    def open_sheet(self, sheet_name=None):
        """スプレッドシートを開く"""
        try:
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            if sheet_name:
                try:
                    self.worksheet = spreadsheet.worksheet(sheet_name)
                except Exception:
                    # 新規作成時は列数を7に設定
                    self.worksheet = spreadsheet.add_worksheet(sheet_name, 1000, 7)
                    self._initialize_sheet()
            else:
                self.worksheet = spreadsheet.sheet1
                self._initialize_sheet()
            
            logger.info(f"シートを開きました: {self.worksheet.title}")
        except Exception as e:
            logger.error(f"シートオープンエラー: {e}")
            raise
    
    def _initialize_sheet(self):
        """シートのヘッダーを初期化"""
        try:
            existing_header = self.worksheet.row_values(1)
            if not existing_header:
                self.worksheet.append_row(self.COLUMNS)
                logger.info("新規ヘッダー行を追加しました")
        except Exception as e:
            logger.error(f"シート初期化エラー: {e}")
    
    def get_existing_urls(self):
        """重複チェック用：既存の元URL（6列目）をすべて取得"""
        try:
            # 要件2：元URLは6列目
            url_column = self.worksheet.col_values(6)
            return set(url_column[1:]) if len(url_column) > 1 else set()
        except Exception as e:
            logger.error(f"既存URL取得エラー: {e}")
            return set()
    
    def append_projects(self, projects: List[Dict]):
        """案件データを追記（URL重複は自動除外）"""
        if not self.worksheet:
            raise ValueError("ワークシートが開かれていません")
        
        # 重複チェック（元URLを使用）
        existing_urls = self.get_existing_urls()
        
        rows_to_add = []
        for p in projects:
            source_url = p.get('source_url', '')
            if source_url in existing_urls:
                continue
            
            # 要件2：[取得日, 都道府県, 案件名, 要約, 期限, 元URL, 申込URL]
            row = [
                p.get('date', datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d")),
                p.get('prefecture', ''),
                p.get('title', '')[:200],
                p.get('summary', '')[:500],
                p.get('deadline', '不明'),
                source_url,
                p.get('application_url', '')
            ]
            rows_to_add.append(row)
            existing_urls.add(source_url) # 今回の実行内での重複も防止
        
        if not rows_to_add:
            return 0
        
        try:
            self.worksheet.append_rows(rows_to_add)
            logger.info(f"スプレッドシートに{len(rows_to_add)}件の新規案件を追加しました")
            return len(rows_to_add)
        except Exception as e:
            logger.error(f"データ追加エラー: {e}")
            return 0
    
    def create_monthly_sheet(self):
        """月次シートの名前を生成し、存在確認/作成を行う"""
        sheet_name = datetime.now().strftime("映像案件_%Y年%m月")
        try:
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            try:
                spreadsheet.worksheet(sheet_name)
            except Exception:
                # 新規作成時は列数を7に設定
                spreadsheet.add_worksheet(sheet_name, 1000, 7)
                logger.info(f"新規月次シートを作成しました: {sheet_name}")
            return sheet_name
        except Exception as e:
            logger.error(f"月次シート管理エラー: {e}")
            raise
