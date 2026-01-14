"""都道府県の入札情報ページを直接スクレイピング"""

import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict
import time

logger = logging.getLogger(__name__)


# 各都道府県の入札情報ページURL
PREFECTURE_BID_PAGES = {
    "北海道": "https://www.pref.hokkaido.lg.jp/fs/2/9/2/8/9/7/8/_/nyusatsu.html",
    "青森県": "https://www.pref.aomori.lg.jp/soshiki/soumu/kaikei/nyusatsu.html",
    "岩手県": "https://www.pref.iwate.jp/kensei/nyusatsu/index.html",
    "宮城県": "https://www.pref.miyagi.jp/soshiki/nyusatsu/",
    "秋田県": "https://www.pref.akita.lg.jp/pages/genre/nyusatsu",
    "山形県": "https://www.pref.yamagata.jp/110001/bosyu/nyusatsu/",
    "福島県": "https://www.pref.fukushima.lg.jp/sec/01055a/",
    "茨城県": "https://www.pref.ibaraki.jp/bugai/kaikei/nyusatsu/",
    "栃木県": "https://www.pref.tochigi.lg.jp/c05/nyuusatsu/nyuusatsuindex.html",
    "群馬県": "https://www.pref.gunma.jp/s/nyusatsu/",
    "埼玉県": "https://www.pref.saitama.lg.jp/a0001/nyusatsu/",
    "千葉県": "https://www.pref.chiba.lg.jp/kaikei/nyuusatsu/",
    "東京都": "https://www.metro.tokyo.lg.jp/tosei/hodohappyo/press/kyoutsuu.html",
    "神奈川県": "https://www.pref.kanagawa.jp/docs/r5k/cnt/f5681/",
    "新潟県": "https://www.pref.niigata.lg.jp/sec/shukei/1356837194058.html",
    "富山県": "https://www.pref.toyama.jp/sections/1101/nyusatsu/",
    "石川県": "https://www.pref.ishikawa.lg.jp/kinyuu/nyusatsu/",
    "福井県": "https://www.pref.fukui.lg.jp/doc/keiri/koukyou/nyuusatsu.html",
    "山梨県": "https://www.pref.yamanashi.jp/kanri/nyusatsu/index.html",
    "長野県": "https://www.pref.nagano.lg.jp/kaikei/nyusatsu/",
    "岐阜県": "https://www.pref.gifu.lg.jp/soshiki/11530/",
    "静岡県": "https://www.pref.shizuoka.jp/soumu/so-310/nyusatsu/index.html",
    "愛知県": "https://www.pref.aichi.jp/soshiki/shukei/",
    "三重県": "https://www.pref.mie.lg.jp/ZAIKEI/HP/",
    "滋賀県": "https://www.pref.shiga.lg.jp/kensei/nyusatsu/",
    "京都府": "https://www.pref.kyoto.jp/zaisei/nyuusatu.html",
    "大阪府": "https://www.pref.osaka.lg.jp/keiyaku/",
    "兵庫県": "https://web.pref.hyogo.lg.jp/kk21/nyusatsujoho.html",
    "奈良県": "http://www.pref.nara.jp/1842.htm",
    "和歌山県": "https://www.pref.wakayama.lg.jp/prefg/020100/",
    "鳥取県": "https://www.pref.tottori.lg.jp/dd.aspx?menuid=3109",
    "島根県": "https://www.pref.shimane.lg.jp/admin/contract/",
    "岡山県": "https://www.pref.okayama.jp/page/311846.html",
    "広島県": "https://www.pref.hiroshima.lg.jp/soshiki/73/",
    "山口県": "https://www.pref.yamaguchi.lg.jp/soshiki/16/",
    "徳島県": "https://www.pref.tokushima.lg.jp/jigyoshanokata/nyusatsu/",
    "香川県": "https://www.pref.kagawa.lg.jp/kanri/nyusatsu/",
    "愛媛県": "https://www.pref.ehime.jp/keiri/nyusatsu/",
    "高知県": "https://www.pref.kochi.lg.jp/soshiki/110601/",
    "福岡県": "https://www.pref.fukuoka.lg.jp/contents/nyusatsu.html",
    "佐賀県": "https://www.pref.saga.lg.jp/kiji00311385/index.html",
    "長崎県": "https://www.pref.nagasaki.jp/bunrui/shigoto-sangyo/nyusatsu/",
    "熊本県": "https://www.pref.kumamoto.jp/soshiki/12/",
    "大分県": "https://www.pref.oita.jp/soshiki/10120/",
    "宮崎県": "https://www.pref.miyazaki.lg.jp/kanri/",
    "鹿児島県": "https://www.pref.kagoshima.jp/ad01/nyusatsu/",
    "沖縄県": "https://www.pref.okinawa.jp/site/somu/kaikei/nyusatsu/",
}


def scrape_prefecture_page(pref_name: str, url: str) -> List[Dict]:
    """都道府県の入札ページから映像制作関連の情報を取得"""
    
    # 映像制作関連のキーワード
    keywords = [
        '映像', '動画', 'ビデオ', 'プロモーション', 'PR', 
        '広報', '撮影', 'コンテンツ', '制作', '配信',
        'YouTube', 'SNS', 'Web'
    ]
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        logger.info(f"{pref_name}: {url} にアクセス中...")
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        results = []
        seen_urls = set()
        
        # 全てのリンクを取得
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True)
            
            # 親要素のテキストも取得
            parent_text = ''
            if link.parent:
                parent_text = link.parent.get_text(strip=True)
            
            combined_text = text + ' ' + parent_text
            
            # キーワードチェック
            if any(keyword in combined_text for keyword in keywords):
                # 相対URLを絶対URLに変換
                from urllib.parse import urljoin
                absolute_url = urljoin(url, href)
                
                # 重複チェック
                if absolute_url not in seen_urls:
                    seen_urls.add(absolute_url)
                    
                    results.append({
                        'title': text if text else '（タイトルなし）',
                        'url': absolute_url,
                        'snippet': combined_text[:200]
                    })
        
        logger.info(f"{pref_name}: {len(results)}件の映像関連リンク発見")
        return results
        
    except requests.Timeout:
        logger.warning(f"{pref_name}: タイムアウト")
        return []
    except requests.RequestException as e:
        logger.error(f"{pref_name}: アクセスエラー - {e}")
        return []
    except Exception as e:
        logger.error(f"{pref_name}: 予期しないエラー - {e}")
        return []


def search_all_prefectures_direct(max_prefectures=None) -> Dict[str, List[Dict]]:
    """全都道府県を直接スクレイピング"""
    
    all_results = {}
    
    items = list(PREFECTURE_BID_PAGES.items())
    if max_prefectures:
        items = items[:max_prefectures]
    
    for pref_name, url in items:
        logger.info(f"--- {pref_name} 直接スクレイピング開始 ---")
        
        results = scrape_prefecture_page(pref_name, url)
        all_results[pref_name] = results
        
        # レート制限対策
        time.sleep(2)
    
    # 統計情報
    total_links = sum(len(results) for results in all_results.values())
    logger.info(f"直接スクレイピング完了: 合計{total_links}件のリンク取得")
    
    return all_results
