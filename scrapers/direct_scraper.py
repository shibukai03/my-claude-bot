"""47都道府県 入札・公募ページ全ページ巡回エンジン（v1.3 ページネーション対応）"""

import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Set
import time
import os
import re
from urllib.parse import urljoin
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)

# URLリスト（ユーザー様ご提供のリストを維持）
PREFECTURE_BID_PAGES = {
    "北海道": ["https://www.pref.hokkaido.lg.jp/news/nyusatsu/", "https://www.pref.hokkaido.lg.jp/category/d001/c001/s002/"],
    "青森県": ["https://www.pref.aomori.lg.jp/soshiki/suito/keiri/buppin-top.html", "https://www.pref.aomori.lg.jp/boshu/"],
    "岩手県": ["https://www.pref.iwate.jp/kensei/nyuusatsu/it/1024231/index.html", "https://www.pref.iwate.jp/news/1016275.html"],
    "宮城県": ["https://www.pref.miyagi.jp/life/8/40/105/index.html", "https://www.pref.miyagi.jp/life/proposal/index.html"],
    "秋田県": ["https://www.pref.akita.lg.jp/pages/genre/12121", "https://www.pref.akita.lg.jp/pages/genre/12231"],
    "山形県": ["https://www.pref.yamagata.jp/kensei/nyuusatsujouhou/nyuusatsujouhou/jyokyo/index.html", "https://www.pref.yamagata.jp/kensei/nyuusatsujouhou/nyuusatsujouhou/proposal/index.html"],
    "福島県": ["https://www.pref.fukushima.lg.jp/sec/01115c/nyusatsujoho.html", "https://www.pref.fukushima.lg.jp/sec/55015a/suitou-proposal.html"],
    "茨城県": ["https://www.pref.ibaraki.jp/shiru/nyusatsu-chotatsu/index.html", "https://www.pref.ibaraki.jp/bosyu.html"],
    "栃木県": ["https://www.pref.tochigi.lg.jp/kensei/nyuusatsu/koubo-itaku/index.html", "https://www.pref.tochigi.lg.jp/kensei/nyuusatsu/koubo-koukyou/index.html"],
    "群馬県": ["https://www.pref.gunma.jp/site/nyuusatsu/index-2.html", "https://www.pref.gunma.jp/site/nyuusatsu/list135-773.html"],
    "埼玉県": ["https://www.pref.saitama.lg.jp/a0212/kense/tetsuzuki/nyusatsu/buppin/index.html", "https://www.pref.saitama.lg.jp/search/result.html?q=%E5%85%AC%E5%8B%9F&sa=%E6%A4%9C%E7%B4%A2&cx=0898cdc8c417302e4&ie=UTF-8&cof=FORID%3A9"],
    "千葉県": ["https://www.pref.chiba.lg.jp/nyuu-kei/buppin-itaku/index.html", "https://www.pref.chiba.lg.jp/nyuu-kei/buppin-itaku/nyuusatsukoukoku/koukoku/index.html"],
    "東京都": ["https://www.e-procurement.metro.tokyo.lg.jp/SrvPublish", "https://www.metro.tokyo.lg.jp/search?keyword=&purpose=163047"],
    "神奈川県": ["https://www.pref.kanagawa.jp/search.html?q=%E5%85%AC%E5%8B%9F&sa=%E6%A4%9C%E7%B4%A2&cx=007296304677419487325%3Afufp31hx7qk&ie=UTF-8&cof=FORID%3A9#gsc.tab=0&gsc.q=%E5%85%A5%E6%9C%AD&gsc.sort=date", "https://www.pref.kanagawa.jp/search.htmlq=%E5%85%AC%E5%8B%9F&sa=%E6%A4%9C%E7%B4%A2&cx=007296304677419487325%3Afufp31hx7qk&ie=UTF-8&cof=FORID%3A9#gsc.tab=0&gsc.q=%E5%85%AC%E5%8B%9F&gsc.sort=date"],
    "新潟県": ["https://www.pref.niigata.lg.jp/life/sub/8/index-2.html", "https://www.pref.niigata.lg.jp/sec/list1-1.html"],
    "富山県": ["https://www.pref.toyama.jp/sangyou/nyuusatsu/jouhou/ekimu/koukokukekka/koukoku.html", "https://www.pref.toyama.jp/sangyou/nyuusatsu/koubo/bosyuu.html"],
    "石川県": ["https://www.pref.ishikawa.lg.jp/search/result.html?q=%E3%83%97%E3%83%AD%E3%83%9D%E3%83%BC%E3%82%B6%E3%83%AB&sa=%E6%A4%9C%E7%B4%A2&cx=013090918390897489992%3Axcsb1hsaoy4&ie=UTF-8&cof=FORID%3A9#gsc.tab=0&gsc.q=%E3%83%97%E3%83%AD%E3%83%9D%E3%83%BC%E3%82%B6%E3%83%AB&gsc.sort=date", "https://www.pref.ishikawa.lg.jp/search/result.html?q=%E3%83%97%E3%83%AD%E3%83%9D%E3%83%BC%E3%82%B6%E3%83%AB&sa=%E6%A4%9C%E7%B4%A2&cx=013090918390897489992%3Axcsb1hsaoy4&ie=UTF-8&cof=FORID%3A9#gsc.tab=0&gsc.q=%E3%83%97%E3%83%AD%E3%83%9D%E3%83%BC%E3%82%B6%E3%83%AB%E3%80%80%E5%8B%95%E7%94%BB&gsc.sort=date"],
    "福井県": ["https://www.pref.fukui.lg.jp/search.html?q=%E3%83%97%E3%83%AD%E3%83%9D%E3%83%BC%E3%82%B6%E3%83%AB", "https://www.pref.fukui.lg.jp/doc/dx-suishin/sonotanyusatu.html"],
    "山梨県": ["https://www.pref.yamanashi.jp/kensei/nyusatsu/keiyaku/johokokai.html", "https://www.pref.yamanashi.jp/shinchaku/index.html"],
    "長野県": ["https://www.pref.nagano.lg.jp/kensa/kensei/nyusatsu/buppin/index.html", "https://www.pref.nagano.lg.jp/kensa/puropo-kokoku.html"],
    "岐阜県": ["https://www.pref.gifu.lg.jp/site/bid/", "https://www.pref.gifu.lg.jp/bid/search/search.php?search_bid_kwd=&ctg%5B%5D=5&sec02=0&sec01=0&date1=&date2=&search=1"],
    "静岡県": ["https://www.pref.shizuoka.jp/kensei/nyusatsukobai/nyusatsuchiji/index.html", "https://www.pref.shizuoka.jp/kensei/nyusatsukobai/1072932/index.html", "https://www.pref.shizuoka.jp/kensei/nyusatsukobai/nyusatsukurashi/index.html", "https://www.pref.shizuoka.jp/kensei/nyusatsukobai/1047032/index.html", "https://www.pref.shizuoka.jp/kensei/nyusatsukobai/1077988/index.html", "https://www.pref.shizuoka.jp/kensei/nyusatsukobai/nyusatsukikikanri/index.html", "https://www.pref.shizuoka.jp/kensei/nyusatsukobai/nyusatsukeieikanri/index.html", "https://www.pref.shizuoka.jp/kensei/nyusatsukobai/nyusatsukeizaisangyou/index.html", "https://www.pref.shizuoka.jp/kensei/nyusatsukobai/nyusatsukenkou/index.html", "https://www.pref.shizuoka.jp/kensei/nyusatsukobai/nyusatsusports/index.html", "https://www.pref.shizuoka.jp/kensei/nyusatsukobai/koukoku/index.html"],
    "愛知県": ["https://www.pref.aichi.jp/life/5/19/index-2.html", "https://www.pref.aichi.jp/life/sub/3/19/66/"],
    "三重県": ["https://www.pref.mie.lg.jp/common/07/all000179359.htm", "https://www.pref.mie.lg.jp/app/nyusatsu/nyusatsu/00006836/0?SPI=1"],
    "滋賀県": ["https://www.pref.shiga.lg.jp/zigyousya/nyusatsubaikyaku/itaku/", "https://www.pref.shiga.lg.jp/zigyousya/nyusatsubaikyaku/itaku/#list"],
    "京都府": ["https://info.pref.kyoto.lg.jp/e-buppin/POEg/guest/generalPublishedMatterListAction.do?Cphjag-JRCBE72XnP6gWM5_1768961607952", "https://www.pref.kyoto.jp/shinchaku/nyusatsu/index.html"],
    "大阪府": ["https://www.e-nyusatsu.pref.osaka.jp/CALS/Publish/EbController?Shori=KokokuInfo", "https://www.pref.osaka.lg.jp/o040100/keiyaku_2/e-nyuusatsu/puropo.html"],
    "兵庫県": ["https://web.pref.hyogo.lg.jp/bid/bid_opn_02.html", "https://web.pref.hyogo.lg.jp/kobo_boshu/index.html"],
    "奈良県": ["https://www.pref.nara.jp/16808.htm", "https://www.pref.nara.jp/33706.htm"],
    "和歌山県": ["https://www.pref.wakayama.lg.jp/whatsnew/nyusatsu.html"],
    "鳥取県": ["https://www.pref.tottori.lg.jp/1326.htm", "https://www.pref.tottori.lg.jp/9511.htm"],
    "島根県": ["https://www.pref.shimane.lg.jp/bid_info/", "https://www.pref.shimane.lg.jp/bid_info/rireki_list.html"],
    "岡山県": ["https://www.pref.okayama.jp/site/321/", "https://www.pref.okayama.jp/site/321/list328-1555.html"],
    "広島県": ["https://www.pref.hiroshima.lg.jp/soshiki/list15-1.html", "https://www.pref.hiroshima.lg.jp/site/nyusatsukeiyaku/list945-4046.html"],
    "山口県": ["https://www.pref.yamaguchi.lg.jp/life/6/13/34/", "https://www.pref.yamaguchi.lg.jp/soshiki/list8-1.html"],
    "徳島県": ["https://www.pref.tokushima.lg.jp/ippannokata/nyusatsu/itaku/", "https://www.pref.tokushima.lg.jp/jigyoshanokata/nyusatsu/itaku/", "https://www.pref.tokushima.lg.jp/mokuteki/nyusatsu/"],
    "香川県": ["https://www.pref.kagawa.lg.jp/cgi-bin/page/list.php?tpl_type=2&page_type=5", "https://www.pref.kagawa.lg.jp/cgi-bin/page/list.php?para_page_no=2&tpl_type=2&page_type=5"],
    "愛媛県": ["https://www.pref.ehime.jp/site/nyusatsu/list92-339.html", "https://www.pref.ehime.jp/life/sub/4/47/47/"],
    "高知県": ["https://www.pref.kochi.lg.jp/category/bunya/shigoto_sangyo/nyusatsujoho/", "https://www.pref.kochi.lg.jp/category/bunya/shigoto_sangyo/nyusatsujoho/ippankyosonyusatsu_proposal/", "https://www.pref.kochi.lg.jp/category/bunya/shigoto_sangyo/nyusatsujoho/ippankyosonyusatsu_proposal/more@docs_1.html", "https://www.pref.kochi.lg.jp/category/bunya/shigoto_sangyo/nyusatsujoho/ippankyosonyusatsu_proposal/more@docs_4@c_boshujoho.html"],
    "福岡県": ["https://www.pref.fukuoka.lg.jp/bid/index.php?search_cnr_kwd=&pa%5B%5D=3&pa%5B%5D=4&pc=&pd=&pe=&pf=&search=1", "https://www.pref.fukuoka.lg.jp/bid/index.php?search_cnr_kwd=&pa%5B%5D=3&pa%5B%5D=4&pc=&pd=&pe=&pf=&search=1&page=2"],
    "佐賀県": ["https://www.pref.saga.lg.jp/list02043.html#top", "https://www.pref.saga.lg.jp/list03715.html"],
    "長崎県": ["https://www.pref.nagasaki.jp/object/nyusatsu-chotatsujoho/gyomuitaku/index.html", "https://www.pref.nagasaki.jp/index_all.html"],
    "熊本県": ["https://www.pref.kumamoto.jp/life/sub/5/index-2.html", "https://www.pref.kumamoto.jp/soshiki/list7-1.html"],
    "大分県": ["https://www.pref.oita.jp/soshiki/list14-1.html", "https://www.pref.oita.jp/site/nyusatu-koubo/list22380-29038.html", "https://www.pref.oita.jp/site/nyusatu-koubo/index-2.html"],
    "宮崎県": ["https://www.pref.miyazaki.lg.jp/kense/chotatsu/index.html", "https://www.pref.miyazaki.lg.jp/kense/chotatsu/itaku/kikakutean/index.html"],
    "鹿児島県": ["https://www.pref.kagoshima.jp/kensei/nyusatsu/nyusatujoho/index.html", "https://www.pref.kagoshima.jp/jigyosha/saishin/index.html"],
    "沖縄県": ["https://www.pref.okinawa.jp/shigoto/nyusatsukeiyaku/1015342/1025064/1037584/index.html", "https://www.pref.okinawa.jp/shigoto/nyusatsukeiyaku/1015342/1025082/1038049/index.html", "https://www.pref.okinawa.jp/shigoto/nyusatsukeiyaku/1015342/1025078/1037595/index.html", "https://www.pref.okinawa.jp/shigoto/nyusatsukeiyaku/1015342/1025067/1037594/index.html", "https://www.pref.okinawa.jp/shigoto/nyusatsukeiyaku/1015342/1025075/1037593/index.html"]
}

def get_latest_urls_via_google(pref_name: str) -> List[str]:
    api_key = os.getenv('GOOGLE_API_KEY')
    cx = os.getenv('CUSTOM_SEARCH_ENGINE_ID')
    if not api_key or not cx: return []
    query = f"{pref_name} 映像制作 委託 公募 site:pref.{pref_name}.lg.jp"
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {'key': api_key, 'cx': cx, 'q': query, 'num': 3}
    try:
        response = requests.get(search_url, params=params, timeout=10)
        return [item['link'] for item in response.json().get('items', [])]
    except: return []

def get_pagination_urls(soup: BeautifulSoup, base_url: str) -> List[str]:
    """ページ内のページネーションリンク（2, 3, 次へ等）を探す"""
    pag_urls = []
    # 数字のみのリンク、または「次へ」「>」を含むリンクを探す
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        # 1〜10の数字、または特定のキーワード
        if re.match(r'^([2-9]|10)$', text) or "次" in text or ">" in text:
            full_url = urljoin(base_url, a['href'])
            # 同一ドメイン内かつ、極端に違う階層でないことを確認
            if base_url.split('/')[2] == full_url.split('/')[2]:
                pag_urls.append(full_url)
    return list(dict.fromkeys(pag_urls))[:5] # 重複排除して最大5つ追加ページを許可

def scrape_prefecture_page(pref_name: str, url: str) -> Dict:
    keywords = ['動画', '映像', '配信', '撮影', 'プロモーション']
    results = []
    found_pag_urls = []
    try:
        logger.info(f"{pref_name}: 調査中 -> {url}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=20, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 案件リンクの抽出
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            parent_text = link.parent.get_text(strip=True) if link.parent else ''
            if any(k in (text + parent_text) for k in keywords):
                abs_url = urljoin(url, link['href'])
                results.append({'title': text or '詳細資料', 'url': abs_url})
        
        # ページネーションリンクの抽出
        found_pag_urls = get_pagination_urls(soup, url)
        
        return {"results": results, "pagination": found_pag_urls}
    except Exception as e:
        logger.warning(f"{pref_name}: アクセス失敗({url}) - {e}")
        return {"results": [], "pagination": []}

def search_all_prefectures_direct() -> Dict[str, List[Dict]]:
    all_results = {}
    for pref_name, start_urls in PREFECTURE_BID_PAGES.items():
        pref_combined_results = []
        seen_project_urls = set()
        queue = list(start_urls)
        visited_pages = set()
        
        page_count = 0
        while queue and page_count < 10: # 最大10ページまで探索
            target_url = queue.pop(0)
            if target_url in visited_pages: continue
            visited_pages.add(target_url)
            page_count += 1
            
            data = scrape_prefecture_page(pref_name, target_url)
            
            # 案件を追加
            for res in data["results"]:
                if res['url'] not in seen_project_urls:
                    seen_project_urls.add(res['url'])
                    pref_combined_results.append(res)
            
            # 新しく見つかったページネーションをキューに追加
            for p_url in data["pagination"]:
                if p_url not in visited_pages:
                    queue.append(p_url)
            
            time.sleep(0.5)

        if not pref_combined_results:
            logger.info(f"{pref_name}: ヒットなし。Google検索APIで最終救済...")
            for fb_url in get_latest_urls_via_google(pref_name):
                data = scrape_prefecture_page(pref_name, fb_url)
                for res in data["results"]:
                    if res['url'] not in seen_project_urls:
                        seen_project_urls.add(res['url'])
                        pref_combined_results.append(res)
                
        all_results[pref_name] = pref_combined_results
    return all_results
