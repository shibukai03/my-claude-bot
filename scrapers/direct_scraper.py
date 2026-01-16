"""都道府県の入札情報ページを直接スクレイピング（404エラー時のGoogle検索救済機能付き）"""

import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict
import time
import os
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

# 全47都道府県の最新URLリスト（静的な入り口）
PREFECTURE_BID_PAGES = {
    "北海道": "https://www.pref.hokkaido.lg.jp/sm/sum/nyusatsu/index.html",
    "青森県": "https://www.pref.aomori.lg.jp/sangyo/build/nyusatsu_jouhou.html",
    "岩手県": "https://www.pref.iwate.jp/kensei/nyusatsu/index.html",
    "宮城県": "https://www.pref.miyagi.jp/soshiki/keiyaku/kst.html",
    "秋田県": "https://www.pref.akita.lg.jp/pages/genre/nyusatsu",
    "山形県": "https://www.pref.yamagata.jp/110001/bosyu/nyusatsu/",
    "福島県": "https://www.pref.fukushima.lg.jp/sec/01055a/nyuusatsu_portal.html",
    "茨城県": "https://www.pref.ibaraki.jp/bugai/kaikei/nyusatsu/index.html",
    "栃木県": "https://www.pref.tochigi.lg.jp/c05/nyuusatsu/nyuusatsuindex.html",
    "群馬県": "https://www.pref.gunma.jp/page/nyusatsu.html",
    "埼玉県": "https://www.pref.saitama.lg.jp/a0201/shiryo/nyusatsu-portal.html",
    "千葉県": "https://www.pref.chiba.lg.jp/kaikei/nyuusatsu/index.html",
    "東京都": "https://www.e-procurement.metro.tokyo.lg.jp/index.jsp",
    "神奈川県": "https://www.pref.kanagawa.jp/docs/r5k/cnt/f5681/",
    "新潟県": "https://www.pref.niigata.lg.jp/sec/shukei/1356837194058.html",
    "富山県": "https://www.pref.toyama.jp/1101/sangyou/nyuusatsu/",
    "石川県": "https://www.pref.ishikawa.lg.jp/nanaonourin/nyuusatu/nyuusatu.html",
    "福井県": "https://www.pref.fukui.lg.jp/doc/keiri/koukyou/nyuusatsu.html",
    "山梨県": "https://www.pref.yamanashi.jp/kanri/nyusatsu/index.html",
    "長野県": "https://www.pref.nagano.lg.jp/kaikei/nyusatsu/",
    "岐阜県": "https://www.pref.gifu.lg.jp/soshiki/11530/",
    "静岡県": "https://www.pref.shizuoka.jp/soumu/so-310/nyusatsu/index.html",
    "愛知県": "https://www.pref.aichi.jp/soshiki/shukei/nyusatsu.html",
    "三重県": "https://www.pref.mie.lg.jp/ZAIKEI/HP/index.htm",
    "滋賀県": "https://www.pref.shiga.lg.jp/kensei/nyusatsu/",
    "京都府": "https://www.pref.kyoto.jp/zaisei/nyuusatu.html",
    "大阪府": "https://www.pref.osaka.lg.jp/o130330/otori/nyusatsu/index.html",
    "兵庫県": "https://web.pref.hyogo.lg.jp/kk21/nyusatsujoho.html",
    "奈良県": "https://www.pref.nara.jp/10553.htm",
    "和歌山県": "https://www.pref.wakayama.lg.jp/prefg/020100/index.html",
    "鳥取県": "https://www.pref.tottori.lg.jp/dd.aspx?menuid=3109",
    "島根県": "https://www.pref.shimane.lg.jp/admin/contract/nyusatsu/",
    "岡山県": "https://www.pref.okayama.jp/page/311846.html",
    "広島県": "https://chotatsu.pref.hiroshima.lg.jp/nyusatsu/index.html",
    "山口県": "https://www.pref.yamaguchi.lg.jp/soshiki/127/23376.html",
    "徳島県": "https://www.pref.tokushima.lg.jp/ippannokata/nyusatsu/",
    "香川県": "https://www.pref.kagawa.lg.jp/kanri/nyusatsu/index.html",
    "愛媛県": "https://www.pref.ehime.jp/site/nyusatsu/39222.html",
    "高知県": "https://www.pref.kochi.lg.jp/soshiki/110601/nyusatsu-top.html",
    "福岡県": "https://www.pref.fukuoka.lg.jp/contents/nyusatsu.html",
    "佐賀県": "https://www.pref.saga.lg.jp/kiji00311385/index.html",
    "長崎県": "https://www.pref.nagasaki.jp/bunrui/shigoto-sangyo/nyusatsu/",
    "熊本県": "https://www.pref.kumamoto.lg.jp/soshiki/12/",
    "大分県": "https://www.pref.oita.jp/site/nyusatu-koubo/index.html",
    "宮崎県": "https://www.pref.miyazaki.lg.jp/kanri/nyusatsu/index.html",
    "鹿児島県": "https://www.pref.kagoshima.jp/ad01/nyusatsu/index.html",
    "沖縄県": "https://www.pref.okinawa.jp/site/somu/kaikei/nyusatsu/"
}

def get_latest_urls_via_google(pref_name: str) -> List[str]:
    """【新機能】Google検索を使って最新の入札ページURLを探す"""
    api_key = os.getenv('GOOGLE_API_KEY')
    cx = os.getenv('CUSTOM_SEARCH_ENGINE_ID')
    
    if not api_key or not cx:
        logger.warning(f"{pref_name}: Google APIキーまたはCX IDが設定されていません。検索をスキップします。")
        return []

    # 検索クエリ： 「〇〇県 映像制作 入札 公募」
    query = f"{pref_name} 映像制作 入札 公募 site:pref.*.lg.jp"
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'key': api_key,
        'cx': cx,
        'q': query,
        'num': 3  # 上位3件を取得
    }

    try:
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        search_results = response.json()
        links = [item['link'] for item in search_results.get('items', [])]
        logger.info(f"{pref_name}: Google検索により {len(links)} 件の新しい候補URLを発見")
        return links
    except Exception as e:
        logger.error(f"{pref_name}: Google検索エラー - {e}")
        return []

def scrape_prefecture_page(pref_name: str, url: str) -> List[Dict]:
    """特定のURLから映像制作関連のリンクを抽出する（中身のロジックは維持）"""
    keywords = ['映像', '動画', 'ビデオ', 'プロモーション', 'PR', '広報', '撮影', '制作', '配信']
    
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        logger.info(f"{pref_name}: 調査対象URL -> {url}")
        
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        results = []
        seen_urls = set()
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)
            parent_text = link.parent.get_text(strip=True) if link.parent else ''
            combined_text = text + ' ' + parent_text
            
            if any(keyword in combined_text for keyword in keywords):
                absolute_url = urljoin(url, href)
                if absolute_url not in seen_urls:
                    seen_urls.add(absolute_url)
                    results.append({
                        'title': text if text else '（タイトルなし）',
                        'url': absolute_url,
                        'snippet': combined_text[:200]
                    })
        return results
    except Exception as e:
        logger.warning(f"{pref_name}: このURLの解析に失敗しました ({url}) - {e}")
        return []

def search_all_prefectures_direct(max_prefectures=None) -> Dict[str, List[Dict]]:
    """【改良版】全都道府県を巡回し、必要に応じてGoogle検索で補完する"""
    all_results = {}
    items = list(PREFECTURE_BID_PAGES.items())
    if max_prefectures:
        items = items[:max_prefectures]
    
    for pref_name, default_url in items:
        logger.info(f"--- {pref_name} 調査開始 ---")
        
        # 1. まずは固定URLを試す
        results = scrape_prefecture_page(pref_name, default_url)
        
        # 2. もし固定URLで何も見つからない、またはエラーだった場合、Google検索を発動
        if not results:
            logger.info(f"{pref_name}: 固定URLで成果なし。Google検索APIで救済措置を実行します...")
            fallback_urls = get_latest_urls_via_google(pref_name)
            
            for fb_url in fallback_urls:
                fb_results = scrape_prefecture_page(pref_name, fb_url)
                results.extend(fb_results)
                if fb_results:
                    logger.info(f"{pref_name}: Googleが見つけたURLから {len(fb_results)} 件の情報を取得成功！")
        
        all_results[pref_name] = results
        time.sleep(2)  # サーバーに優しく
    
    total_links = sum(len(results) for results in all_results.values())
    logger.info(f"ハイブリッド・スクレイピング完了: 合計{total_links}件のリンク取得")
    return all_results
