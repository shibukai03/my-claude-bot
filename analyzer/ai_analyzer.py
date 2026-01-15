"""Claude APIを使用したコンテンツ解析（バランス版・モデル修正）"""

import logging
import json
import os
from typing import Dict, Optional
import re

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """Claude APIによるコンテンツ解析クラス（バランス版）"""
    
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY が設定されていません")
        
        try:
            from anthropic import Anthropic
            self.client = Anthropic(api_key=api_key)
            self.model = "claude-sonnet-4-20250514"  # ← 修正！最新モデル
            logger.info(f"AIAnalyzer初期化完了（モデル: {self.model}）")
        except ImportError:
            logger.error("anthropic パッケージが利用できません")
            raise
    
    def analyze_project(self, content_data: Dict) -> Optional[Dict]:
        """案件コンテンツを解析（バランス版）"""
        title = content_data.get('title', '')
        content = content_data.get('content', '')
        url = content_data.get('url', '')
        
        # 最低限のコンテンツチェック
        if not content or len(content.strip()) < 50:
            logger.debug(f"コンテンツ不十分（{len(content)}文字）: {title[:50]}")
            return None
        
        # 明確に除外すべきキーワード（結果発表など）
        strong_exclude = [
            '審査結果', '落札結果', '契約締結結果', '選定結果',
            '受賞者', '入賞者', '結果について', '結果の公表'
        ]
        
        combined_text = title + ' ' + content[:500]
        
        if any(keyword in combined_text for keyword in strong_exclude):
            logger.info(f"❌ 結果発表系 → 除外: {title[:50]}")
            return None
        
        # 映像関連キーワード（広めに設定）
        video_keywords = [
            '映像', '動画', 'ビデオ', '撮影', 'プロモーション', 'PR',
            '制作', '広報', 'Web', 'コンテンツ', '配信', 'SNS',
            'YouTube', 'オンライン', '記録', 'デジタル'
        ]
        
        # タイトルまたはコンテンツの冒頭500文字に1つでもあればOK
        has_video_keyword = any(kw in combined_text for kw in video_keywords)
        
        if not has_video_keyword:
            logger.debug(f"映像関連キーワードなし: {title[:50]}")
            return None
        
        logger.info(f"🎬 AI判定対象: {title[:50]}")
        
        # コンテンツを8000文字に制限
        if len(content) > 8000:
            content = content[:8000] + "\n...(省略)"
        
        # AI判定
        prompt = self._build_prompt(title, content, url)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2
            )
            
            response_text = response.content[0].text
            result = self._parse_response(response_text)
            
            if result:
                is_video = result.get('is_video_project', False)
                
                if is_video:
                    logger.info(f"✅ AI判定: 映像案件 - {title[:40]}")
                else:
                    logger.info(f"⏭️  AI判定: 非該当 - {title[:40]}")
                
                return result if is_video else None
            
        except Exception as e:
            logger.error(f"AI解析エラー: {e}")
            
            # エラー時は寛容に判定（タイトルに明確なキーワードがあれば採用）
            priority_keywords = ['映像制作', '動画制作', 'ビデオ制作', '撮影業務']
            if any(kw in title for kw in priority_keywords):
                logger.info(f"✅ エラー時救済採用: {title[:50]}")
                return {
                    'is_video_project': True,
                    'summary': f"{title}（エラー時判定）",
                    'deadline': '不明',
                    'application_url': url,
                    'confidence': '低',
                    'project_type': 'エラー時判定'
                }
        
        return None
    
    def _build_prompt(self, title: str, content: str, url: str) -> str:
        """プロンプト構築（バランス版）"""
        return f"""以下の行政文書を分析してください。

**タイトル**: {title}
**URL**: {url}

**本文（抜粋）**:
{content[:2000]}

---

この文書が「映像制作・動画制作・撮影・編集などの発注案件」か判定してください。

✅ **該当する例:**
- 観光PR映像の制作委託
- イベント記録撮影業務
- プロモーション動画制作
- Web動画コンテンツ制作
- 広報映像制作

❌ **該当しない例:**
- 審査結果・落札結果の発表
- 過去の実績紹介・事例紹介
- 単なるイベント告知
- 映像視聴ページ

**判定基準:**
- タイトルと本文を総合的に判断
- 発注・委託・募集などの要素があるか
- 迷ったら「該当する」寄りで判定（見逃さない）

以下のJSON形式で回答:

{{
 "is_video_project": true,
  "summary": "業務内容を1-2行で（例：観光地紹介動画の企画・撮影・編集）",
  "deadline": "YYYY-MM-DD または 不明",
  "application_url": "申込フォームURL、仕様書ダウンロードURL、または問い合わせページURL（本文中に明記されている場合のみ）",
  "confidence": "高/中/低",
  "project_type": "具体的な種別"
}}
"""
    
    def _parse_response(self, response_text: str) -> Optional[Dict]:
        """レスポンスからJSON抽出"""
        try:
            json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
            else:
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    return None
            
            result = json.loads(json_str)
            
            # デフォルト値設定
            result.setdefault('deadline', '不明')
            result.setdefault('application_url', '')
            result.setdefault('confidence', '中')
            result.setdefault('project_type', '映像制作関連')
            result.setdefault('summary', '詳細情報を確認してください')
            
            return result
            
        except Exception as e:
            logger.error(f"JSON解析エラー: {e}")
            return None
    
    def batch_analyze(self, content_list: list) -> list:
        """複数コンテンツを一括解析"""
        results = []
        
        logger.info(f"🎬 AI解析開始（バランス版）: {len(content_list)}件を処理")
        
        for idx, content_data in enumerate(content_list, 1):
            if idx % 10 == 0:
                logger.info(f"📊 解析進捗: {idx}/{len(content_list)}")
            
            analysis = self.analyze_project(content_data)
            
            if analysis and analysis.get('is_video_project'):
                merged_result = {**content_data, **analysis}
                results.append(merged_result)
        
        logger.info(f"🎯 映像案件抽出完了: {len(results)}/{len(content_list)}件（採用率: {len(results)/len(content_list)*100:.1f}%）")
        return results
