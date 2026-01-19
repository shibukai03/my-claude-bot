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

# 日本時間(JST)の設定
JST = timezone(timedelta(hours=9))

@st.cache_resource
def get_sheets_client():
    """Google Sheets API認証"""
    try:
        creds_dict = st.secrets["gcp_service_account"]
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"認証エラー: {e}")
        return None

@st.cache_data(ttl=300)
def load_data():
    """スプレッドシートからデータを読み込む"""
    client = get_sheets_client()
    if not client: return pd.DataFrame()
    
    try:
        spreadsheet_id = st.secrets["spreadsheet_id"]
        sheet = client.open_by_key(spreadsheet_id)
        
        # 現在の月のシート名を作成 (例: 映像案件_2026年01月)
        now = datetime.now(JST)
        sheet_name = now.strftime("映像案件_%Y年%m月")
        
        worksheet = sheet.worksheet(sheet_name)
        rows = worksheet.get_all_values()
        
        if len(rows) <= 1:
            return pd.DataFrame()
        
        # データフレーム作成 (最初の行をヘッダーに)
        df = pd.DataFrame(rows[1:], columns=rows[0])
        
        # 取得日を日付型に変換
        if '取得日' in df.columns:
            df['取得日'] = pd.to_datetime(df['取得日'], errors='coerce')
        
        return df
    except Exception as e:
        st.sidebar.warning(f"シート '{sheet_name}' がまだ作成されていないか、読み込めません。")
        return pd.DataFrame()

def main():
    st.title("🎬 映像案件 自動収集システム")
    st.caption(f"現在の日本時間: {datetime.now(JST).strftime('%Y-%m-%d %H:%M')}")

    df = load_data()

    # サイドバーメニュー
    menu = st.sidebar.radio("メニュー", ["📊 統計ダッシュボード", "📋 全データ表示・検索", "💡 使い方"])

    if df.empty:
        st.info("まだ本日のデータが登録されていないか、今月のシートが空です。")
        return

    if menu == "📊 統計ダッシュボード":
        show_dashboard(df)
    elif menu == "📋 全データ表示・検索":
        show_data_table(df)
    else:
        st.write("### 💡 このシステムについて")
        st.write("毎日朝9時に全国47都道府県のサイトをAIが巡回し、映像制作に関する案件を自動抽出しています。")

def show_dashboard(df):
    # Kpi表示
    col1, col2, col3 = st.columns(3)
    col1.metric("総案件数", f"{len(df)} 件")
    col2.metric("調査済み県数", f"{df['都道府県'].nunique()} 県")
    
    # グラフ表示
    st.markdown("---")
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("📍 都道府県別の案件数")
        pref_counts = df['都道府県'].value_counts()
        fig_pref = px.bar(pref_counts, x=pref_counts.index, y=pref_counts.values, labels={'x':'県名', 'y':'件数'})
        st.plotly_chart(fig_pref, use_container_width=True)
        
    with c2:
        st.subheader("📅 取得日別の推移")
        df['date_only'] = df['取得日'].dt.date
        date_counts = df['date_only'].value_counts().sort_index()
        fig_date = px.line(x=date_counts.index, y=date_counts.values, labels={'x':'取得日', 'y':'件数'})
        st.plotly_chart(fig_date, use_container_width=True)

def show_data_table(df):
    st.subheader("📋 案件一覧")
    
    # 検索・フィルター
    search_query = st.text_input("🔍 案件名や内容で検索")
    selected_pref = st.multiselect("📍 都道府県で絞り込み", options=sorted(df['都道府県'].unique().tolist()))
    
    filtered_df = df.copy()
    if search_query:
        filtered_df = filtered_df[filtered_df.apply(lambda row: row.astype(str).str.contains(search_query, case=False).any(), axis=1)]
    if selected_pref:
        filtered_df = filtered_df[filtered_df['都道府県'].isin(selected_pref)]
    
    st.write(f"表示中: {len(filtered_df)} 件")
    
    # テーブル表示
    st.dataframe(filtered_df, use_container_width=True, hide_index=True)
    
    # CSVダウンロード機能
    csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 表示中のデータをCSV保存", csv, f"video_projects_{datetime.now(JST).strftime('%Y%m%d')}.csv", "text/csv")

if __name__ == "__main__":
    main()
