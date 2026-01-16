"""Claude APIを使用したコンテンツ解析（ねじれ解消・2026年最新対応版）"""

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
            # 環境変数があればそれを使用し、なければ安定版モデルを使用します
            self.model = os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
            logger.info(f"AIAnalyzer初期化完了（モデル: {self.model}）")
        except ImportError:
            logger.error("anthropic パッケージが利用できません")
            raise
    
    def analyze_project(self, content_data: Dict) -> Optional[Dict]:
        """案件コンテンツを解析し、正しい県名と締切を特定する"""
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
            
            result = self._parse_response(response.content[0].text)
            
            if result and result.get('is_video_project'):
                # 検索時のラベルではなく、AIが特定した本当の県名を優先します
                return result
            
        except Exception as e:
            logger.error(f"AI解析エラー: {e}")
        
        return None
    
    def _build_prompt(self, title: str, content: str, url: str) -> str:
        return f"""以下の行政文書を分析し、映像制作に関連する【民間委託の募集】か判定してください。

**タイトル**: {title}
**URL**: {url}
**本文（抜粋）**:
{content[:3000]}

---
【分析の絶対ルール】
1. **都道府県の特定**: サイトの場所に関わらず、本文の内容から「実際に発注している都道府県名」を特定してください。
2. **最新性の判定**: 既に終了した「結果発表」や「過去のアーカイブ」は false としてください。
3. **映像案件の定義**: 動画制作、撮影、ライブ配信、PR映像制作などが含まれる募集を true としてください。

以下のJSON形式でのみ回答してください:
{{
  "prefecture": "特定した都道府県名（例：岩手県）",
  "is_video_project": true/false,
  "title": "正確な案件名",
  "summary": "業務内容の簡潔な要約",
  "deadline": "YYYY-MM-DD形式（不明なら 不明 と記載）",
  "application_url": "募集詳細または資料があるURL"
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
        logger.info(f"🎬 AI解析開始（精度重視）: {len(content_list)}件を処理")
        for content_data in content_list:
            analysis = self.analyze_project(content_data)
            if analysis:
                analysis['url'] = content_data.get('url')
                results.append(analysis)
        return results
