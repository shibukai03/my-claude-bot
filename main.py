import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from anthropic import Anthropic
import json

# 金庫からカギを取り出す
secrets = st.secrets
# ここの読み取りでエラーが出ていたので、金庫が正しくなれば直ります
gcp_json = json.loads(secrets["GCP_SERVICE_ACCOUNT_JSON"])

# ロボットの準備
scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_info(gcp_json, scopes=scopes)
gc = gspread.authorize(creds)
client = Anthropic(api_key=secrets["ANTHROPIC_API_KEY"])

st.title("🚀 Claude お仕事ロボット")

url = st.text_input("スプレッドシートのURLを貼ってください：")

if st.button("リサーチを開始する") and url:
    with st.spinner("Claudeがお仕事中..."):
        sh = gc.open_by_url(url)
        worksheet = sh.get_worksheet(0)
        data = worksheet.col_values(1)
        for i, text in enumerate(data):
            if i == 0 or not text: continue
            response = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1000,
                messages=[{"role": "user", "content": f"{text}について最新情報を要約して"}]
            )
            worksheet.update_cell(i + 1, 2, response.content[0].text)
            st.success(f"✅ {text} の調査完了！")
