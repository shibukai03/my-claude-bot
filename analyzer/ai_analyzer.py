import logging
import json
import os
import re
from typing import Dict, Optional
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY が設定されていません")
        
        self.client = Anthropic(api_key=api_key)
        self.model = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
        logger.info(f"AI深層解析ユニット起動完了（モデル: {self.model}）")

    def analyze_project(self, content_data: Dict) -> Optional[Dict]:
        title = content_data.get('title', '')
        content = content_data.get('content') or content_data.get('text') or ''
        url = content_data.get('url', '')

        if not content or len(content.strip()) < 50:
            return None

        # --- 今日の日付を動的に取得 ---
        from datetime import datetime, timezone, timedelta
        jst = timezone(timedelta(hours=9))
        today_str = datetime.now(jst).strftime('%Y-%m-%d')

        prompt = f"""あなたは自治体案件の精査官です。
今日の日付は **{today_str}** です。
提供されたテキストから情報を抜き出してください。和暦（令和・R）は必ず西暦に変換してください。

### 【最優先ルール：終了案件は即Label C】
以下のいずれかに該当する場合は、映像制作の有無に関わらず、必ず **Label C (除外)** と判定してください。
1. **終了の明記**: 「審査結果」「結果の公表」「委託候補者の決定」「落札者決定」「特定されました」「募集は終了しました」「受付終了」という文言がある。
2. **過去の日付**: 締切日が今日（{today_str}）より1日でも前の日付である。
3. **アーカイブ情報**: 提供テキストが過去の公告一覧や質問回答のみであり、現在進行中の募集要項ではない。

### 日付抽出と和暦変換の掟
- 令和7年(R7) = 2025年 / 令和8年(R8) = 2026年
- 文中の「令和○年○月○日」や「R○.○.○」を必ず西暦（YYYY-MM-DD）に変換すること。
- **「不明」と答える前に、テキスト内の「期限」「締切」「日程」「提出」の周辺を徹底的に探してください。**

### ラベル判定基準
- Label A: 現在募集中で、映像制作が必須。
- Label B: 現在募集中で、映像制作の可能性が高い。
- Label C: 終了済み、または映像制作に関連しない。

---
**解析対象タイトル**: {title}
**テキストデータ**:
{content[:15000]} 

---
### 出力形式 (JSON)
{{
  "label": "A, B, または C",
  "title": "正確な案件名",
  "deadline_prop": "YYYY-MM-DD (和暦は必ず西暦に変換。見つからない場合のみ不明)",
  "evidence": "映像制作の必要性、または終了・落札等と判断した具体的な文言の引用",
  "memo": "現在のステータスを詳細に記載（例：〇〇に決定済み、令和7年〇月締切、など）"
}}
"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
                temperature=0
            )
            res_text = response.content[0].text
            json_match = re.search(r'\{.*\}', res_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                result['source_url'] = url
                return result
            return None
        except Exception as e:
            logger.error(f"Sonnet解析エラー: {e}")
            return None
