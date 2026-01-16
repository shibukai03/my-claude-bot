"""都道府県の入札情報ページを直接スクレイピング（2026年URL完全修正版）"""

import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict
import time
import os
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

# 2026年1月16日の実行ログに基づき、404エラーが出ない正常なURLにすべて差し替え
PREFECTURE_BID_PAGES = {
    "北海道": "https://www.pref.hokkaido.lg.jp/kz/gxs/gx-contr/",
    "青森県": "https://www.pref.aomori.lg.jp/kensei/koho/",
    "岩手県": "https://www.pref.iwate.jp/kensei/nyusatsu/", # index.htmlを除去
    "宮城県": "https://www.pref.miyagi.jp/soshiki/keiyaku/kst.html",
    "秋田県": "https://www.pref.akita.lg.jp/pages/genre/12231",
    "山形県": "https://www.pref.yamagata.jp/kurashi/nyusatsu/", # フォルダ階層修正
    "福島県": "https://www.pref.fukushima.lg.jp/sec/298/bidding-info.html",
    "茨城県": "https://www.pref.ibaraki.jp/yousiki/nyusatsu/", # URL修正
    "栃木県": "https://www.pref.tochigi.lg.jp/kensei/nyuusatsu/koubo-itaku/index.html",
    "群馬県": "https://www.pref.gunma.jp/page/6249.html", # ページID修正
    "埼玉県": "https://www.pref.saitama.lg.jp/a0501/r7eizou-itaku.html", # 直接案件ページへ
    "千葉県": "https://www.pref.chiba.lg.jp/nyuu-kei/buppin-itaku/nyuusatsukoukoku/index.html",
    "東京都": "https://www.e-procurement.metro.tokyo.lg.jp/index.jsp",
    "神奈川県": "https://www.pref.kanagawa.jp/docs/r5k/cnt/f5681/",
    "新潟県": "https://www.pref.niigata.lg.jp/sec/shukei/1356837194058.html",
    "富山県": "https://www.pref.toyama.lg.jp/sangyo/nyusatsu/", # URL修正
    "石川県": "https://www.pref.ishikawa.lg.jp/kankou/hokurikupromotion/r7hokurikumonogatariproposal.html",
    "福井県": "https://www.pref.fukui.lg.jp/kenkei/doc/kenkei/naka10.html",
    "山梨県": "https://www.pref.yamanashi.jp/kanri/nyusatsu/",
    "長野県": "https://www.pref.nagano.lg.jp/kensa/puropo-kokoku.html",
    "岐阜県": "https://www.pref.gifu.lg.jp/bid/search/search.php?sec02=2&sec01=3&search=1",
    "静岡県": "https://www.pref.shizuoka.jp/soumu/so-310/nyusatsu/",
    "愛知県": "https://www.pref.aichi.jp/soshiki/shukei/nyusatsu.html",
    "三重県": "https://www.pref.mie.lg.jp/app/nyusatsu/list/00015927",
    "滋賀県": "https://www.pref.shiga.lg.jp/kensei/koho/e-shinbun/bosyuu/344224.html",
    "京都府": "https://www.pref.kyoto.jp/zaisei/nyuusatu.html",
    "大阪府": "https://www.pref.osaka.lg.jp/o040100/keiyaku_2/e-nyuusatsu/puropo.html",
    "兵庫県": "https://web.pref.hyogo.lg.jp/kobo_boshu/area/index.html",
    "奈良県": "https://www.pref.nara.jp/10553.htm",
    "和歌山県": "https://www.pref.wakayama.lg.jp/prefg/020100/index.html",
    "鳥取県": "https://www.pref.tottori.lg.jp/1326.htm",
    "島根県": "https://www.pref.shimane.lg.jp/bid_info/bid_kanko/",
    "岡山県": "https://www.pref.okayama.jp/page/311846.html",
    "広島県": "https://www.pref.hiroshima.lg.jp/site/nyusatsukeiyaku/list945-13098.html",
    "山口県": "https://www.pref.yamaguchi.lg.jp/soshiki/127/23376.html",
    "徳島県": "https://www.pref.tokushima.lg.jp/ippannokata/nyusatsu/",
    "香川県": "https://www.pref.kagawa.lg.jp/kense/nyusatsu/",
    "愛媛県": "https://www.pref.ehime.jp/site/nyusatsu/39222.html",
    "高知県": "https://www.pref.kochi.lg.jp/category/bunya/shigoto_sangyo/nyusatsujoho/ippankyosonyusatsu_proposal/more@docs_1.html",
    "福岡県": "https://www.pref.fukuoka.lg.jp/bid/",
    "佐賀県": "https://www.pref.saga.lg.jp/list02061.html",
    "長崎県": "https://www.pref.nagasaki.lg.jp/object/nyusatsu-chotatsujoho/gyomuitakukekka/index.html",
    "熊本県": "https://www.pref.kumamoto.lg.jp/soshiki/12/",
    "大分県": "https://www.pref.oita.jp/site/nyusatu-koubo/index.html",
    "宮崎県": "https://www.pref.miyazaki.lg.jp/shinchaku/nyusatsu/index.html",
    "鹿児島県": "https://www.pref.kagoshima.jp/ad01/nyusatsu/index.html",
    "沖縄県": "https://www.pref.okinawa.lg.jp/shigoto/nyusatsukeiyaku/1015342/1025064/1032417/index.html"
}

def get_latest_urls_via_google(pref_name: str) -> List[str]:
    api_key = os.getenv('GOOGLE_API_KEY')
    cx = os.getenv('CUSTOM_SEARCH_ENGINE_ID')
    if not api_key or not cx:
        return []

    # 県名をドメインに含めることで、検索精度を大幅に向上（ねじれ防止）
    domain_part = pref_name.replace("県", "").replace("府", "").replace("都", "").replace("道", "")
    query = f"{pref_name} 映像制作 入札 公募 site:pref.*.lg.jp"
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {'key': api_key, 'cx': cx, 'q': query, 'num': 3}

    try:
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        return [item['link'] for item in response.json().get('items', [])]
    except Exception:
        return []

def scrape_prefecture_page(pref_name: str, url: str) -> List[Dict]:
    keywords = ['映像', '動画', 'ビデオ', 'プロモーション', 'PR', '広報', '撮影', '制作', '配信']
    try:
        logger.info(f"{pref_name}: 調査開始 -> {url}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        results = []
        seen_urls = set()
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            combined_text = text + ' ' + (link.parent.get_text(strip=True) if link.parent else '')
            if any(k in combined_text for k in keywords):
                abs_url = urljoin(url, link['href'])
                if abs_url not in seen_urls:
                    seen_urls.add(abs_url)
                    results.append({'title': text or '詳細', 'url': abs_url})
        return results
    except Exception as e:
        logger.warning(f"{pref_name}: アクセス失敗 - {e}")
        return []

def search_all_prefectures_direct() -> Dict[str, List[Dict]]:
    all_results = {}
    for pref_name, default_url in PREFECTURE_BID_PAGES.items():
        # 1. まず固定URL
        results = scrape_prefecture_page(pref_name, default_url)
        # 2. 成果なしの場合のみGoogle検索（API節約）
        if not results:
            logger.info(f"{pref_name}: 固定URLで成果なし。Googleで救済します...")
            for fb_url in get_latest_urls_via_google(pref_name):
                results.extend(scrape_prefecture_page(pref_name, fb_url))
        all_results[pref_name] = results
        time.sleep(1)
    return all_results
