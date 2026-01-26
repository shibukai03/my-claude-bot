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
    logger.info("映像案件スクレイピング v1.22 [西暦・和暦 厳格補正版]")
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
        
        logger.info("【ステップ2】極限選別（偽の2026年案件を徹底排除）...")
        for i, task in enumerate(all_tasks, 1):
            url = task['url']
            title_raw = task['title']

            # --- 🛡️ 門番1：タイトルの物理排除 (事後報告・採用・過去年度) ---
            if re.search(r"決定|公表|選定|落札|結果|審査|報告|実績", title_raw): continue # 終わったものは見ない
            if re.search(r"採用|職員|薬剤師|警察|教員|看護|試験|相談", title_raw): continue # 人の募集は見ない
            if re.search(r"令和[4-7]|R[4-7]|202[2-5]", title_raw) and "令和8" not in title_raw: continue

            # 最低限必要な「仕事」のキーワード
            if not re.search(r"公募|委託|入札|募集|提案|プロポーザル|コンペ|制作|撮影|業務", title_raw): continue

            if i % 20 == 0: logger.info(f"進捗: {i}/{len(all_tasks)} 件完了")
            
            # 内容抽出
            content_data = extractor.extract(url)
            if not content_data: continue
            raw_text = content_data['content']

            # --- 🛡️ 門番2：本文の生データ検閲 (AIが嘘をつく前にチェック) ---
            # 本文に令和6年(2024)や令和7年(2025)が書いてあり、令和8年(2026)がない場合は即除外
            if re.search(r"令和[67]|R[67]|202[45]", raw_text) and not re.search(r"令和8|R8|2026", raw_text):
                continue

            # AI解析
            analysis = analyzer.analyze_single(title_raw, raw_text, url)
            if not analysis: continue
            
            # --- 🛡️ 門番3：AI回答の矛盾チェック ---
            if analysis.get('label') not in ["A", "B"]: continue
            title = analysis.get('title', '無題')
            if title in seen_titles: continue

            evidence = analysis.get('evidence','')
            memo = analysis.get('memo','')
            full_ans = f"{title} {evidence} {memo}"

            # AIが「令和8年度ではない」と書いている、または過去だと認めている場合
            if re.search(r"ではありません|ではない|過去|終了|令和[67]|202[45]", memo + evidence):
                if "令和8" not in memo and "2026" not in memo: continue
                if re.search(r"令和8年度?の案件ではありません", memo): continue

            # 本文と回答を合わせて「2026/令和8」の文字が1回も出ないなら除外
            if "令和8" not in full_ans and "2026" not in full_ans: continue

            # 期限切れチェック (変換ミス対策：AIが2026年と答えても、元が令和6年ならここで落ちる)
            deadline_str = analysis.get('deadline_prop', '不明')
            if deadline_str == "不明": deadline_str = analysis.get('deadline_apply', '不明')
            if deadline_str != "不明":
                m = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', deadline_str)
                if m:
                    # AIの計算ミスを補正：もし西暦が2026なのに元がR6なら修正される
                    d_date = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
                    if d_date < today: continue

            # --- ✨ 最終合格：本物の令和8年度（2026年度）案件 ---
            analysis.update({'prefecture': task['pref']})
            final_projects.append(analysis)
            seen_titles.add(title)
            logger.info(f"🎯 真の2026年案件を捕捉: {title}")
            time.sleep(0.1)

        if final_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v16")
            sheets_manager.append_projects(sheets_manager.prepare_v12_sheet(sheet_name), final_projects)
            logger.info(f"✨ 完了！ 厳選案件 {len(final_projects)}件を追加しました")
        else:
            logger.warning("⚠️ 2026年度の新規案件は見つかりませんでした")
            
    except Exception as e:
        logger.error(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
