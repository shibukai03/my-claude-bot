"""Claude APIを使用したコンテンツ解析"""

import logging
import json
import os
from typing import Dict, Optional
import re

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """Claude APIによるコンテンツ解析クラス"""
    
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY が設定されていません")
        
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
            self.model = "claude-3-5-sonnet-20241022"
            logger.info("AIAnalyzer初期化完了")
        except ImportError:
            logger.error("anthropic パッケージが利用できません")
            raise
    
    def analyze_project(self, content_data: Dict) -> Optional[Dict]:
        """案件コンテンツを解析"""
        title = content_data.get('title', '')
        content = content_data.get('content', '')
        
        if not content or len(content.strip()) < 50:
            logger.warning("コンテンツが不十分です")
            return None
        
        # コンテンツを15000文字に制限
        if len(content) > 15000:
            content = content[:15000] + "\n...(省略)"
        
        prompt = f"""以下の文書を分析し、JSON形式で回答してください。

**タイトル**: {title}

**本文**:
{content}

---

以下の情報を抽出し、JSON形式のみで回答してください。

1. is_video_project (boolean): 映像制作・動画制作・撮影案件か？
2. summary (string): 3行以内の要約
3. deadline (string): 締切日時（YYYY-MM-DD形式、不明なら"不明"）
4. application_url (string): 申込URLまたは""
5. confidence (string): "高"/"中"/"低"
6. project_type (string): 案件種別

回答形式（このJSONのみを返してください）:
{{
  "is_video_project": true,
  "summary": "要約文",
  "deadline": "2024-03-15",
  "application_url": "",
  "confidence": "高",
  "project_type": "プロモーション映像制作"
}}
"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            response_text = response.content[0].text
            result = self._parse_response(response_text)
            
            if result:
                logger.info(f"解析完了: is_video={result['is_video_project']}")
                return result
            
        except Exception as e:
            logger.error(f"AI解析エラー: {e}")
        
        return None
    
    def _parse_response(self, response_text: str) -> Optional[Dict]:
        """レスポンスからJSON抽出"""
        try:
            # JSONブロック抽出
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    logger.error("JSON形式が見つかりません")
                    return None
            
            result = json.loads(json_str)
            
            # 必須フィールドチェック
            required_fields = ['is_video_project', 'summary', 'deadline', 'application_url']
            for field in required_fields:
                if field not in result:
                    logger.error(f"必須フィールド '{field}' がありません")
                    return None
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析エラー: {e}")
            return None
        except Exception as e:
            logger.error(f"レスポンス処理エラー: {e}")
            return None
    
    def batch_analyze(self, content_list: list) -> list:
        """複数コンテンツを一括解析"""
        results = []
        
        for idx, content_data in enumerate(content_list, 1):
            logger.info(f"解析進捗: {idx}/{len(content_list)}")
            
            analysis = self.analyze_project(content_data)
            
            if analysis and analysis.get('is_video_project'):
                merged_result = {**content_data, **analysis}
                results.append(merged_result)
            else:
                logger.info(f"映像案件ではないためスキップ")
        
        logger.info(f"映像案件抽出完了: {len(results)}/{len(content_list)}件")
        return results
