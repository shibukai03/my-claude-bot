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
    logger.info("映像案件スクレイピング v1.23 [真の案件のみ・不純物100%排除版]")
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
        
        logger.info("【ステップ2】案件の最終検閲（100%令和8年度・募集中のみ）...")
        for i, task in enumerate(all_tasks, 1):
            url = task['url']
            title_raw = task['title']

            # --- 🛡️ 門番1：ドメイン遮断 ---
            if re.search(r"youtube\.com|youtu\.be|facebook\.com|instagram\.com|x\.com|twitter\.com", url):
                continue

            # --- 🛡️ 門番2：タイトルの「冷徹な排除」ルール ---
            # 1. すでに終わったもの・事後報告・成功ニュースを排除
            if re.search(r"決定|公表|選定|落札|結果|審査|報告|実績|成功|達成|公開|完了", title_raw): continue
            # 2. 職員採用・資格試験・人物の募集を排除
            if re.search(r"採用|職員|薬剤師|警察|教員|看護|医師|試験|相談|個人", title_raw): continue
            # 3. 令和7年以前をタイトル段階で排除（令和8との併記がない限り）
            if re.search(r"令和[4-7]|R[4-7]|202[2-5]", title_raw) and "令和8" not in title_raw:
                continue

            # 門番3：タイトルに「ビジネスの注文」ワードがあるか
            if not re.search(r"募集|委託|入札|プロポーザル|コンペ|公募|企画提案|制作|撮影|業務", title_raw):
                continue

            if i % 20 == 0: logger.info(f"進捗: {i}/{len(all_tasks)} 件完了")
            
            content_data = extractor.extract(url)
            if not content_data: continue
            raw_text = content_data['content']

            # --- 🛡️ 門番4：本文の「和暦」直接検閲 ---
            # AIがハルシネーション（嘘）をつく前に、本文に古い年号しかない場合は捨てる
            if re.search(r"令和[67]|R[67]|202[45]", raw_text) and not re.search(r"令和8|R8|2026", raw_text):
                continue

            analysis = analyzer.analyze_single(title_raw, raw_text, url)
            if not analysis: continue
            
            # --- 🛡️ 門番5：AI回答の「否定語」検閲 ---
            if analysis.get('label') not in ["A", "B"]: continue
            title = analysis.get('title', '無題')
            if title in seen_titles: continue

            evidence = analysis.get('evidence','')
            memo = analysis.get('memo','')
            full_ans = f"{title} {evidence} {memo}"

            # ① AIの回答に「〜ではない」「過去」「終了」が含まれていたら即破棄
            if re.search(r"ではありません|ではない|過去|終了|終了済", memo + evidence):
                continue

            # ② 令和8年度(2026)の「実在」を確認
            # 回答内に「令和8年度の案件」あるいは「2026年度の案件」と肯定されている必要がある
            if not re.search(r"令和8年度?の案件|2026年度?の案件|令和8年度予算", full_ans):
                # 未来の年号単体でもOKだが、過去の年号が混じっている場合は上記の肯定文を必須とする
                if re.search(r"令和[67]|202[45]", full_ans) and not re.search(r"令和8|2026", full_ans):
                    continue

            # ③ 期限切れチェック
            deadline_str = analysis.get('deadline_prop', '不明')
            if deadline_str == "不明": deadline_str = analysis.get('deadline_apply', '不明')
            if deadline_str != "不明":
                m = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', deadline_str)
                if m:
                    d_date = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
                    if d_date < today: continue

            # --- ✨ 最終合格：あなたが今すぐ応募すべき2026年の本物の案件 ---
            analysis.update({'prefecture': task['pref']})
            final_projects.append(analysis)
            seen_titles.add(title)
            logger.info(f"✨ 真の2026年案件を捕捉: {title}")
            time.sleep(0.1)

        if final_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v16")
            sheets_manager.append_projects(sheets_manager.prepare_v12_sheet(sheet_name), final_projects)
            logger.info(f"✨ 完了！ 100%本物の案件のみ {len(final_projects)}件を追加しました")
        else:
            logger.warning("⚠️ 条件に合う有効な新規案件は見つかりませんでした")
            
    except Exception as e:
        logger.error(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
