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
    logger.info("映像案件スクレイピング v1.19 [プロ案件特化・不純物ゼロ目標]")
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
        
        logger.info("【ステップ2】案件の選別（公募・委託・2026年度予算に厳選）...")
        for i, task in enumerate(all_tasks, 1):
            url = task['url']
            title_raw = task['title']

            # --- 🛡️ 門番1：【物理排除】URLとドメイン ---
            if re.search(r"youtube\.com|youtu\.be|facebook\.com|instagram\.com|x\.com|twitter\.com", url):
                continue

            # --- 🛡️ 門番2：【タイトルによる絶対除外ルール】 ---
            # 1. 職員採用・資格試験（映像制作会社が受ける仕事ではないもの）
            if re.search(r"採用|職員募集|薬剤師|警察官|教員募集|ガイダンス|試験|相談会", title_raw):
                continue
            # 2. 事後報告・結果（すでに応募できないもの）
            if re.search(r"決定しました|選定結果|審査結果|入札結果|落札|事後報告|更新しました|配信中|公開中", title_raw):
                continue
            # 3. 年度フィルター (令和7年以前がメインのタイトルは無視)
            if re.search(r"令和[4-7]|R[4-7]|202[2-5]", title_raw) and "令和8" not in title_raw:
                continue

            # --- 🛡️ 門番3：【案件形式の必須キーワード】 ---
            # 「公募」「委託」「入札」「プロポーザル」のいずれかがないページは、単なるお知らせとして捨てる
            if not re.search(r"公募|委託|入札|募集|プロポーザル|コンペ|企画提案", title_raw):
                continue

            if i % 20 == 0: logger.info(f"進捗: {i}/{len(all_tasks)} 件完了")
            
            # 内容抽出
            content_data = extractor.extract(url)
            if not content_data: continue
            
            # AI解析
            analysis = analyzer.analyze_single(title_raw, content_data['content'], url)
            if not analysis: continue
            
            # --- 🛡️ 門番4：【AI解析後の内容検閲】 ---
            if analysis.get('label') not in ["A", "B"]: continue
            title = analysis.get('title', '無題')
            if title in seen_titles: continue

            evidence = analysis.get('evidence','')
            memo = analysis.get('memo','')
            full_text = f"{title} {evidence} {memo}"

            # ① 否定語・事後報告の再検閲
            if re.search(r"ではありません|ではない|過去の案件|終了しています|決定しました|候補者を選定", full_text):
                continue

            # ② 「令和8年/2026年」の「新規案件」であることの証明
            # 本文に令和8年(2026年)が「これから始まる」文脈でないものは除外
            if "令和8" not in full_text and "2026" not in full_text:
                continue
            
            # 過去の年度(令和7)が強調されている場合は、未来案件でも除外（混同を避ける）
            if re.search(r"令和7年度の案件|令和7年度予算", full_text) and "令和8" not in full_text:
                continue

            # ③ 期限切れチェック
            deadline_str = analysis.get('deadline_prop', '不明')
            if deadline_str == "不明": deadline_str = analysis.get('deadline_apply', '不明')
            if deadline_str != "不明":
                match = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', deadline_str)
                if match:
                    d_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3))).date()
                    if d_date < today: continue

            # --- ✨ 合格（映像制作業として成立する公募案件） ---
            analysis.update({'prefecture': task['pref']})
            final_projects.append(analysis)
            seen_titles.add(title)
            logger.info(f"🎯 真の案件を捕捉: {title}")
            time.sleep(0.1)

        # 3. 書き込み
        if final_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v16")
            sheets_manager.append_projects(sheets_manager.prepare_v12_sheet(sheet_name), final_projects)
            logger.info(f"✨ 完了！ 厳選された {len(final_projects)}件を追加しました")
        else:
            logger.warning("⚠️ 現在募集中の有効な案件は見送られました")
            
    except Exception as e:
        logger.error(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
