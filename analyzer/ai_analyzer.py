import logging
import json
import os
import re
import time
from typing import Dict, Optional
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        # あなたの指定通り getenv で取得
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY が設定されていません")
        
        self.client = Anthropic(api_key=api_key)
        # 最も安定している Sonnet v2 を指定
        self.model = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
        logger.info(f"AI深層解析ユニット起動完了（モデル: {self.model}）")

    def analyze_project(self, content_data: Dict) -> Optional[Dict]:
        """大量のテキスト（PDF全ページ分）から映像案件を精密に抽出する"""
        title = content_data.get('title', '')
        content = content_data.get('content') or content_data.get('text') or ''
        url = content_data.get('url', '')

        if not content or len(content.strip()) < 50:
            return None

        # --- プロンプト強化ポイント ---
        # 15,000文字まで解析範囲を拡大し、スキャン手順をAIに指示
        prompt = f"""あなたは自治体の仕様書・実施要領を隅々まで精査するプロのリサーチアナリストです。
提示された【解析対象テキスト】は、複数のPDFページを結合した非常に長い文書です。
以下の手順で慎重に分析し、指定のJSON形式で回答してください。

### 解析の手順
1. 文書全体をスキャンし、「映像制作」「動画作成」「CM」「撮影」「配信」「YouTube」「PR動画」というキーワードが含まれる箇所を特定してください。
2. その記述が「必須要件（A）」か「選択肢/可能性がある（B）」か、あるいは「単なる過去実績や無関係な記述（C）」かを厳格に判定してください。
3. 判定の根拠となった一文を必ず「evidence」欄に引用してください。
4. 予算、納期、3つの締切（申込・質問・提案）を文書の全ページから探し出してください。

---
**解析対象タイトル**: {title}
**解析対象テキスト（全容）**:
{content[:15000]} 

---
### 出力形式 (JSON)
必ず以下のJSON形式でのみ回答してください。推測が混じる場合は「不明」としてください。
{{
  "label": "A, B, または C",
  "title": "正確な案件名",
  "prefecture": "都道府県名",
  "method": "入札/プロポ等",
  "budget": "予定価格/上限",
  "period": "履行期間",
  "deadline_app": "YYYY-MM-DD",
  "deadline_ques": "YYYY-MM-DD",
  "deadline_prop": "YYYY-MM-DD",
  "evidence": "映像制作の必要性が確認できる一文を直接引用",
  "tag": "ジャンル",
  "memo": "特記事項"
}}
"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
                temperature=0 # 抽出精度を上げるため固定
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
