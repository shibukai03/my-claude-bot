import logging
import os
from typing import Dict
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
        logger.info(f"AI解析ユニット起動完了")
    
    def get_prompt(self, title: str, content: str) -> str:
        jst = timezone(timedelta(hours=9))
        now = datetime.now(jst)
        today_str = now.strftime('%Y-%m-%d')
        # 令和の計算
        r_year = now.year - 2018
        last_r = r_year - 1
        last_w = now.year - 1
        
        return f"""あなたは自治体案件の精査プロです。今日: {today_str} (令和{r_year}年)

# 🚨 絶対除外ルール (Label C)
1. **過去年度**: タイトルや本文が「令和{last_r}年({last_w})」以前の募集。
2. **ノイズ**: 「質問回答(Q&A)」「選定結果」「入札結果」のページ。
3. **期限切れ**: 締切が今日({today_str})より前の日付。
4. **令和{r_year}年の不在**: 本文に令和{r_year}年(2026)以降の具体的な日付が一切ない過去の残骸。

# 判定基準
- **Label A**: 映像制作・動画作成・配信等が主業務。
- **Label B**: 広報やイベントの一部に映像制作が含まれる。

# 出力形式 (JSON)
{{
  "label": "A, B, または C",
  "title": "案件名",
  "source_url": "提供された情報のURL", 
  "deadline_apply": "参加申込の締切日 YYYY-MM-DD (不明時は 不明)",
  "deadline_prop": "YYYY-MM-DD (不明時は 不明)",
  "evidence": "映像制作の必要性と現在募集中である根拠",
  "memo": "令和{r_year}年度案件、等の詳細ステータス"
}}

---
件名: {title}
内容: {content[:13000]}
"""

    def make_batch_request(self, custom_id: str, title: str, content: str) -> Dict:
        return {
            "custom_id": custom_id,
            "params": {
                "model": self.model,
                "max_tokens": 1000,
                "temperature": 0,
                "messages": [{"role": "user", "content": self.get_prompt(title, content)}]
            }
        }
