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
    logger.info("映像案件スクレイピング v1.15 [YouTube除外・案件特化版]")
    logger.info("=" * 60)
    
    try:
        from scrapers.direct_scraper import search_all_prefectures_direct
        from scrapers.content_extractor import ContentExtractor
        
        analyzer = AIAnalyzer()
        sheets_manager = SheetsManager(os.environ["SPREADSHEET_ID"], json.loads(os.environ["GCP_SERVICE_ACCOUNT"]))
        extractor = ContentExtractor()
        jst = timezone(timedelta(hours=9))
        today = datetime.now(jst).date()

        logger.info("【ステップ1】全国自治体サイトから最新リンクを収集開始...")
        prefecture_results = search_all_prefectures_direct()
        all_tasks = [{"pref": p, **r} for p, rs in prefecture_results.items() for r in rs]
        
        final_projects = []
        seen_titles = set()
        
        logger.info("【ステップ2】案件の選別（YouTube/SNS/公開済動画を排除）...")
        for i, task in enumerate(all_tasks, 1):
            url = task['url']
            title_raw = task['title']

            # --- 🛡️ フィルター1：URLドメインチェック ---
            # YouTubeやSNSのリンクそのものは「案件」ではないため即除外
            if re.search(r"youtube\.com|youtu\.be|facebook\.com|instagram\.com|x\.com|twitter\.com", url):
                continue

            # --- 🛡️ フィルター2：タイトルキーワードチェック ---
            # 「配信中」「公開中」「チャンネル」「動画を見る」などは案件ではないため除外
            if re.search(r"配信中|公開中|チャンネル|視聴用|動画ライブラリ|動画集|ご覧ください", title_raw):
                continue

            if i % 10 == 0: logger.info(f"進捗: {i}/{len(all_tasks)} 件チェック中")
            
            # 内容抽出
            content_data = extractor.extract(url)
            if not content_data: continue
            
            # AI解析
            analysis = analyzer.analyze_single(title_raw, content_data['content'], url)
            if not analysis: continue
            
            # --- 🛡️ フィルター3：AI回答ベースの厳重検閲 ---
            label = analysis.get('label', 'C')
            if label not in ["A", "B"]: continue
            
            title = analysis.get('title', '無題')
            if title in seen_titles: continue

            evidence = analysis.get('evidence', '')
            memo = analysis.get('memo', '')
            full_check_text = f"{title} {evidence} {memo}"

            # すでに完成した動画の紹介ページ（過去の成果物）を排除
            if re.search(r"制作しました|公開しています|放映中|更新しました|ライブラリ", full_check_text):
                if not re.search(r"委託|募集|入札|プロポーザル|コンペ", full_check_text):
                    continue

            # 年度チェック (2026年/令和8年以降を優先)
            is_future = re.search(r"令和([8-9]|[1-9]\d)|202[6-9]|20[3-9]\d", full_check_text)
            is_past = re.search(r"令和[4-7]|R[4-7]|202[2-5]", full_check_text)
            if is_past and not is_future: continue

            # 期限切れ排除
            deadline_str = analysis.get('deadline_prop', '不明')
            if deadline_str == "不明": deadline_str = analysis.get('deadline_apply', '不明')
            if deadline_str != "不明":
                match = re.search(r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})', deadline_str)
                if match:
                    deadline_date = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3))).date()
                    if deadline_date < today: continue

            # --- ✨ 合格（本物の案件） ---
            analysis.update({'prefecture': task['pref']})
            final_projects.append(analysis)
            seen_titles.add(title)
            logger.info(f"✨ 案件確定: {title}")
            time.sleep(0.1)

        # 3. 書き込み
        if final_projects:
            sheet_name = datetime.now(jst).strftime("映像案件_%Y年%m月_v16")
            sheets_manager.append_projects(sheets_manager.prepare_v12_sheet(sheet_name), final_projects)
            logger.info(f"✨ 完了！ {len(final_projects)}件をシートに追加しました")
        else:
            logger.warning("⚠️ 募集中の新規案件は見つかりませんでした")
            
    except Exception as e:
        logger.error(f"❌ エラー: {e}")

if __name__ == "__main__":
    main()
