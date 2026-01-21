import logging
import json
import os
import re
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY が設定されていません")
        
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
        logger.info(f"AI解析ユニット(Batch/基準拡大版)起動完了")

    def get_prompt(self, title: str, content: str) -> str:
        from datetime import datetime, timezone, timedelta
        jst = timezone(timedelta(hours=9))
        today_str = datetime.now(jst).strftime('%Y-%m-%d')

        return f"""あなたは自治体案件の精査官です。今日の日付は **{today_str}** です。
和暦（令和・R）は必ず西暦に変換してください。

### 【判定基準：映像・動画・配信を広くカバー】
- **Label A (確定)**: 現在募集中で、以下のいずれかが「主業務」または「必須要素」である。
  （動画制作、映像作成、ライブ配信、撮影、CM制作、YouTube活用、動画広告運用、サイネージ映像等）
- **Label B (可能性あり)**: 現在募集中で、広報・イベント・プロモーション等の業務内容に、上記（動画制作や配信等）が含まれる可能性が極めて高い。
- **Label C (除外)**: 映像・動画に関連しない。または、以下の【鉄の掟】に該当する場合。

### 【鉄の掟：終了案件は即Label C】
以下のいずれかに該当する場合は内容に関わらず必ず **Label C (除外)** としてください。
1. 終了文言: 「審査結果」「結果の公表」「候補者決定」「落札者決定」「募集終了」「受付終了」がある。
2. 過去日付: 締切日が今日（{today_str}）より1日でも前の日付である。
3. アーカイブ: 提供テキストが過去の結果一覧であり、現在進行中の募集要項ではない。

---
解析対象タイトル: {title}
テキストデータ:
{content[:12000]} 

---
### 出力形式 (JSON)
{{
  "label": "A, B, または C",
  "title": "正確な案件名",
  "deadline_prop": "YYYY-MM-DD (和暦は必ず西暦に変換。見つからない場合は死ぬ気で探し、それでも無理なら不明と回答)",
  "evidence": "映像制作・配信の必要性、または終了済みと判断した一文を引用",
  "memo": "ステータス詳細（例：募集中、〇月〇日締切、など）"
}}
"""

    def make_batch_request(self, custom_id: str, title: str, content: str) -> Dict:
        return {
            "custom_id": custom_id,
            "params": {
                "model": self.model,
                "max_tokens": 1500,
                "temperature": 0,
                "messages": [{"role": "user", "content": self.get_prompt(title, content)}]
            }
        }
