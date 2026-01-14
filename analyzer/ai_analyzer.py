"""Claude APIを使用したコンテンツ解析（厳格判定版）"""

import logging
import json
import os
from typing import Dict, Optional
import re

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """Claude APIによるコンテンツ解析クラス（厳格判定版）"""
    
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY が設定されていません")
        
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
            self.model = "claude-3-5-sonnet-20241022"
            logger.info("AIAnalyzer初期化完了（厳格判定版）")
        except ImportError:
            logger.error("anthropic パッケージが利用できません")
            raise
    
    def analyze_project(self, content_data: Dict) -> Optional[Dict]:
        """案件コンテンツを解析（厳格版）"""
        title = content_data.get('title', '')
        content = content_data.get('content', '')
        url = content_data.get('url', '')
        
        # コンテンツチェック
        if not content or len(content.strip()) < 100:
            logger.warning(f"コンテンツ不十分（{len(content)}文字）: {title[:50]}")
            return None
        
        # 明らかに関係ないキーワードで除外
        exclude_keywords = [
            '審査結果', '落札結果', '契約締結', '実績紹介', 
            '事例紹介', '過去の', 'アーカイブ', 'セミナー',
            'カフェ', '募集要項', '応募フォーム'
        ]
        
        combined_text = title + ' ' + content[:500]
        if any(keyword in combined_text for keyword in exclude_keywords):
            logger.info(f"除外キーワード検出 → スキップ: {title[:50]}")
            return None
        
        # 必須キーワードチェック（タイトルまたはコンテンツ）
        required_keywords = ['映像', '動画', 'ビデオ', '撮影', 'プロモーション', 'PR', 'コンテンツ制作']
        has_required = any(kw in combined_text for kw in required_keywords)
        
        if not has_required:
            logger.info(f"必須キーワードなし → スキップ: {title[:50]}")
            return None
        
        # 行政案件キーワードチェック
        admin_keywords = ['入札', '公募', '調達', '委託', '募集', '業務', '契約']
        has_admin = any(kw in combined_text for kw in admin_keywords)
        
        if not has_admin:
            logger.info(f"行政案件キーワードなし → スキップ: {title[:50]}")
            return None
        
        # コンテンツを8000文字に制限
        if len(content) > 8000:
            content = content[:8000] + "\n...(省略)"
        
        # AI判定
        logger.info(f"AI判定開始: {title[:50]}")
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
            
            if result:
                is_video = result.get('is_video_project', False)
                logger.info(f"AI判定結果: {title[:30]}... → {is_video}")
                return result if is_video else None
            
        except Exception as e:
            logger.error(f"AI解析エラー: {e}")
            return None
        
        return None
    
    def _build_prompt(self, title: str, content: str, url: str) -> str:
        """プロンプト構築（厳格版）"""
        return f"""以下の行政文書を厳密に分析してください。

**タイトル**: {title}
**URL**: {url}

**本文（抜粋）**:
{content[:1500]}

---

この文書が以下の条件を**すべて満たす**映像制作案件か判定してください：

✅ **必須条件（すべて満たす必要あり）:**
1. 映像制作・動画制作・撮影・編集などが**主要な業務内容**である
2. 入札公告・公募・委託業務・調達案件など、**発注者が業者を募集している**
3. まだ募集中、またはこれから募集する案件である

❌ **以下は必ず除外:**
- 審査結果・落札結果・契約締結の発表
- 過去の実績・事例の紹介
- 完了した案件の報告書
- イベント・セミナー・カフェの告知
- 単なる情報提供・お知らせ
- 映像視聴ページ・動画配信ページ

**厳格な判定基準:**
- タイトルだけでなく、本文を必ず読んで判断する
- 「映像制作」というキーワードがあっても、結果発表や事例紹介なら false
- 少しでも疑わしい、または情報不足なら false
- **確実に映像制作の発注案件のみ true**

以下のJSON形式で回答してください:

{{
  "is_video_project": true,
  "summary": "発注する業務内容を具体的に（例：観光PR動画の企画・撮影・編集）",
  "deadline": "YYYY-MM-DD形式の締切日（本文中に見つからない場合は'不明'）",
  "application_url": "仕様書ダウンロードまたは申込ページのURL（なければ空文字）",
  "confidence": "高/中/低",
  "project_type": "具体的な案件種別（例：観光プロモーション映像制作）"
}}

JSON以外の文字は含めないでください。
"""
    
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
            
            # デフォルト値設定
            result.setdefault('deadline', '不明')
            result.setdefault('application_url', '')
            result.setdefault('confidence', '中')
            result.setdefault('project_type', '映像制作関連')
            result.setdefault('summary', '詳細情報を確認してください')
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析エラー: {e}")
            logger.debug(f"レスポンス内容: {response_text[:300]}")
            return None
        except Exception as e:
            logger.error(f"レスポンス処理エラー: {e}")
            return None
    
    def batch_analyze(self, content_list: list) -> list:
        """複数コンテンツを一括解析"""
        results = []
        
        logger.info(f"🎬 AI解析開始（厳格判定）: {len(content_list)}件を処理")
        
        for idx, content_data in enumerate(content_list, 1):
            logger.info(f"📊 解析進捗: {idx}/{len(content_list)}")
            
            analysis = self.analyze_project(content_data)
            
            if analysis and analysis.get('is_video_project'):
                merged_result = {**content_data, **analysis}
                results.append(merged_result)
                logger.info(f"✅ 採用: {content_data.get('title', '')[:50]}")
            else:
                logger.debug(f"⏭️  スキップ: {content_data.get('title', '')[:50]}")
        
        logger.info(f"🎯 映像案件抽出完了: {len(results)}/{len(content_list)}件（採用率: {len(results)/len(content_list)*100:.1f}%）")
        return results
