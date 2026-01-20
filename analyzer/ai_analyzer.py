import logging
import os
import json
import time
from anthropic import Anthropic

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        # APIキーをgetenvで取得（GitHub Secretsの ANTHROPIC_API_KEY を使用）
        api_key = os.getenv('ANTHROPIC_API_KEY')
        self.client = Anthropic(api_key=api_key)
        
        # モデル名は変数を介さず、確実に存在する正式IDを直接指定します
        # これにより 404 Not Found エラーを完全に防ぎます
        self.model = "claude-3-5-sonnet-20241022"
        
        logger.info(f"AI解析ユニット起動中... (Model: {self.model})")

    def analyze_project(self, content_data):
        # 取得データの正規化
        text = ""
        if isinstance(content_data, dict):
            text = content_data.get('text') or content_data.get('content') or ""
        elif isinstance(content_data, str):
            text = content_data

        if not text or len(text.strip()) < 10:
            logger.warning("AI解析スキップ: テキスト内容が不十分です。")
            return None

        system_prompt = """
あなたは自治体の調達情報を精査するリサーチアナリストです。
提示されたテキストから「映像制作・動画制作・配信・撮影」に関する募集中案件を特定し、
以下のJSON形式で回答してください。

【ラベリング基準】
A：確定（動画制作が必須。尺・本数・工程が明確）
B：候補（動画が含まれる可能性が高いが、必須と断定できない）
C：除外（募集終了、結果発表、物品購入、動画要件なし）

【出力形式】
JSON形式でのみ回答。
{
  "label": "A",
  "title": "件名",
  "prefecture": "都道府県/市区町村名",
  "method": "入札/プロポ等",
  "budget": "予定価格/上限",
  "period": "履行期間",
  "deadline_app": "参加申込締切(YYYY-MM-DD)",
  "deadline_ques": "質問締切(YYYY-MM-DD)",
  "deadline_prop": "提案書提出締切(YYYY-MM-DD)",
  "application_url": "申込先URL",
  "evidence": "映像要件の根拠(引用)",
  "tag": "ジャンル",
  "memo": "特記事項"
}
"""
        try:
            # AIへのリクエスト実行
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=system_prompt,
                messages=[{"role": "user", "content": f"解析対象:\n\n{text[:12000]}"}]
            )
            return json.loads(message.content[0].text)
        except Exception as e:
            logger.error(f"解析エラー詳細: {e}")
            # 連続エラーを避けるための短い待機
            time.sleep(2)
            return None
