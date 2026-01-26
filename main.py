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
    logger.info("映像案件スクレイピング v1.24 [クリエイティブ案件・完全特化版]")
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
        
        logger.info("【ステップ2】案件の極限選別（機材購入・過去案件を徹底排除）...")
        for i, task in enumerate(all_tasks, 1):
            url = task['url']
            title_raw = task['title']

            # --- 🛡️ 門番1：ドメイン遮断 ---
            if re.search(r"youtube\.com|youtu\.be|facebook\.com|instagram\.com|x\.com|twitter\.com", url):
                continue

            # --- 🛡️ 門番2：タイトルによる「絶対排除」 ---
            # ① すでに終わったもの・事後報告・制作完了報告
            if re.search(r"決定|公表|選定|落札|結果|審査|報告|実績|成功|達成|公開|完了|制作しました|放映中|配信中", title_raw):
                continue
            # ② 映像制作「業」ではないもの (機械・ハード・システムの購入)
            if re.search(r"装置|機器|購入|システムの導入|ハードウェア|備品|売却|賃貸", title_raw):
                continue
            # ③ 職員採用・資格試験
            if re.search(r"採用|職員|薬剤師|警察|教員|看護|医師|試験|相談|個人|講習", title_raw):
                continue
            # ④ 年度検閲：タイトルに令和7年(2025)以前があれば、AIに聞く前に即終了
            if re.search(r"令和[4-7]|R[4-7]|202[0-5]", title_raw):
                if "令和8" not in title_raw and "2026" not in title_raw:
                    continue

            # 門番3：タイトルに「クリエイティブ仕事」の気配があるか
            if not re.search(r"募集|委託|入札|プロポーザル|コンペ|公募|企画提案|制作|撮影", title_raw):
                continue

            if i % 20 == 0: logger.info(f"進捗: {i}/{len(all_tasks)} 件完了")
            
            content_data = extractor.extract(url)
            if not content_data: continue
            raw_text = content_data['content']

            # --- 🛡️ 門番4：本文の生データ直接検閲 ---
            # 本文に古い年号しかなく、2026/令和8の文字が1回も出ないなら偽物
            if re.search(r"令和[67]|R[67]|202[45]", raw_text) and not re.search(r"令和8|R8|2026", raw_text):
                continue

            analysis = analyzer.analyze_single(title_raw, raw_text, url)
            if not analysis: continue
            
            # --- 🛡️ 門番5：AI回答内容の「最終審判」 ---
            if analysis.get('label') not in ["A", "B"]: continue
            title = analysis.get('title', '無題')
            if title in seen_titles: continue

            evidence = analysis.get('evidence','')
            memo = analysis.get('memo','')
            full_ans = f"{title} {evidence} {memo}"

            # ① 否定語・ハードウェア購入の再チェック
            if re.search(r"ではありません|ではない|過去|終了|システムの購入|機器の購入", memo + evidence):
                continue

            # ② 令和8年度(2026)の「肯定文」がAI回答にあるか
            if not re.search(r"令和8年度?の案件|2026年度?の案件|令和8年度予算", full_ans):
                if "令和8" not in full_ans and "2026" not in full_ans: continue

            # ③ 期限切れチェック
            deadline_str = analysis.get('deadline_prop', '不明')
            if deadline_str == "不明": deadline_str = analysis.get('deadline_apply', '不明')
            if deadline_str != "不明":
                m = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', deadline_str)
                if m:
                    d_date = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3))).date()
                    if d_date < today: continue

            # --- ✨ 合格（真の映像制作・プロモーション公募案件） ---
            analysis.update({'prefecture': task['pref']})
            final_projects.append(analysis)
            seen_titles.add(title)
            logger.info(f"✨ 真の案件確定: {title}")
            time.sleep(0.1)

        if final_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v16")
            sheets_manager.append_projects(sheets_manager.prepare_v12_sheet(sheet_name), final_projects)
            logger.info(f"✨ 完了！ 厳選された {len(final_projects)}件のみを追加しました")
        else:
            logger.warning("⚠️ 現在募集中の有効案件は見つかりませんでした")
            
    except Exception as e:
        logger.error(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
