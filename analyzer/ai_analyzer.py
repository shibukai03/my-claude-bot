import logging
from anthropic import Anthropic
import json

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        # APIキーは環境変数から自動読み込み
        self.client = Anthropic()
        # モデルはSonnetを指定
        self.model = "claude-3-5-sonnet-20240620"

    def analyze_project(self, text):
        system_prompt = """
あなたは「官公庁・自治体の調達情報を収集し、映像制作に関わる募集中案件を抽出・整理するリサーチアナリスト」です。
推測・憶測を排し、公告本文や仕様書に基づき、以下の基準で判定してください。

【ラベリング基準】
A：確定（動画制作が必須。尺・本数・工程が明確）
B：候補（動画が含まれる可能性が高いが、必須と断定できない/評価項目で示唆）
C：除外（除外条件に該当、または動画要件が確認できない/募集終了）

【除外条件】
物品調達、広告枠買い、Webサイト制作のみ、イベント運営のみ、写真のみ。

【出力形式】
必ず以下のJSON形式でのみ回答してください。
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
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                system=system_prompt,
                messages=[{"role": "user", "content": f"以下のテキストを解析してください:\n\n{text[:10000]}"}]
            )
            # JSON部分のみ抽出してパース
            return json.loads(message.content[0].text)
        except Exception as e:
            logger.error(f"AI解析エラー: {e}")
            return None
