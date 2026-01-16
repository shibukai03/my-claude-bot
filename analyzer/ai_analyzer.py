"""Claude APIを使用したコンテンツ解析（2026年最新モデル対応版）"""

import logging
import json
import os
from typing import Dict, Optional
import re

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY が設定されていません")
        
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
            # --- ここを修正：2026年環境で動作する最新モデル名に戻しました ---
            self.model = os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
            logger.info(f"AIAnalyzer初期化完了（モデル: {self.model}）")
        except ImportError:
            logger.error("anthropic パッケージが利用できません")
            raise
    
    def analyze_project(self, content_data: Dict) -> Optional[Dict]:
        """案件コンテンツを解析"""
        title = content_data.get('title', '')
        content = content_data.get('content', '')
        url = content_data.get('url', '')
        
        if not content or len(content.strip()) < 50:
            return None
        
        prompt = self._build_prompt(title, content, url)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            response_text = response.content[0].text
            result = self._parse_response(response_text)
            
            if result and result.get('is_video_project'):
                return result
            
        except Exception as e:
            logger.error(f"AI解析エラー: {e}")
        
        return None
    
    def _build_prompt(self, title: str, content: str, url: str) -> str:
        """プロンプト構築（ねじれ防止・日付フィルタ強化）"""
        return f"""以下の行政文書を分析してください。

**タイトル**: {title}
**URL**: {url}
**本文（抜粋）**:
{content[:3000]}

---
【分析ルール】
1. この文書が、行政による「映像制作・動画制作・PR動画・撮影・ライブ配信」の【民間委託（入札・公募型プロポ）】に関する最新募集か判定してください。
2. **重要**: 検索結果のラベルに関わらず、本文の内容から「実際に発注している都道府県名」を特定してください。
3. すでに募集が終了した結果発表や、単なる事例紹介、締切が不明なアーカイブは `is_video_project: false` としてください。

【抽出情報】
- prefecture: 発注元の正しい都道府県名（例：岩手県）
- is_video_project: 映像制作の新規案件募集であり、かつ締切が「2026年1月16日以降」なら true
- deadline: 締切日を YYYY-MM-DD 形式で。令和7年は2025、令和8年は2026。不明なら "不明"。

以下のJSON形式でのみ回答してください:
{{
  "prefecture": "特定した都道府県名",
  "is_video_project": true/false,
  "title": "正確な案件名",
  "summary": "案件の内容（2行程度）",
  "deadline": "YYYY-MM-DD または 不明",
  "application_url": "募集ページまたは仕様書のURL",
  "project_type": "映像制作関連"
}}
"""

    def _parse_response(self, response_text: str) -> Optional[Dict]:
        try:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            return None
        except Exception as e:
            logger.error(f"JSON解析エラー: {e}")
            return None

    def batch_analyze(self, content_list: list) -> list:
        results = []
        for content_data in content_list:
            analysis = self.analyze_project(content_data)
            if analysis:
                analysis['url'] = content_data.get('url')
                results.append(analysis)
        return results
