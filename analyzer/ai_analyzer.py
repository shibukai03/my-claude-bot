import logging
import json
import os
import re
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        # 以前のコードと同じ環境変数の読み込み方式
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY が設定されていません")
        
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        # GitHub Secrets の設定を優先し、なければ Sonnet を使用
        self.model = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
        logger.info(f"AI解析ユニット初期化完了（モデル: {self.model}）")

    def analyze_project(self, content_data: Dict) -> Optional[Dict]:
        """案件を解析し、v1.2の要件に基づいた情報を抽出する"""
        title = content_data.get('title', '')
        # content または text どちらからでも取得できるように修正
        content = content_data.get('content') or content_data.get('text') or ''
        url = content_data.get('url', '')

        if not content or len(content.strip()) < 50:
            return None

        # 指示書 v1.2 の内容を「以前のコード」と同じ形式のプロンプトに統合
        prompt = f"""あなたは公的機関の映像制作案件を精査するリサーチアナリストです。
以下のテキストを分析し、指定のJSON形式で回答してください。推測は禁止です。

**解析対象タイトル**: {title}
**本文（抜粋）**: {content[:5000]}

---
【判定・抽出ルール (v1.2)】
1. **ラベリング**: 
   - A：確定（動画制作が必須。尺・本数・工程が明確）
   - B：候補（動画が含まれる可能性が高いが、必須と断定できない）
   - C：除外（募集終了、結果発表、物品購入、動画要件なし）
2. **証拠(Evidence)**: なぜそのラベルにしたのか、本文から短い証拠文言を引用してください。
3. **都道府県**: 発注している都道府県/市区町村名を特定。
4. **予算・締切**: 予定価格、参加申込締切(YYYY-MM-DD)等を抽出。不明なら「不明」。

以下のJSON形式でのみ回答してください:
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
  "evidence": "映像要件の根拠(短い引用)",
  "tag": "観光PR/採用等",
  "memo": "B判定理由など"
}}
"""
        try:
            # 以前のコードと同じ API 呼び出し構造
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            res_text = response.content[0].text
            json_match = re.search(r'\{.*\}', res_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                # 申込先URLを追加
                result['source_url'] = url
                return result
            return None
        except Exception as e:
            logger.error(f"AI解析エラー: {e}")
            return None
