import logging
import os
import json
import time
import re
from datetime import datetime, timezone, timedelta
from analyzer.ai_analyzer import AIAnalyzer
from database.sheets_manager import SheetsManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 60)
    logger.info("映像案件スクレイピング v1.18 [真・公募案件限定版]")
    logger.info("=" * 60)
    
    try:
        from scrapers.direct_scraper import search_all_prefectures_direct
        from scrapers.content_extractor import ContentExtractor
        
        analyzer = AIAnalyzer()
        sheets_manager = SheetsManager(os.environ["SPREADSHEET_ID"], json.loads(os.environ["GCP_SERVICE_ACCOUNT"]))
        extractor = ContentExtractor()
        jst = timezone(timedelta(hours=9))
        today = datetime.now(jst).date()

        logger.info("【ステップ1】全国自治体サイトから最新リンクを収集...")
        prefecture_results = search_all_prefectures_direct()
        all_tasks = [{"pref": p, **r} for p, rs in prefecture_results.items() for r in rs]
        
        final_projects = []
        seen_titles = set()
        
        logger.info("【ステップ2】案件の厳重選別（非案件・過去案件を徹底排除）...")
        for i, task in enumerate(all_tasks, 1):
            url = task['url']
            title_raw = task['title']

            # --- 🛡️ 門番1：URLドメインチェック ---
            if re.search(r"youtube\.com|youtu\.be|facebook\.com|instagram\.com|x\.com|twitter\.com", url):
                continue

            # --- 🛡️ 門番2：超・厳格タイトルチェック (公募案件であることの証明) ---
            # 「公募」「委託」「入札」「募集」「提案」「プロポーザル」が含まれないものは、単なる紹介ページとして捨てる
            if not re.search(r"公募|委託|入札|募集|提案|プロポーザル|コンペ|選定", title_raw):
                continue
            
            # 逆に、タイトルに以下の「非案件ワード」がある場合は即捨てる
            if re.search(r"質問回答|Q&A|結果|お仕事紹介|メッセージ|チャンネル|公開中|放映中|動画集|配信中|案内|ライブラリ|実績", title_raw):
                continue

            if i % 20 == 0: logger.info(f"進捗: {i}/{len(all_tasks)} 件チェック中")
            
            # 内容抽出
            content_data = extractor.extract(url)
            if not content_data: continue
            
            # AI解析
            analysis = analyzer.analyze_single(title_raw, content_data['content'], url)
            if not analysis: continue
            
            # --- 🛡️ 門番3：AI回答後の「年度と目的」最終検閲 ---
            if analysis.get('label') not in ["A", "B"]: continue
            title = analysis.get('title', '無題')
            if title in seen_titles: continue

            full_text = f"{title} {analysis.get('evidence','')} {analysis.get('memo','')}"

            # ① 否定語の検知 (AIが過去のものだと認めたら即アウト)
            if re.search(r"ではありません|過去の案件|終了しています|過去に実施|過去のもの", full_text):
                continue

            # ② 徹底的な年度チェック (令和8年/2026年が「主役」でないものはゴミ)
            # 本文に「令和8」か「2026」が1回も出てこないものは、AIが何と言おうと「過去案件」とみなす
            if "令和8" not in full_text and "2026" not in full_text:
                continue

            # ③ 期限切れチェック
            deadline_str = analysis.get('deadline_prop', '不明')
            if deadline_str == "不明": deadline_str = analysis.get('deadline_apply', '不明')
            if deadline_str != "不明":
                match = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', deadline_str)
                if match:
                    d_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3))).date()
                    if d_date < today: continue

            # --- ✨ 全関門突破！本物のビジネス案件のみ ---
            analysis.update({'prefecture': task['pref']})
            final_projects.append(analysis)
            seen_titles.add(title)
            logger.info(f"🎯 真の有効案件を捕捉: {title}")
            time.sleep(0.1)

        # 3. シート書き込み
        if final_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v16")
            sheets_manager.append_projects(sheets_manager.prepare_v12_sheet(sheet_name), final_projects)
            logger.info(f"✨ 完了！ 真の有効案件 {len(final_projects)}件のみを追加しました")
        else:
            logger.warning("⚠️ 現在募集中の本物の案件は見つかりませんでした")
            
    except Exception as e:
        logger.error(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
