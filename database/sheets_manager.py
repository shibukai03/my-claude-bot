import gspread
from google.oauth2.service_account import Credentials
import logging

logger = logging.getLogger(__name__)

class SheetsManager:
    # 指示書 v1.2 準拠のヘッダー
    HEADER = [
        "案件ID", "ラベル", "発注主体", "都道府県/市区町村", "件名", 
        "方式", "予算上限/予定価格", "履行期間", 
        "締切(参加申込)", "締切(質問)", "締切(提案書)", 
        "公告URL", "添付資料URL", "映像要件の根拠(Evidence)", "タグ", "メモ"
    ]

    def __init__(self, spreadsheet_id, credentials_dict):
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(credentials_dict, scopes=scopes)
        self.client = gspread.authorize(creds)
        self.spreadsheet = self.client.open_by_key(spreadsheet_id)

    def prepare_v12_sheet(self, sheet_name):
        """指示書v1.2用の新しいシートを準備する"""
        try:
            # 既存の同名シートがあれば削除（リセット）
            try:
                ws = self.spreadsheet.worksheet(sheet_name)
                self.spreadsheet.del_worksheet(ws)
                logger.info(f"既存のシート '{sheet_name}' をリセットしました。")
            except gspread.exceptions.WorksheetNotFound:
                pass
            
            # 新規作成してヘッダーを書き込む
            ws = self.spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="20")
            ws.append_row(self.HEADER)
            return ws
        except Exception as e:
            logger.error(f"シート準備エラー: {e}")
            return None

    def append_projects(self, worksheet, projects):
        """A/Bラベルのついた案件をスプレッドシートに追加"""
        rows_to_add = []
        for i, p in enumerate(projects, 1):
            row = [
                i, p['label'], p['prefecture'], p['prefecture'], p['title'],
                p['method'], p['budget'], p['period'],
                p['deadline_app'], p['deadline_ques'], p['deadline_prop'],
                p['source_url'], p['source_url'], p['evidence'], p['tag'], p['memo']
            ]
            rows_to_add.append(row)
        
        if rows_to_add:
            worksheet.append_rows(rows_to_add)
            return len(rows_to_add)
        return 0
