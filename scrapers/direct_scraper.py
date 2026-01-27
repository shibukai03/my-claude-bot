"""47都道府県 入札・公募ページ全ページ巡回エンジン（v1.4 Google検索救済・ログ強化版）"""

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

# URLリスト
PREFECTURE_BID_PAGES = {
    "北海道": ["https://www.pref.hokkaido.lg.jp/news/nyusatsu/", "https://www.pref.hokkaido.lg.jp/category/d001/c001/s002/"],
    "青森県": ["https://www.pref.aomori.lg.jp/soshiki/suito/keiri/buppin-top.html", "https://www.pref.aomori.lg.jp/boshu/index_1.html"],
    "岩手県": ["https://www.pref.iwate.jp/kensei/nyuusatsu/it/1024231/index.html", "https://www.pref.iwate.jp/news/1016275.html"],
    "宮城県": ["https://www.pref.miyagi.jp/life/8/40/105/index.html", "https://www.pref.miyagi.jp/soshiki/keiyaku/r7puropo.html"],
    "秋田県": ["https://www.pref.akita.lg.jp/pages/genre/12121", "https://www.pref.akita.lg.jp/pages/genre/12231"],
    "山形県": ["https://www.pref.yamagata.jp/kensei/nyuusatsujouhou/nyuusatsujouhou/jyokyo/index.html", "https://www.pref.yamagata.jp/kensei/nyuusatsujouhou/nyuusatsujouhou/proposal/index.html"],
    "福島県": ["https://www.pref.fukushima.lg.jp/sec/01115c/nyusatsujoho.html", "https://www.pref.fukushima.lg.jp/sec/55015a/suitou-proposal.html"],
    "茨城県": ["https://www.pref.ibaraki.jp/shiru/news.html", "https://www.pref.ibaraki.jp/bosyu.html"],
    "栃木県": ["https://www.pref.tochigi.lg.jp/kensei/nyuusatsu/koubo-itaku/index.html", "https://www.pref.tochigi.lg.jp/kensei/nyuusatsu/koubo-koukyou/index.html","https://www.pref.tochigi.lg.jp/kensei/nyuusatsu/koubo-buppin/index.html"],
    "群馬県": ["https://www.pref.gunma.jp/site/nyuusatsu/index-2.html", "https://www.pref.gunma.jp/site/nyuusatsu/list135-773.html"],
    "埼玉県": ["https://www.pref.saitama.lg.jp/a0212/kense/tetsuzuki/nyusatsu/buppin/index.html", "https://www.pref.saitama.lg.jp/search/result.html?q=%E5%85%AC%E5%8B%9F&sa=%E6%A4%9C%E7%B4%A2&cx=0898cdc8c417302e4&ie=UTF-8&cof=FORID%3A9"],
    "千葉県": ["https://www.pref.chiba.lg.jp/nyuu-kei/buppin-itaku/index.html", "https://www.pref.chiba.lg.jp/nyuu-kei/buppin-itaku/nyuusatsukoukoku/koukoku/index.html"],
    "東京都": ["https://www.e-procurement.metro.tokyo.lg.jp/SrvPublish", "https://www.metro.tokyo.lg.jp/search?keyword=&purpose=163047"],
    "神奈川県": ["https://www.pref.kanagawa.jp/search.html?q=%E5%85%AC%E5%8B%9F&sa=%E6%A4%9C%E7%B4%A2&cx=007296304677419487325%3Afufp31hx7qk&ie=UTF-8&cof=FORID%3A9#gsc.tab=0&gsc.q=%E5%85%A5%E6%9C%AD&gsc.sort=date", "https://www.pref.kanagawa.jp/search.htmlq=%E5%85%AC%E5%8B%9F&sa=%E6%A4%9C%E7%B4%A2&cx=007296304677419487325%3Afufp31hx7qk&ie=UTF-8&cof=FORID%3A9#gsc.tab=0&gsc.q=%E5%85%AC%E5%8B%9F&gsc.sort=date"],
    "新潟県": ["https://www.pref.niigata.lg.jp/life/sub/8/index-2.html", "https://www.pref.niigata.lg.jp/sec/list1-1.html"],
    "富山県": ["https://www.pref.toyama.jp/sangyou/nyuusatsu/jouhou/ekimu/koukokukekka/koukoku.html", "https://www.pref.toyama.jp/sangyou/nyuusatsu/koubo/bosyuu.html"],
    "石川県": ["https://www.pref.ishikawa.lg.jp/search/result.html?q=%E3%83%97%E3%83%AD%E3%83%9D%E3%83%BC%E3%82%B6%E3%83%AB&sa=%E6%A4%9C%E7%B4%A2&cx=013090918390897489992%3Axcsb1hsaoy4&ie=UTF-8&cof=FORID%3A9#gsc.tab=0&gsc.q=%E3%83%97%E3%83%AD%E3%83%9D%E3%83%BC%E3%82%B6%E3%83%AB&gsc.sort=date", "https://www.pref.ishikawa.lg.jp/search/result.html?q=%E3%83%97%E3%83%AD%E3%83%9D%E3%83%BC%E3%82%B6%E3%83%AB&sa=%E6%A4%9C%E7%B4%A2&cx=013090918390897489992%3Axcsb1hsaoy4&ie=UTF-8&cof=FORID%3A9#gsc.tab=0&gsc.q=%E3%83%97%E3%83%AD%E3%83%9D%E3%83%BC%E3%82%B6%E3%83%AB%E3%80%80%E5%8B%95%E7%94%BB&gsc.sort=date","https://www.pref.ishikawa.lg.jp/kanzai/index.html","https://www.pref.ishikawa.lg.jp/soumu/index.html","https://www.pref.ishikawa.lg.jp/johosei/index.html","https://www.pref.ishikawa.lg.jp/bousai/index.html","https://www.pref.ishikawa.lg.jp/kikaku/index.html","https://www.pref.ishikawa.lg.jp/shinkou/index.html","https://www.pref.ishikawa.lg.jp/shink/index.html","https://www.pref.ishikawa.lg.jp/muse/index.html","https://www.pref.ishikawa.lg.jp/kankou/index.html","https://www.pref.ishikawa.lg.jp/kokukan/index.html","https://www.pref.ishikawa.lg.jp/kokusai/index.html","https://www.pref.ishikawa.lg.jp/sports/index.html","https://www.pref.ishikawa.lg.jp/kousei/index.html","https://www.pref.ishikawa.lg.jp/ansin/index.html","https://www.pref.ishikawa.lg.jp/fukusi/index.html","https://www.pref.ishikawa.lg.jp/iryou/support/center.html","https://www.pref.ishikawa.lg.jp/iryou/index.html","https://www.pref.ishikawa.lg.jp/kenkou/index.html","https://www.pref.ishikawa.lg.jp/kankyo/index.html","https://www.pref.ishikawa.lg.jp/ontai/index.html","https://www.pref.ishikawa.lg.jp/haitai/index.html","https://www.pref.ishikawa.lg.jp/sizen/index.html","https://www.pref.ishikawa.lg.jp/kenmin/index.html","https://www.pref.ishikawa.lg.jp/seikatu/index.html"],
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
    "兵庫県": ["https://web.pref.hyogo.lg.jp/bid/bid_opn_02.html", "https://web.pref.hyogo.lg.jp/kobo_boshu/index.html","https://web.pref.hyogo.lg.jp/kobo_boshu/safe/cate2_801.html", "https://web.pref.hyogo.lg.jp/kobo_boshu/life/cate2_101.html","https://web.pref.hyogo.lg.jp/kobo_boshu/life/cate2_107.html", "https://web.pref.hyogo.lg.jp/kobo_boshu/life/cate2_104.html","https://web.pref.hyogo.lg.jp/kobo_boshu/life/cate2_106.html", "https://web.pref.hyogo.lg.jp/kobo_boshu/town/cate2_209.html","https://web.pref.hyogo.lg.jp/kobo_boshu/town/cate2_202.html", "https://web.pref.hyogo.lg.jp/kobo_boshu/town/cate2_201.html","https://web.pref.hyogo.lg.jp/kobo_boshu/town/cate2_203.html", "https://web.pref.hyogo.lg.jp/kobo_boshu/work/cate2_308.html","https://web.pref.hyogo.lg.jp/kobo_boshu/work/cate2_301.html", "https://web.pref.hyogo.lg.jp/kobo_boshu/aff/cate2_402.html","https://web.pref.hyogo.lg.jp/kobo_boshu/aff/cate2_404.html", "https://web.pref.hyogo.lg.jp/kobo_boshu/aff/cate2_406.html","https://web.pref.hyogo.lg.jp/kobo_boshu/aff/cate2_407.html", "https://web.pref.hyogo.lg.jp/kobo_boshu/aff/cate2_401.html","https://web.pref.hyogo.lg.jp/kobo_boshu/aff/cate2_403.html", "https://web.pref.hyogo.lg.jp/kobo_boshu/aff/cate2_405.html","https://web.pref.hyogo.lg.jp/kobo_boshu/interaction/cate2_503.html", "https://web.pref.hyogo.lg.jp/kobo_boshu/interaction/cate2_505.html","https://web.pref.hyogo.lg.jp/kobo_boshu/interaction/cate3_510.html", "https://web.pref.hyogo.lg.jp/kobo_boshu/interaction/cate2_502.html","https://web.pref.hyogo.lg.jp/kobo_boshu/interaction/cate2_504.html", "https://web.pref.hyogo.lg.jp/kobo_boshu/interaction/cate2_507.html","https://web.pref.hyogo.lg.jp/kobo_boshu/interaction/cate2_501.html", "https://web.pref.hyogo.lg.jp/kobo_boshu/pref/cate2_602.html"],
    "奈良県": ["https://www.pref.nara.jp/16808.htm", "https://www.pref.nara.jp/33706.htm", "https://www.pref.nara.jp/module/16303.htm#moduleid16303"],
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
    "熊本県": ["https://www.pref.kumamoto.jp/life/sub/5/index-2.html", "https://www.pref.kumamoto.jp/soshiki/list7-1.html", "https://www.pref.kumamoto.jp/search.html?cx=016131352725075398165%3Awqoxzp2wllk&cof=FORID%3A11&ie=UTF-8&q=%E5%85%AC%E5%8B%9F&sa=%E6%A4%9C%E7%B4%A2&ss=0j0j1#gsc.tab=0&gsc.q=%E5%85%AC%E5%8B%9F&gsc.sort=date"],
    "大分県": ["https://www.pref.oita.jp/soshiki/list14-1.html", "https://www.pref.oita.jp/site/nyusatu-koubo/list22380-29038.html", "https://www.pref.oita.jp/site/nyusatu-koubo/index-2.html"],
    "宮崎県": ["https://www.pref.miyazaki.lg.jp/kense/chotatsu/index.html", "https://www.pref.miyazaki.lg.jp/kense/chotatsu/itaku/kikakutean/index.html"],
    "鹿児島県": ["https://www.pref.kagoshima.jp/kensei/nyusatsu/nyusatujoho/index.html", "https://www.pref.kagoshima.jp/jigyosha/saishin/index.html", "https://www.pref.kagoshima.jp/search/result.html?q=%E5%85%AC%E5%8B%9F&sa=%E6%A4%9C%E7%B4%A2&cx=010935469551604429717%3Afammeppf88m&ie=UTF-8&cof=FORID%3A9"],
    "沖縄県": ["https://www.pref.okinawa.jp/shigoto/nyusatsukeiyaku/1015342/1025064/1037584/index.html", "https://www.pref.okinawa.jp/shigoto/nyusatsukeiyaku/1015342/1025082/1038049/index.html", "https://www.pref.okinawa.jp/shigoto/nyusatsukeiyaku/1015342/1025078/1037595/index.html", "https://www.pref.okinawa.jp/shigoto/nyusatsukeiyaku/1015342/1025067/1037594/index.html", "https://www.pref.okinawa.jp/shigoto/nyusatsukeiyaku/1015342/1025075/1037593/index.html"],
    "札幌市": ["https://www.city.sapporo.jp/keiyaku/itaku/index.html"],
    "仙台市": ["https://www.city.sendai.jp/business/nyusatsu/index.html"],
    "さいたま市": ["https://www.city.saitama.lg.jp/005/001/011/index.html"],
    "千葉市": ["https://www.city.chiba.jp/zaiseikyoku/zaisei/keiyaku/itakukokoku.html"],
    "横浜市": ["https://www.city.yokohama.lg.jp/business/nyusatsu/kakukukyoku/2026/itaku/"],
    "川崎市": ["https://www.city.kawasaki.jp/shisei/category/51-1-0-0-0-0-0-0-0-0.html"],
    "相模原市": ["https://www.city.sagamihara.kanagawa.jp/sangyo/nyusatsu/1026857/index.html"],
    "新潟市": ["https://www.city.niigata.lg.jp/business/nyusatsu/index.html"],
    "静岡市": ["https://www.city.shizuoka.lg.jp/s7253/s002166.html"],
    "浜松市": ["https://www.city.hamamatsu.shizuoka.jp/keiyaku/nyusatsu/index.html"],
    "名古屋市": ["https://www.city.nagoya.jp/shisei/category/74-12-0-0-0-0-0-0-0-0.html"],
    "京都市": ["https://www.city.kyoto.lg.jp/contents/pbi/index.html"],
    "大阪市": ["https://www.city.osaka.lg.jp/templates/proposal_hattyuuannkenn/0-Curr.html"],
    "堺市": ["https://www.city.sakai.lg.jp/sangyo/nyusatsu/index.html"],
    "神戸市": ["https://www.city.kobe.lg.jp/a30145/business/bidding/itaku/index.html"],
    "岡山市": ["https://www.city.okayama.jp/category/00001552.html"],
    "広島市": ["https://www.city.hiroshima.lg.jp/site/nyusatsu/"],
    "北九州市": ["https://www.city.kitakyushu.lg.jp/shiseidatsu/menu05_0001.html"],
    "福岡市": ["https://www.city.fukuoka.lg.jp/zaisei/keiyaku/business/buppin-itaku/index.html"],
    "熊本市": ["https://www.city.kumamoto.jp/hpkiji/pub/List.aspx?c_id=5&class_set_id=2&class_id=141"]
}

def get_latest_urls_via_google(pref_name: str, base_url: str) -> List[str]:
    """
    直接巡回でヒットしなかった場合のGoogle検索バックアップ（キーワード拡張 ＆ ログ強化版）
    """
    api_key = os.getenv('GOOGLE_API_KEY')
    cx = os.getenv('CUSTOM_SEARCH_ENGINE_ID')
    if not api_key or not cx: return []
    
    # ドメインをURLから抽出（例: pref.miyagi.lg.jp）
    domain = base_url.split('/')[2]
    
    # 🆕 ご要望のキーワードに拡張
    query = f"site:{domain} (映像 OR 動画 OR 撮影 OR 配信 OR プロモーション) 募集"
    
    # 🆕 クエリをログに出力
    logger.info(f"🔍 Google検索実行: {query}")
    
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {'key': api_key, 'cx': cx, 'q': query, 'num': 10} # 救済なので上位10件取得
    
    try:
        response = requests.get(search_url, params=params, timeout=10)
        items = response.json().get('items', [])
        
        # 🆕 ヒット件数をログに出力
        logger.info(f"🎯 Google検索結果: {len(items)}件の候補URLを取得しました")
        
        return [item['link'] for item in items]
    except Exception as e:
        logger.error(f"❌ Google検索中にエラー: {e}")
        return []

def get_pagination_urls(soup: BeautifulSoup, base_url: str) -> List[str]:
    """ページ内のページネーションリンク（2, 3, 次へ等）を探す"""
    pag_urls = []
    for a in soup.find_all('a', href=True):
        text = a.get_text(strip=True)
        if re.match(r'^([2-9]|10)$', text) or "次" in text or ">" in text:
            full_url = urljoin(base_url, a['href'])
            if base_url.split('/')[2] == full_url.split('/')[2]:
                pag_urls.append(full_url)
    return list(dict.fromkeys(pag_urls))[:5]

def scrape_prefecture_page(pref_name: str, url: str) -> Dict:
    # Google検索結果もこのキーワードでフィルタリングされます
    keywords = ['動画', '映像', '配信', '撮影', 'プロモーション', '作成']
    results = []
    found_pag_urls = []
    try:
        logger.info(f"{pref_name}: 調査中 -> {url}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=20, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            parent_text = link.parent.get_text(strip=True) if link.parent else ''
            
            # 除外キーワード（質問回答などはここで捨てる）
            exclude_keywords = ["質問", "回答", "公表", "結果", "落札", "入札状況", "R6", "R7", "2024", "2025"]
            combined_text = (text + parent_text)
            
            if any(k in combined_text for k in keywords):
                # 令和8年を含まない過去年度は除外
                if any(ex in combined_text for ex in exclude_keywords) and "令和8" not in combined_text:
                    continue
                    
                abs_url = urljoin(url, link['href'])
                results.append({'title': text or '詳細資料', 'url': abs_url})
        
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
        while queue and page_count < 10:
            target_url = queue.pop(0)
            if target_url in visited_pages: continue
            visited_pages.add(target_url)
            page_count += 1
            
            data = scrape_prefecture_page(pref_name, target_url)
            for res in data["results"]:
                if res['url'] not in seen_project_urls:
                    seen_project_urls.add(res['url'])
                    pref_combined_results.append(res)
            
            for p_url in data["pagination"]:
                if p_url not in visited_pages:
                    queue.append(p_url)
            
            time.sleep(0.5)

        # 🆕 直接巡回で1件も「映像系」が見つからなかった場合のみGoogle検索救済を発動
        if not pref_combined_results:
            logger.info(f"{pref_name}: ヒットなし。Google検索APIで最終救済...")
            # 第一URLのドメインを使って検索
            google_urls = get_latest_urls_via_google(pref_name, start_urls[0])
            for fb_url in google_urls:
                data = scrape_prefecture_page(pref_name, fb_url)
                for res in data["results"]:
                    if res['url'] not in seen_project_urls:
                        seen_project_urls.add(res['url'])
                        pref_combined_results.append(res)
                
        all_results[pref_name] = pref_combined_results
    return all_results
