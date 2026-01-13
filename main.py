import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from anthropic import Anthropic
import json

# 1. 金庫からカギを取り出す
secrets = st.secrets
anthropic_key = secrets["ANTHROPIC_API_KEY"]
gcp_json = json.loads(secrets["GCP_SERVICE_ACCOUNT_JSON"])

# 2. ロボットの準備（スプレッドシートを触る準備）
scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
creds = Credentials.from_service_account_info(gcp_json, scopes=scopes)
gc = gspread.authorize(creds)
client = Anthropic(api_key=anthropic_key)

st.title("🚀 Claude 自動リサーチロボット")

# 画面でスプレッドシートのURLを入力できるようにします
url = st.text_input("スプレッドシートのURLを貼ってください：")

if st.button("リサーチを開始する") and url:
    with st.spinner("Claudeがお仕事中..."):
        sh = gc.open_by_url(url)
        worksheet = sh.get_worksheet(0) # 一番左のシート
        
        # A列を読み取って、Claudeに聞いて、B列に書く
        data = worksheet.col_values(1)
        for i, text in enumerate(data):
            if i == 0 or not text: continue # 1行目や空っぽは飛ばす
            
            # Claudeにお願いする
            message = client.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=1000,
                messages=[{"role": "user", "content": f"{text}について最新情報をリサーチして要約してください。"}]
            )
            
            # 結果をB列（2列目）に書く
            worksheet.update_cell(i + 1, 2, message.content[0].text)
            st.success(f"✅ 【{text}】を調べ終わりました！")

st.write("※A列に調べたい言葉を入れてボタンを押してね。")
