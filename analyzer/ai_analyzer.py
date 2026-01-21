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
        """大量のテキストから『現在募集中の映像案件』のみを精密に抽出する"""
        title = content_data.get('title', '')
        content = content_data.get('content') or content_data.get('text') or ''
        url = content_data.get('url', '')

        if not content or len(content.strip()) < 50:
            return None

        # --- プロンプト強化：終了案件排除ロジック搭載 ---
        prompt = f"""あなたは自治体の仕様書・実施要領を精査するプロのアナリストです。
提示された【解析対象テキスト】から、現在募集中の映像制作案件のみを特定してください。

### 解析の最優先ルール（終了案件の徹底排除）
以下のいずれかに該当する場合、どんなに内容が良くても必ず **Label C (除外)** と判定してください。
1. **ステータス判断**: タイトルや本文に「審査結果」「特定されました」「選定結果」「落札者決定」「契約候補者の決定」「募集終了」という言葉がある場合。
2. **期限判断**: 締切日（参加申込や提案書提出）が、今日（2026年1月21日）よりも過去の日付である場合。
3. **内容不足**: 単なる過去のアーカイブ記事や、質問回答集のみで募集要項が含まれない場合。

### ラベル判定基準
- **Label A (確定)**: 現在「募集中」であり、動画制作、映像作成、ライブ配信、撮影が必須要件である。
- **Label B (可能性あり)**: 現在「募集中」であり、プロモーション等の業務内容に動画制作が含まれる可能性が極めて高い。
- **Label C (除外)**: 上記の終了案件、または映像制作に関連しない案件。

---
**解析対象タイトル**: {title}
**解析対象テキスト（15,000文字）**:
{content[:15000]} 

---
### 出力形式 (JSON)
必ず以下のJSON形式でのみ回答してください。
注意：有効なJSONであることを厳守し、末尾のカンマ、波括弧の閉じ忘れ、文字列内の不適切な改行がないよう、慎重に出力してください。回答の冒頭に説明文を入れず、{{ から始めて }} で終わってください。

{{
  "label": "A, B, または C",
  "title": "正確な案件名",
  "prefecture": "都道府県名",
  "method": "入札/プロポ等",
  "budget": "予算上限(数字と通貨)",
  "period": "履行期間",
  "deadline_app": "YYYY-MM-DD (不明な場合は不明)",
  "deadline_ques": "YYYY-MM-DD (不明な場合は不明)",
  "deadline_prop": "YYYY-MM-DD (不明な場合は不明)",
  "evidence": "映像制作の必要性、または終了・落札等の判断根拠となった一文を直接引用",
  "tag": "ジャンル(観光,採用,広報等)",
  "memo": "特記事項(審査結果掲載済みの場合はその旨を記載)"
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
