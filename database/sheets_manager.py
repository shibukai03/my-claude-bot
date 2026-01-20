import gspread
from google.oauth2.service_account import Credentials
import logging

logger = logging.getLogger(__name__)

class SheetsManager:
    # 指示書 v1.2 準拠の16項目
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
        """指示書v1.2用の新しいシートを準備（既存があればリセット）"""
        try:
            try:
                ws = self.spreadsheet.worksheet(sheet_name)
                self.spreadsheet.del_worksheet(ws)
            except gspread.exceptions.WorksheetNotFound:
                pass
            
            ws = self.spreadsheet.add_worksheet(title=sheet_name, rows="1000", cols="20")
            ws.append_row(self.HEADER)
            return ws
        except Exception as e:
            logger.error(f"シート準備エラー: {e}")
            return None

    def append_projects(self, worksheet, projects):
        """A/Bラベルの案件をスプレッドシートに一括追加"""
        rows_to_add = []
        for i, p in enumerate(projects, 1):
            row = [
                i, p.get('label'), p.get('prefecture'), p.get('prefecture'), p.get('title'),
                p.get('method'), p.get('budget'), p.get('period'),
                p.get('deadline_app'), p.get('deadline_ques'), p.get('deadline_prop'),
                p.get('source_url'), p.get('source_url'), p.get('evidence'), p.get('tag'), p.get('memo')
            ]
            rows_to_add.append(row)
        
        if rows_to_add:
            worksheet.append_rows(rows_to_add)
            return len(rows_to_add)
        return 0
