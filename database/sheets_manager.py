"""Googleスプレッドシート操作"""

import logging
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import List, Dict
import os

logger = logging.getLogger(__name__)


class SheetsManager:
    """Googleスプレッドシート管理クラス"""
    
    COLUMNS = [
        "取得日", "都道府県", "案件名", "要約", "締切",
        "元URL", "申込URL", "案件種別", "確信度", "ファイル形式"
    ]
    
    def __init__(self):
        self.spreadsheet_id = os.getenv('SPREADSHEET_ID')
        self.credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        
        if not self.spreadsheet_id:
            raise ValueError("SPREADSHEET_ID が設定されていません")
        
        self.client = self._authenticate()
        self.worksheet = None
        logger.info(f"SheetsManager初期化完了")
    
    def _authenticate(self) -> gspread.Client:
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
    
    def open_sheet(self, sheet_name: str = None):
        """スプレッドシートを開く"""
        spreadsheet = self.client.open_by_key(self.spreadsheet_id)
        
        if sheet_name:
            try:
                self.worksheet = spreadsheet.worksheet(sheet_name)
            except:
                self.worksheet = spreadsheet.add_worksheet(sheet_name, 1000, 10)
                self._initialize_sheet()
        else:
            self.worksheet = spreadsheet.sheet1
            self._initialize_sheet()
        
        logger.info(f"シートを開きました: {self.worksheet.title}")
    
    def _initialize_sheet(self):
        """シートを初期化"""
        existing_header = self.worksheet.row_values(1)
        
        if not existing_header or existing_header != self.COLUMNS:
            self.worksheet.clear()
            self.worksheet.append_row(self.COLUMNS)
            logger.info("シートを初期化しました")
    
    def get_existing_urls(self) -> set:
        """既存URLを取得"""
        url_column = self.worksheet.col_values(6)  # F列
        return set(url_column[1:]) if len(url_column) > 1 else set()
    
    def append_projects(self, projects: List[Dict]) -> int:
        """案件データを追記"""
        existing_urls = self.get_existing_urls()
        new_projects = [p for p in projects if p.get('url', '') not in existing_urls]
        
        if not new_projects:
            logger.info("追加する新規案件はありません")
            return 0
        
        rows_to_add = []
        for project in new_projects:
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                project.get('prefecture', ''),
                project.get('title', '')[:200],
                project.get('summary', '')[:300],
                project.get('deadline', '不明'),
                project.get('url', ''),
                project.get('application_url', ''),
                project.get('project_type', ''),
                project.get('confidence', ''),
                project.get('file_type', '')
            ]
            rows_to_add.append(row)
        
        self.worksheet.append_rows(rows_to_add)
        logger.info(f"スプレッドシートに{len(rows_to_add)}件追加")
        return len(rows_to_add)
    
    def create_monthly_sheet(self) -> str:
        """月次シートを作成"""
        sheet_name = datetime.now().strftime("映像案件_%Y年%m月")
        
        try:
            self.client.open_by_key(self.spreadsheet_id).worksheet(sheet_name)
            logger.info(f"シート '{sheet_name}' は既に存在します")
        except:
            spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            self.worksheet = spreadsheet.add_worksheet(sheet_name, 1000, 10)
            self._initialize_sheet()
            logger.info(f"月次シート作成: {sheet_name}")
        
        return sheet_name
```
