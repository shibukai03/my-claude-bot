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
    logger.info("映像案件スクレイピング v1.16 [募集案件特化・不純物排除版]")
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
        
        logger.info("【ステップ2】案件の選別（不要な資料・YouTube・過去案件を排除）...")
        for i, task in enumerate(all_tasks, 1):
            url = task['url']
            title_raw = task['title']

            # --- 🛡️ 門番1：ドメイン遮断 (YouTube等) ---
            if re.search(r"youtube\.com|youtu\.be|facebook\.com|instagram\.com|x\.com|twitter\.com", url):
                continue

            # --- 🛡️ 門番2：タイトルキーワード遮断 (募集ではない資料を排除) ---
            # 「質問回答」「結果」「チャンネル」などをAIに渡す前に捨てる
            if re.search(r"質問回答|Q&A|選定結果|審査結果|落札|入札結果|候補者の決定|配信中|公開中|チャンネル|動画集|ご覧ください|視聴用", title_raw):
                continue

            if i % 20 == 0: logger.info(f"進捗: {i}/{len(all_tasks)} 件完了")
            
            content_data = extractor.extract(url)
            if not content_data: continue
            
            analysis = analyzer.analyze_single(title_raw, content_data['content'], url)
            if not analysis: continue
            
            # --- 🛡️ 門番3：AIの回答を「連座制」で厳重検閲 ---
            if analysis.get('label') not in ["A", "B"]: continue
            title = analysis.get('title', '無題')
            if title in seen_titles: continue

            # AIが書いた「証拠」と「メモ」を徹底スキャン
            evidence = analysis.get('evidence','')
            memo = analysis.get('memo','')
            full_text = f"{title} {evidence} {memo}"

            # ① 否定語チェック (AIが「〜ではありません」「過去」「終了」と書いたらアウト)
            if re.search(r"ではありません|過去の案件|終了しています|令和7年|2025年", memo + evidence):
                # ただし「令和8年ではありません」ではなく、単に古い年度の話をしていたら落とす
                if "令和8" not in memo and "2026" not in memo:
                    continue
                # AIが「令和8年ではありません」と明記している場合も落とす
                if re.search(r"令和8年度?の案件ではありません|2026年度?の案件ではありません", memo):
                    continue

            # ② 過去の成果物排除
            if re.search(r"制作しました|公開しています|放映中|更新しました", full_text):
                if not re.search(r"委託|募集|入札|プロポーザル|コンペ", full_text):
                    continue

            # ③ 未来年度チェック (令和8/2026年以降が優先)
            is_future = re.search(r"令和([8-9]|[1-9]\d)|202[6-9]|20[3-9]\d", full_text)
            is_past = re.search(r"令和[4-7]|R[4-7]|202[2-5]", full_text)
            if is_past and not is_future: continue

            # ④ 期限切れチェック
            deadline_str = analysis.get('deadline_prop', '不明')
            if deadline_str == "不明": deadline_str = analysis.get('deadline_apply', '不明')
            if deadline_str != "不明":
                match = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', deadline_str)
                if match:
                    d_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3))).date()
                    if d_date < today: continue

            # --- ✨ 合格 ---
            analysis.update({'prefecture': task['pref']})
            final_projects.append(analysis)
            seen_titles.add(title)
            logger.info(f"✨ 有効案件: {title}")
            time.sleep(0.1)

        # 3. 書き込み
        if final_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v16")
            sheets_manager.append_projects(sheets_manager.prepare_v12_sheet(sheet_name), final_projects)
            logger.info(f"✨ 完了！ {len(final_projects)}件をシートに追加しました")
        else:
            logger.warning("⚠️ 現在募集中の案件は見つかりませんでした")
            
    except Exception as e:
        logger.error(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
