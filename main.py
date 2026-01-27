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
    logger.info("映像案件スクレイピング v1.25 [Claude 4.5 × 最終調整版]")
    logger.info("=" * 60)
    
    try:
        from scrapers.direct_scraper import search_all_prefectures_direct
        from scrapers.content_extractor import ContentExtractor
        
        analyzer = AIAnalyzer()
        sheets_manager = SheetsManager(os.environ["SPREADSHEET_ID"], json.loads(os.environ["GCP_SERVICE_ACCOUNT"]))
        extractor = ContentExtractor()
        jst = timezone(timedelta(hours=9))
        today = datetime.now(jst).date()

        logger.info("【ステップ1】全国リンク収集開始...")
        prefecture_results = search_all_prefectures_direct()
        all_tasks = [{"pref": p, **r} for p, rs in prefecture_results.items() for r in rs]
        
        final_projects = []
        seen_titles = set()
        
        logger.info("【ステップ2】案件選別（不純物を排除しつつ本物を救済）...")
        for i, task in enumerate(all_tasks, 1):
            url = task['url']
            title_raw = task['title']

            # --- 🛡️ 門番1：ドメイン遮断 ---
            if re.search(r"youtube\.com|youtu\.be|facebook\.com|instagram\.com|x\.com|twitter\.com", url):
                continue

            # --- 🛡️ 門番2：タイトルの「絶対排除」 (v1.24を継承) ---
            if re.search(r"決定|公表|選定|落札|結果|審査|報告|実績|成功|達成|公開|完了|制作しました|放映中|配信中", title_raw):
                continue
            if re.search(r"採用|職員|薬剤師|警察|教員|看護|医師|試験|相談|個人|講習", title_raw):
                continue

            # --- 🛡️ 門番3：【救済】タイトルキーワードの拡充 ---
            # 「作成」「動画」「PR」「プロモーション」を追加して奈良や宮崎の案件を拾います
            if not re.search(r"募集|委託|入札|プロポーザル|コンペ|公募|企画提案|制作|作成|撮影|業務|動画|PR|プロモーション", title_raw):
                continue

            if i % 20 == 0: logger.info(f"進捗: {i}/{len(all_tasks)} 件完了")
            
            content_data = extractor.extract(url)
            if not content_data: continue
            raw_text = content_data['content']

            # --- 🛡️ 門番4：本文の年度検閲 (少し柔軟に) ---
            # 令和8年(2026)の文字があるか、あるいはAIに判断を委ねる（4.5なら嘘を見破れるため）
            # ただし、令和6年などの明らかに古い数字「だけ」しかないものはここで落とす
            if re.search(r"令和[56]|R[56]|202[34]", raw_text) and not re.search(r"令和[789]|R[789]|202[567]", raw_text):
                continue

            # AI解析 (Claude 4.5 Haiku)
            analysis = analyzer.analyze_single(title_raw, raw_text, url)
            if not analysis: continue
            
            # --- 🛡️ 門番5：AI内容の最終審判 ---
            if analysis.get('label') not in ["A", "B"]: continue
            title = analysis.get('title', '無題')
            if title in seen_titles: continue

            full_ans = f"{title} {analysis.get('evidence','')} {analysis.get('memo','')}"

            # 否定語チェック
            if re.search(r"ではありません|ではない|終了済", analysis.get('memo','')):
                continue

            # 2026/令和8年度案件であることの再確認
            if not re.search(r"令和8|2026|令和7年度から令和8|令和7年度補正", full_ans):
                continue

            # 期限切れチェック
            deadline_str = analysis.get('deadline_prop', '不明')
            if deadline_str == "不明": deadline_str = analysis.get('deadline_apply', '不明')
            if deadline_str != "不明":
                m = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', deadline_str)
                if m:
                    d_date = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
                    if d_date < today: continue

            # --- ✨ 合格 ---
            analysis.update({'prefecture': task['pref']})
            final_projects.append(analysis)
            seen_titles.add(title)
            logger.info(f"🎯 有効案件を捕捉: {title}")
            time.sleep(0.1)

        if final_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v16")
            sheets_manager.append_projects(sheets_manager.prepare_v12_sheet(sheet_name), final_projects)
            logger.info(f"✨ 完了！ 真の有効案件 {len(final_projects)}件を追加しました")
        else:
            logger.warning("⚠️ 募集中の有効案件は見つかりませんでした")
            
    except Exception as e:
        logger.error(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
