"""Claude APIを使用したコンテンツ解析（ねじれ解消・2026年最新対応版）"""

import logging
import json
import os
import re
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY が設定されていません")
        
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
            # 環境変数があれば使用、なければ最新のSonnetを指定
            self.model = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
            logger.info(f"AIAnalyzer初期化完了（モデル: {self.model}）")
        except ImportError:
            raise

    def analyze_project(self, content_data: Dict) -> Optional[Dict]:
        """案件を解析し、要件に基づいた情報を抽出する"""
        title = content_data.get('title', '')
        content = content_data.get('content', '')
        url = content_data.get('url', '')

        if not content or len(content.strip()) < 50:
            return None

        # 要件に基づいたプロンプト
        prompt = f"""以下の行政文書を分析してください。
**タイトル**: {title}
**本文（抜粋）**: {content[:3000]}

---
【判定・抽出ルール】
1. **映像案件判定**: 映像制作、PR動画、撮影、配信等の募集案件なら is_video_project を true に。単なる結果報告やアーカイブは false。
2. **都道府県の特定**: 本文の内容から「実際に発注している都道府県名」を特定してください（重要）。
3. **要約**: 案件内容を3行程度で要約してください。
4. **締切**: 締切日を YYYY-MM-DD 形式で抽出。西暦・和暦を変換してください。不明なら「不明」。
5. **URL**: 申込先や資料URLが本文にあれば抽出、なければ {url} を使用。

以下のJSON形式でのみ回答してください:
{{
  "prefecture": "特定した都道府県名",
  "is_video_project": true/false,
  "title": "正確な案件名",
  "summary": "案件の3行要約",
  "deadline": "YYYY-MM-DD または 不明",
  "application_url": "URL"
}}
"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            # JSON部分を抽出して解析
            res_text = response.content[0].text
            json_match = re.search(r'\{.*\}', res_text, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                # is_video_projectがtrueのものだけを返す（要件1）
                return result if result.get('is_video_project') == True else None
            return None
        except Exception as e:
            logger.error(f"AI解析エラー: {e}")
            return None
