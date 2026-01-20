import logging
from anthropic import Anthropic
import json

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        self.client = Anthropic()
        self.model = "claude-3-5-sonnet-20240620"

    def analyze_project(self, content_data):
        # content_dataが辞書形式（{'text': '...', 'url': '...'}）の場合、テキスト部分のみ抽出
        if isinstance(content_data, dict):
            text = content_data.get('text', '')
        else:
            text = str(content_data)

        if not text or len(text.strip()) < 10:
            return None

        system_prompt = """
あなたは「官公庁・自治体の調達情報を収集し、映像制作に関わる募集中案件を抽出・整理するリサーチアナリスト」です。
推測を排し、以下の【ラベリング基準】に従い、JSON形式でのみ回答してください。

【ラベリング基準】
A：確定（動画制作が必須。尺・本数・工程が明確）
B：候補（動画が含まれる可能性が高いが、必須と断定できない）
C：除外（募集終了、物品購入、広告枠買い、動画要件なし、結果発表）

【出力形式】
{
  "label": "A",
  "title": "件名",
  "prefecture": "都道府県/市区町村名",
  "method": "入札/プロポ/企画提案競技等",
  "budget": "予定価格/上限（不明なら不明）",
  "period": "履行期間（不明なら不明）",
  "deadline_app": "参加申込締切(YYYY-MM-DD)",
  "deadline_ques": "質問締切(YYYY-MM-DD)",
  "deadline_prop": "提案書提出締切(YYYY-MM-DD)",
  "application_url": "申込先URL",
  "evidence": "映像要件の根拠(短い引用)",
  "tag": "観光PR/採用/教育/防災等",
  "memo": "B判定理由や注意点"
}
"""
        try:
            # 安全にテキストを10000文字までに制限
            safe_text = text[:10000]
            
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=system_prompt,
                messages=[{"role": "user", "content": f"以下のテキストを解析してください:\n\n{safe_text}"}]
            )
            return json.loads(message.content[0].text)
        except Exception as e:
            logger.error(f"AI解析エラー詳細: {e}")
            return None
