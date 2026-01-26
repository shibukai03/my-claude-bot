import logging
import os
import json
import re
from typing import Dict, Optional
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        # 🚀 修正：確定した最新モデル ID を使用
        self.model = "claude-haiku-4-5-20251001" 
        logger.info(f"AI解析ユニット(Claude 4.5 Haiku)起動完了")
    
    def get_prompt(self, title: str, content: str, url: str) -> str:
        jst = timezone(timedelta(hours=9))
        today = datetime.now(jst)
        today_str = today.strftime('%Y-%m-%d')
        r_year = today.year - 2018
        
        return f"""あなたは自治体入札案件のプロ査定士です。今日: {today_str} (令和{r_year}年)

# 🎯 判定ミッション
Webページから「映像制作・動画制作・ライブ配信」の業務委託を探してください。

# ❌ 絶対除外ルール (Label C)
1. **物品の購入**: カメラ、モニター、ドローン、医療機器等の「モノの買い入れ」は除外。
2. **システムの構築**: サーバーやネットワーク、ソフトウェア導入のみの案件。
3. **過去・終了案件**: 令和7年(2025)以前のもの、または「選定結果」等の事後報告。
4. **人材募集**: 職員採用、試験案内など。

# ✅ 採用基準
- **Label A**: 動画制作、撮影業務が主目的。
- **Label B**: イベントや事務事業の一部に映像制作が含まれる。

# ⚠️ 令和8年(2026) 厳守
- 本文に「令和8年」または「2026年」という具体的な未来の予定・期限があること。
- 令和6年や令和7年が主役の案件は全て Label C としてください。

# 出力形式 (JSON)
{{
  "label": "A, B, または C",
  "title": "正式な案件名",
  "source_url": "{url}", 
  "deadline_apply": "YYYY-MM-DD (不明時は 不明)",
  "deadline_prop": "YYYY-MM-DD (不明時は 不明)",
  "prefecture": "自治体名",
  "evidence": "映像制作の必要性と現在募集中である根拠",
  "memo": "令和{r_year}年度(2026)案件であることを確認済み"
}}

---
件名: {title}
内容: {content[:13000]}
"""

    def analyze_single(self, title: str, content: str, url: str) -> Optional[Dict]:
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0,
                messages=[{"role": "user", "content": self.get_prompt(title, content, url)}]
            )
            res_text = message.content[0].text
            match = re.search(r'\{.*\}', res_text, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return None
        except Exception as e:
            logger.error(f"解析エラー: {e}")
            return None
