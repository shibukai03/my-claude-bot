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
    logger.info("映像案件スクレイピング v1.17 [令和8年/2026年 徹底特化版]")
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
        
        logger.info("【ステップ2】案件の選別（不純物を徹底排除）...")
        for i, task in enumerate(all_tasks, 1):
            url = task['url']
            title_raw = task['title']

            # --- 🛡️ 門番1：タイトル段階での物理排除 (YouTube/過去年度/結果/回答) ---
            # ここに含まれるキーワードはAIに渡すまでもなく「ゴミ」として扱います
            if re.search(r"youtube\.com|youtu\.be|facebook\.com|instagram\.com|x\.com|twitter\.com", url):
                continue
            
            # 「令和7年」や「結果」などがタイトルにあるものは、案件ではないので破棄
            if re.search(r"令和[4-7]|R[4-7]|202[2-5]|質問回答|Q&A|選定結果|審査結果|候補者|決定|入札結果|落札|配信中|公開中|チャンネル|動画集|ご覧ください|視聴用", title_raw):
                continue

            if i % 20 == 0: logger.info(f"進捗: {i}/{len(all_tasks)} 件完了")
            
            # 内容抽出
            content_data = extractor.extract(url)
            if not content_data: continue
            
            # AI解析
            analysis = analyzer.analyze_single(title_raw, content_data['content'], url)
            if not analysis: continue
            
            # --- 🛡️ 門番2：AIの回答内容に対する「超・厳重検閲」 ---
            if analysis.get('label') not in ["A", "B"]: continue
            title = analysis.get('title', '無題')
            if title in seen_titles: continue

            # AIの回答（根拠・メモ）をすべて合体
            evidence = analysis.get('evidence','')
            memo = analysis.get('memo','')
            full_text = f"{title} {evidence} {memo}"

            # ① 否定語の検知 (AIが「〜ではない」「過去」と書いたら即落選)
            if re.search(r"ではありません|ではない|過去の案件|終了しています|募集は終了|過去に実施|過去のもの", memo + evidence):
                continue

            # ② 過去年度の残存チェック (令和8年/2026年の明記がないものは落とす)
            # 「令和8」も「2026」もどこにも書いていない、あるいは「令和7」が主役なら落とす
            has_future = re.search(r"令和8|2026|令和9|2027", full_text)
            has_past = re.search(r"令和[4-7]|R[4-7]|202[2-5]", full_text)
            
            if not has_future:
                # 未来の年号がないなら、安全のため落とす
                continue
            if has_past and not re.search(r"令和8年度?の案件|2026年度?の案件", full_text):
                # 過去年があり、かつ「令和8年の案件である」という断定がないなら落とす
                continue

            # ③ 期限切れチェック (今日以前の日付なら捨てる)
            deadline_str = analysis.get('deadline_prop', '不明')
            if deadline_str == "不明": deadline_str = analysis.get('deadline_apply', '不明')
            if deadline_str != "不明":
                match = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', deadline_str)
                if match:
                    d_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3))).date()
                    if d_date < today: continue

            # --- ✨ 全合格（2026年以降の本物の募集案件のみ） ---
            analysis.update({'prefecture': task['pref']})
            final_projects.append(analysis)
            seen_titles.add(title)
            logger.info(f"✨ 有効案件確定: {title}")
            time.sleep(0.1)

        # 3. 書き込み
        if final_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v16")
            sheets_manager.append_projects(sheets_manager.prepare_v12_sheet(sheet_name), final_projects)
            logger.info(f"✨ 完了！ 真の有効案件 {len(final_projects)}件を追加しました")
        else:
            logger.warning("⚠️ 現在募集中の有効な案件は見つかりませんでした")
            
    except Exception as e:
        logger.error(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
