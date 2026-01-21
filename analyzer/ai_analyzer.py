import logging
import json
import os
from typing import Dict
from datetime import datetime, timezone, timedelta

logger = logging.getLogger(__name__)

class AIAnalyzer:
    def __init__(self):
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY が設定されていません")
        
        from anthropic import Anthropic
        self.client = Anthropic(api_key=api_key)
        self.model = os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
        logger.info(f"AI解析ユニット起動完了 (Model: {self.model})")
    
    def get_prompt(self, title: str, content: str) -> str:
        jst = timezone(timedelta(hours=9))
        today_str = datetime.now(jst).strftime('%Y-%m-%d')
        
        return f"""あなたは自治体の映像制作案件を判定する専門家です。

# 今日の日付
{today_str}

# 和暦→西暦変換ルール
- 令和6年 = 2024年
- 令和7年 = 2025年  
- 令和8年 = 2026年
- 令和9年 = 2027年

# 判定基準

## Label A（最優先案件）
以下の**両方**を満たす：
1. 映像・動画制作が**メインまたは重要な要素**である
2. 明らかに募集終了・締切超過ではない

**例:** プロモーション動画制作、観光PR映像、記録映像撮影、配信業務

## Label B（通常案件）
以下を満たす：
1. 映像・動画制作が**業務の一部**として含まれる
2. 明らかに募集終了・締切超過ではない

**例:** イベント企画に映像撮影が含まれる、ウェブサイト制作に動画も含む

## Label C（除外）
以下のいずれかを満たす：
1. 映像制作が**全く含まれない**
2. **明確に**「結果公表」「落札者決定」「募集終了」「受付終了」と記載
3. 締切が**明確に**{today_str}より過去（ただし締切不明の場合は除外しない）

# 重要な判断基準

**締切について:**
- 締切が**書かれていない**または**見つからない** → Label AまたはB（除外しない）
- 締切が**表形式で崩れている** → できる限り推測、不明ならLabel AまたはB
- 締切が**明確に過去** → Label C

**除外の判断:**
- 「除外」は慎重に判断してください
- 迷ったらLabel BまたはAにしてください
- 「審査結果」ページでも、新規募集情報があればそちらを優先

# 出力形式（JSON）

{{
  "label": "A" または "B" または "C",
  "title": "案件名（元のタイトルをそのまま）",
  "deadline_prop": "YYYY-MM-DD形式（不明な場合は'不明'）",
  "evidence": "判定の根拠となる文章を1文引用",
  "memo": "ステータス詳細（例：募集中、○月○日締切、結果公表済み など）"
}}

# 判定例

**例1: 映像制作がメイン、締切不明**
```
入力: 「広報動画制作業務の委託先を募集します。詳細は要綱を参照してください。」
出力:
{{
  "label": "A",
  "title": "広報動画制作業務",
  "deadline_prop": "不明",
  "evidence": "広報動画制作業務の委託先を募集します",
  "memo": "募集中、締切記載なし"
}}
```

**例2: 明確に締切が過去**
```
入力: 「プロモーション動画制作。締切：令和7年12月20日」
出力:
{{
  "label": "C",
  "title": "プロモーション動画制作",
  "deadline_prop": "2025-12-20",
  "evidence": "締切：令和7年12月20日",
  "memo": "締切超過（2025-12-20）"
}}
```

**例3: 募集終了**
```
入力: 「観光PR映像制作業務委託。【審査結果を公表しました】候補者：株式会社○○」
出力:
{{
  "label": "C",
  "title": "観光PR映像制作業務委託",
  "deadline_prop": "不明",
  "evidence": "審査結果を公表しました",
  "memo": "募集終了（結果公表済み）"
}}
```

**例4: 映像が含まれない**
```
入力: 「道路補修工事の入札について」
出力:
{{
  "label": "C",
  "title": "道路補修工事",
  "deadline_prop": "不明",
  "evidence": "道路補修工事",
  "memo": "映像制作要素なし"
}}
```

---

# 解析対象

タイトル: {title}

テキスト:
{content[:12000]}

---

上記のコンテンツを判定してJSON形式で出力してください。"""
    
    def make_batch_request(self, custom_id: str, title: str, content: str) -> Dict:
        """Batch APIリクエストを作成"""
        return {
            "custom_id": custom_id,
            "params": {
                "model": self.model,
                "max_tokens": 1500,
                "temperature": 0,
                "messages": [
                    {
                        "role": "user",
                        "content": self.get_prompt(title, content)
                    }
                ]
            }
        }
```

---
