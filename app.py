"""
映像案件管理システム - Streamlit版 (2026年最新仕様)
対応項目: 取得日(JST), 都道府県, 案件名, 要約, 期限, 元URL, 申込URL
"""
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, timezone, timedelta
import plotly.express as px

# ページ設定
st.set_page_config(page_title="映像案件ダッシュボード", page_icon="🎬", layout="wide")
JST = timezone(timedelta(hours=9))

@st.cache_resource
def get_sheets_client():
    try:
        # Secretsから認証情報を取得
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"認証情報の読み込みに失敗しました: {e}")
        return None

@st.cache_data(ttl=300)
def load_data():
    client = get_sheets_client()
    if not client: return pd.DataFrame()

    # 先にシート名を決めておく（エラー防止）
    now = datetime.now(JST)
    sheet_name = now.strftime("映像案件_%Y年%m月")

    try:
        spreadsheet_id = st.secrets["spreadsheet_id"]
        sheet = client.open_by_key(spreadsheet_id)
        worksheet = sheet.worksheet(sheet_name)
        
        rows = worksheet.get_all_values()
        if len(rows) <= 1: return pd.DataFrame()
        
        df = pd.DataFrame(rows[1:], columns=rows[0])
        if '取得日' in df.columns:
            df['取得日'] = pd.to_datetime(df['取得日'], errors='coerce')
        return df
    except Exception as e:
        # スプレッドシートが見つからない場合の警告
        st.sidebar.warning(f"シート '{sheet_name}' を開けません。スプレッドシートが共有されているか確認してください。")
        return pd.DataFrame()

def main():
    st.title("🎬 映像案件 自動収集システム")
    df = load_data()

    if df.empty:
        st.info("データがありません。スプレッドシートの共有設定やシート名（映像案件_2026年01月）を確認してください。")
        return

    # --- 以下、グラフ表示などの処理（以前と同じ） ---
    st.metric("総案件数", f"{len(df)} 件")
    st.dataframe(df, use_container_width=True)

if __name__ == "__main__":
    main()
