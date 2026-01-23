import gspread
from google.oauth2.service_account import Credentials
import logging

logger = logging.getLogger(__name__)

class SheetsManager:
    # 指示書 v1.2 準拠の16項目 (変更なし)
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
            # ヘッダーを強調（太字 + グレー背景）
            ws.format('A1:P1', {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}})
            return ws
        except Exception as e:
            logger.error(f"シート準備エラー: {e}")
            return None

    def append_projects(self, worksheet, projects):
        """A/Bラベルの案件をスプレッドシートに一括追加"""
        rows_to_add = []
        for i, p in enumerate(projects, 1):
            # 🆕 AI側のキー名 (deadline_apply 等) と一致するように修正
            row = [
                i,                                      # 案件ID
                p.get('label', ''),                     # ラベル
                p.get('prefecture', '不明'),             # 発注主体
                p.get('prefecture', '不明'),             # 都道府県/市区町村
                p.get('title', '無題'),                  # 件名
                p.get('method', '公募型プロポーザル'),     # 方式
                p.get('budget', '資料参照'),             # 予算上限/予定価格
                p.get('period', '資料参照'),             # 履行期間
                p.get('deadline_apply', '不明'),         # 🆕 締切(参加申込) ※キー名を合わせました
                p.get('deadline_ques', '不明'),          # 締切(質問)
                p.get('deadline_prop', '不明'),          # 締切(提案書)
                p.get('source_url', ''),                # 公告URL
                p.get('source_url', ''),                # 添付資料URL
                p.get('evidence', ''),                  # 映像要件の根拠(Evidence)
                "映像・プロモーション",                    # タグ
                p.get('memo', '')                       # メモ
            ]
            rows_to_add.append(row)
        
        if rows_to_add:
            worksheet.append_rows(rows_to_add)
            return len(rows_to_add)
        return 0
