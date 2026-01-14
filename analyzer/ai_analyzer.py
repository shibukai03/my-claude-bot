"""Claude APIを使用したコンテンツ解析（判定緩和版）"""

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
        """案件コンテンツを解析（緩和版）"""
        title = content_data.get('title', '')
        content = content_data.get('content', '')
        url = content_data.get('url', '')
        
        # タイトルに映像関連キーワードがあれば優先的に採用
        priority_keywords = ['映像', '動画', 'ビデオ', 'プロモーション', 'PR', '撮影', 'コンテンツ']
        has_priority_keyword = any(keyword in title for keyword in priority_keywords)
        
        if not content or len(content.strip()) < 30:
            logger.warning(f"コンテンツが不十分: {title}")
            # タイトルだけでも判定
            if has_priority_keyword:
                logger.info(f"タイトルに優先キーワードあり、採用: {title}")
                return {
                    'is_video_project': True,
                    'summary': f"{title}に関する案件",
                    'deadline': '不明',
                    'application_url': url,
                    'confidence': '中',
                    'project_type': 'タイトルから判定'
                }
            return None
        
        # コンテンツを10000文字に制限
        if len(content) > 10000:
            content = content[:10000] + "\n...(省略)"
        
        prompt = f"""以下の文書を分析してください。

**タイトル**: {title}
**URL**: {url}

**本文（抜粋）**:
{content[:1000]}

---

この文書が「映像制作・動画制作・撮影・プロモーション映像・デジタルコンテンツ・配信」などに関連する案件かどうか判定してください。

**重要な判定基準:**
1. タイトルや本文に「映像」「動画」「ビデオ」「撮影」「プロモーション」「PR」「コンテンツ」などのキーワードがあれば、基本的に該当とみなす
2. 観光PR、イベント記録、広報活動なども映像制作案件として扱う
3. 疑わしい場合は「該当する」と判定する（寛容に判定）

以下のJSON形式で回答してください:

{{
  "is_video_project": true or false,
  "summary": "1-2行の簡潔な要約",
  "deadline": "YYYY-MM-DD形式（不明なら'不明'）",
  "application_url": "申込URLまたは空文字",
  "confidence": "高/中/低",
  "project_type": "案件の種類"
}}

JSON以外の文字は含めないでください。
"""
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            
            response_text = response.content[0].text
            result = self._parse_response(response_text)
            
            if result:
                # タイトルに優先キーワードがあれば、falseでも強制的にtrueに
                if has_priority_keyword and not result.get('is_video_project'):
                    logger.info(f"タイトルに優先キーワードあり、強制採用: {title}")
                    result['is_video_project'] = True
                    result['confidence'] = '中'
                
                logger.info(f"解析完了: {title[:30]}... → is_video={result['is_video_project']}")
                return result
            
        except Exception as e:
            logger.error(f"AI解析エラー: {e}")
            
            # エラー時、タイトルで判定
            if has_priority_keyword:
                logger.info(f"エラーだがタイトルで採用: {title}")
                return {
                    'is_video_project': True,
                    'summary': f"{title}に関する案件（エラー時判定）",
                    'deadline': '不明',
                    'application_url': url,
                    'confidence': '低',
                    'project_type': 'タイトルから判定'
                }
        
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
            required_fields = ['is_video_project', 'summary']
            for field in required_fields:
                if field not in result:
                    logger.error(f"必須フィールド '{field}' がありません")
                    return None
            
            # デフォルト値設定
            result.setdefault('deadline', '不明')
            result.setdefault('application_url', '')
            result.setdefault('confidence', '中')
            result.setdefault('project_type', '映像制作関連')
            
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
                logger.info(f"✓ 採用: {content_data.get('title', '')[:50]}")
            else:
                logger.debug(f"スキップ: {content_data.get('title', '')[:50]}")
        
        logger.info(f"映像案件抽出完了: {len(results)}/{len(content_list)}件")
        return results
