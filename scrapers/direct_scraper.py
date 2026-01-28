"""47都道府県・20大都市 巡回エンジン（v1.6 PDFリスト透視 ＆ 全自治体統合版）"""

import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict, Set
import time
import os
import re
import unicodedata 
from urllib.parse import urljoin
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
logger = logging.getLogger(__name__)

# --- あなたの最新URLリスト（47都道府県 ＋ 20政令指定都市 ＋ 東京23区 ＋ 周辺都市 ＋ 県庁所在地） ---
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
    "石川県": ["https://www.pref.ishikawa.lg.jp/kanzai/index.html","https://www.pref.ishikawa.lg.jp/soumu/index.html","https://www.pref.ishikawa.lg.jp/johosei/index.html","https://www.pref.ishikawa.lg.jp/bousai/index.html","https://www.pref.ishikawa.lg.jp/kikaku/index.html","https://www.pref.ishikawa.lg.jp/shinkou/index.html","https://www.pref.ishikawa.lg.jp/shink/index.html","https://www.pref.ishikawa.lg.jp/muse/index.html","https://www.pref.ishikawa.lg.jp/kankou/index.html","https://www.pref.ishikawa.lg.jp/kokukan/index.html","https://www.pref.ishikawa.lg.jp/kokusai/index.html","https://www.pref.ishikawa.lg.jp/sports/index.html","https://www.pref.ishikawa.lg.jp/kousei/index.html","https://www.pref.ishikawa.lg.jp/ansin/index.html","https://www.pref.ishikawa.lg.jp/fukusi/index.html","https://www.pref.ishikawa.lg.jp/iryou/support/center.html","https://www.pref.ishikawa.lg.jp/iryou/index.html","https://www.pref.ishikawa.lg.jp/kenkou/index.html","https://www.pref.ishikawa.lg.jp/kankyo/index.html","https://www.pref.ishikawa.lg.jp/ontai/index.html","https://www.pref.ishikawa.lg.jp/haitai/index.html","https://www.pref.ishikawa.lg.jp/sizen/index.html","https://www.pref.ishikawa.lg.jp/kenmin/index.html","https://www.pref.ishikawa.lg.jp/seikatu/index.html"],
    "福井県": ["https://www.pref.fukui.lg.jp/search.html?q=%E3%83%97%E3%83%AD%E3%83%9D%E3%83%BC%E3%82%B6%E3%83%AB", "https://www.pref.fukui.lg.jp/doc/dx-suishin/sonotanyusatu.html"],
    "山梨県": ["https://www.pref.yamanashi.jp/kensei/nyusatsu/keiyaku/johokokai.html", "https://www.pref.yamanashi.jp/shinchaku/index.html"],
    "長野県": ["https://www.pref.nagano.lg.jp/kankoshin/dc_proposal3_2.html", "https://www.pref.nagano.lg.jp/kensa/puropo-kokoku.html"],
    "岐阜県": ["https://www.pref.gifu.lg.jp/site/bid/", "https://www.pref.gifu.lg.jp/bid/search/search.php?search_bid_kwd=&ctg%5B%5D=5&sec02=0&sec01=0&date1=&date2=&search=1"],
    "静岡県": ["https://www.pref.shizuoka.jp/kensei/nyusatsukobai/nyusatsuchiji/index.html", "https://www.pref.shizuoka.jp/kensei/nyusatsukobai/1072932/index.html", "https://www.pref.shizuoka.jp/kensei/nyusatsukobai/nyusatsukurashi/index.html", "https://www.pref.shizuoka.jp/kensei/nyusatsukobai/1047032/index.html", "https://www.pref.shizuoka.jp/kensei/nyusatsukobai/1077988/index.html", "https://www.pref.shizuoka.jp/kensei/nyusatsukobai/nyusatsukikikanri/index.html", "https://www.pref.shizuoka.jp/kensei/nyusatsukobai/nyusatsukeieikanri/index.html", "https://www.pref.shizuoka.jp/kensei/nyusatsukobai/nyusatsukeizaisangyou/index.html", "https://www.pref.shizuoka.jp/kensei/nyusatsukobai/nyusatsukenkou/index.html", "https://www.pref.shizuoka.jp/kensei/nyusatsukobai/nyusatsusports/index.html"],
    "愛知県": ["https://www.pref.aichi.jp/life/5/19/index-2.html", "https://www.pref.aichi.jp/life/sub/3/19/66/"],
    "三重県": ["https://www.pref.mie.lg.jp/common/07/all000179359.htm", "https://www.pref.mie.lg.jp/app/nyusatsu/nyusatsu/00006836/0?SPI=1"],
    "滋賀県": ["https://www.pref.shiga.lg.jp/zigyousya/nyusatsubaikyaku/itaku/", "https://www.pref.shiga.lg.jp/zigyousya/nyusatsubaikyaku/itaku/#list"],
    "京都府": ["https://info.pref.kyoto.lg.jp/e-buppin/POEg/guest/generalPublishedMatterListAction.do?Cphjag-JRCBE72XnP6gWM5_1768961607952", "https://www.pref.kyoto.jp/shinchaku/nyusatsu/index.html"],
    "大阪府": ["https://www.e-nyusatsu.pref.osaka.jp/CALS/Publish/EbController?Shori=KokokuInfo", "https://www.pref.osaka.lg.jp/o040100/keiyaku_2/e-nyuusatsu/puropo.html"],
    "兵庫県": ["https://web.pref.hyogo.lg.jp/bid/bid_opn_02.html", "https://web.pref.hyogo.lg.jp/kobo_boshu/index.html"],
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
    "高知県": ["https://www.pref.kochi.lg.jp/category/bunya/shigoto_sangyo/nyusatsujoho/", "https://www.pref.kochi.lg.jp/category/bunya/shigoto_sangyo/nyusatsujoho/ippankyosonyusatsu_proposal/"],
    "福岡県": ["https://www.pref.fukuoka.lg.jp/bid/index.php?search_cnr_kwd=&pa%5B%5D=3&pa%5B%5D=4&pc=&pd=&pe=&pf=&search=1", "https://www.pref.fukuoka.lg.jp/bid/index.php?search_cnr_kwd=&pa%5B%5D=3&pa%5B%5D=4&pc=&pd=&pe=&pf=&search=1&page=2"],
    "佐賀県": ["https://www.pref.saga.lg.jp/list02043.html#top", "https://www.pref.saga.lg.jp/list03715.html"],
    "長崎県": ["https://www.pref.nagasaki.jp/object/nyusatsu-chotatsujoho/gyomuitaku/index.html", "https://www.pref.nagasaki.jp/index_all.html"],
    "熊本県": ["https://www.pref.kumamoto.jp/life/sub/5/index-2.html", "https://www.pref.kumamoto.jp/soshiki/list7-1.html", "https://www.pref.kumamoto.jp/search.html?cx=016131352725075398165%3Awqoxzp2wllk&cof=FORID%3A11&ie=UTF-8&q=%E5%85%AC%E5%8B%9F&sa=%E6%A4%9C%E7%B4%A2&ss=0j0j1#gsc.tab=0&gsc.q=%E5%85%AC%E5%8B%9F&gsc.sort=date"],
    "大分県": ["https://www.pref.oita.jp/soshiki/list14-1.html", "https://www.pref.oita.jp/site/nyusatu-koubo/list22380-29038.html", "https://www.pref.oita.jp/site/nyusatu-koubo/index-2.html"],
    "宮崎県": ["https://www.pref.miyazaki.lg.jp/kense/chotatsu/index.html", "https://www.pref.miyazaki.lg.jp/kense/chotatsu/itaku/kikakutean/index.html"],
    "鹿児島県": ["https://www.pref.kagoshima.jp/kensei/nyusatsu/nyusatujoho/index.html", "https://www.pref.kagoshima.jp/jigyosha/saishin/index.html", "https://www.pref.kagoshima.jp/search/result.html?q=%E5%85%AC%E5%8B%9F&sa=%E6%A4%9C%E7%B4%A2&cx=010935469551604429717%3Afammeppf88m&ie=UTF-8&cof=FORID%3A9"],
    "沖縄県": ["https://www.pref.okinawa.jp/shigoto/nyusatsukeiyaku/1015342/1025064/1037584/index.html", "https://www.pref.okinawa.jp/shigoto/nyusatsukeiyaku/1015342/1025082/1038049/index.html", "https://www.pref.okinawa.jp/shigoto/nyusatsukeiyaku/1015342/1025078/1037595/index.html", "https://www.pref.okinawa.jp/shigoto/nyusatsukeiyaku/1015342/1025067/1037594/index.html", "https://www.pref.okinawa.jp/shigoto/nyusatsukeiyaku/1015342/1025075/1037593/index.html"],
    "札幌市": ["https://www.city.sapporo.jp/zaisei/keiyaku-kanri/anken/ippan-koubo.html"],
    "仙台市": ["https://www.city.sendai.jp/jigyosha/keyaku/jigyosha/proposal/index.html"],
    "さいたま市": ["https://www.city.saitama.lg.jp/006/001/007/index.html"],
    "千葉市": ["https://www.city.chiba.jp/portal/business/index19/nyusatsujoho/anken/other/index.html","https://www.city.chiba.jp/portal/business/index19/nyusatsujoho/anken/itaku/index.html"],
    "横浜市": ["https://www.city.yokohama.lg.jp/business/nyusatsu/kakukukyoku/allNewsList.html"],
    "川崎市": ["https://www.city.kawasaki.jp/templates/proposal/0-Curr.html"],
    "相模原市": ["https://www.city.sagamihara.kanagawa.jp/sangyo/1026667/index.html"],
    "新潟市": ["https://www.city.niigata.lg.jp/category/jigyosha/index.html"],
    "静岡市": ["https://www.city.shizuoka.lg.jp/p000358.html"],
    "浜松市": ["https://www.city.hamamatsu.shizuoka.jp/tyotatu/bid/consignment/ippan/index.html"],
    "名古屋市": ["https://www.city.nagoya.jp/jigyou/boshu/1014251/1014253/index.html","https://www.city.nagoya.jp/jigyou/boshu/1014251/1014259/index.html","https://www.city.nagoya.jp/jigyou/boshu/1014251/1014287/index.html","https://www.city.nagoya.jp/jigyou/boshu/1014251/1014314/index.html","https://www.city.nagoya.jp/jigyou/boshu/1014251/1014334/index.html"],
    "京都市": ["https://www.city.kyoto.lg.jp/menu5/category/70-3-3-0-0-0-0-0-0-0.html","https://www.city.kyoto.lg.jp/menu5/category/70-3-2-0-0-0-0-0-0-0.html","https://www.city.kyoto.lg.jp/menu5/category/70-3-4-0-0-0-0-0-0-0.html","https://www.city.kyoto.lg.jp/menu5/category/70-3-5-0-0-0-0-0-0-0.html","https://www.city.kyoto.lg.jp/menu5/category/70-3-6-0-0-0-0-0-0-0.html","https://www.city.kyoto.lg.jp/menu5/category/70-3-12-0-0-0-0-0-0-0.html","https://www.city.kyoto.lg.jp/menu5/category/70-3-7-0-0-0-0-0-0-0.html"],
    "大阪市": ["https://www.city.osaka.lg.jp/templates/proposal_hattyuuannkenn/0-Curr.html"],
    "堺市": ["https://www.city.sakai.lg.jp/sangyo/nyusatsu/chotatsu/koboanken/itaku/index.html"],
    "神戸市": ["https://www.city.kobe.lg.jp/a21572/proposal.html"],
    "岡山市": ["https://www.city.okayama.jp/jigyosha/category/5-3-13-1-17-0-0-0-0-0.html","https://www.city.okayama.jp/jigyosha/topics/0001.html"],
    "広島市": ["https://www.city.hiroshima.lg.jp/business/nyusatsu/1006046/1006060/1046169/index.html","https://www.city.hiroshima.lg.jp/business/nyusatsu/1006046/1006060/1036002/index.html"],
    "北九州市": ["https://www.city.kitakyushu.lg.jp/business/menu03_00174.html"],
    "福岡市": ["https://www.city.fukuoka.lg.jp/sub/rss/030.html","https://www.city.fukuoka.lg.jp/business/keiyaku-kobo/teiankyogi.html","https://www.city.fukuoka.lg.jp/zaisei/keiyaku-info/business/zuiikeiyaku.html"],
    "熊本市": ["https://www.city.kumamoto.jp/list04401.html"],
    # --- 🆕 追加：東京23区 ---
    "千代田区": ["https://www.city.chiyoda.lg.jp/koho/kuse/nyusatsu/proposal/index.html"],
    "中央区": ["https://www.city.chuo.lg.jp/kusei/keiyakunyusatsu/index.html"],
    "港区": ["https://www.city.minato.tokyo.jp/keiyaku/kuse/nyusatsu/keyaku/proposal-boshu.html"],
    "新宿区": ["https://www.city.shinjuku.lg.jp/jigyo/index02_pps.html"],
    "文京区": ["https://www.city.bunkyo.lg.jp/b003/p007435.html"],
    "台東区": ["https://www.city.taito.lg.jp/jigyosha/keiyaku/proposal/index.html"],
    "墨田区": ["https://www.city.sumida.lg.jp/sangyo_jigyosya/keiyaku_nyuusatu/proposal/proposal_bosyuu/index.html"],
    "江東区": ["https://www.city.koto.lg.jp/053101/20190319puropo.html"],
    "品川区": ["https://www.city.shinagawa.tokyo.jp/PC/kuseizyoho/kuseizyoho-siryo/kuseizyoho-siryo-keiyaku/kuseizyoho-siryo-keiyaku-hacchu/index.html"],
    "目黒区": ["https://www.city.meguro.tokyo.jp/shigoto/nyuusatsu/joujou/index.html"],
    "大田区": ["https://www.city.ota.tokyo.jp/jigyousha/topics/index.html"],
    "世田谷区": ["https://www.city.setagaya.lg.jp/02234/24385.html", "https://www.city.setagaya.lg.jp/kuseijouhou/keiyakunyuusatsu/category/13139.html", "https://www.city.setagaya.lg.jp/kuseijouhou/keiyakunyuusatsu/category/13140.html", "https://www.city.setagaya.lg.jp/kuseijouhou/keiyakunyuusatsu/category/13141.html", "https://www.city.setagaya.lg.jp/kuseijouhou/keiyakunyuusatsu/category/13142.html", "https://www.city.setagaya.lg.jp/kuseijouhou/keiyakunyuusatsu/category/13143.html", "https://www.city.setagaya.lg.jp/kuseijouhou/keiyakunyuusatsu/category/13144.html", "https://www.city.setagaya.lg.jp/kuseijouhou/keiyakunyuusatsu/category/13145.html"],
    "渋谷区": ["https://www.city.shibuya.tokyo.jp/jigyosha/proposal/proposal/"],
    "中野区": ["https://www.city.tokyo-nakano.lg.jp/jigyosha/osirase/index.html"],
    "杉並区": ["https://www.city.suginami.tokyo.jp/shigoto/shinchaku/index.html"],
    "豊島区": ["https://www.city.toshima.lg.jp/kuse/nyusatsu/proposal/bosyuu/index.html"],
    "北区": ["https://www.city.kita.lg.jp/city-information/contract/1011617/1019339/index.html"],
    "荒川区": ["https://www.city.arakawa.tokyo.jp/jigyousha/nyusatsu/boshuu/index.html"],
    "板橋区": ["https://www.city.itabashi.tokyo.jp/bunka/proposal/boshu/index.html"],
    "練馬区": ["https://www.city.nerima.tokyo.jp/jigyoshamuke/jigyosha/allNewsList.html"],
    "足立区": ["https://www.city.adachi.tokyo.jp/shigoto/nyusatsu/jigyosha/proposal/index.html"],
    "葛飾区": ["https://www.city.katsushika.lg.jp/business/1000011/1000067/1005056/"],
    "江戸川区": ["https://www.city.edogawa.tokyo.jp/shigotosangyo/proposal/kobo/index.html"],
    # --- 🆕 追加：周辺都市 ---
    "取手市": ["https://www.city.toride.ibaraki.jp/jigyosha/shinchaku.html"],
    "所沢市": ["https://www.city.tokorozawa.saitama.jp/shiseijoho/jigyo/index.html"],
    "松戸市": ["https://www.city.matsudo.chiba.jp/jigyosya/koubo/proposal/index.html"],
    "稲城市": ["https://www.city.inagi.tokyo.jp/sangyo/keiyaku/1005481/1005485/index.html"],
    "豊中市": ["https://www.city.toyonaka.osaka.jp/jigyosya/proposal/index.html"],
    "奈良市": ["https://www.city.nara.lg.jp/life/5/35/141/", "https://www.city.nara.lg.jp/life/5/35/index-2.html"],
    "青梅市": ["https://www.city.ome.tokyo.jp/soshiki/76/index-2.html", "https://www.city.ome.tokyo.jp/soshiki/6/10487.html"],
    "立川市": ["https://www.city.tachikawa.lg.jp/sangyo/nyusatsu/1003872/index.html"],
    "八王子市": ["https://www.city.hachioji.tokyo.jp/jigyosha/001/002/002/index.html"],
    "小田原市": ["https://www.city.odawara.kanagawa.jp/recruit/", "https://www.city.odawara.kanagawa.jp/field/municipality/jigyou/proposal/"],
    "岐阜市": ["https://www.city.gifu.lg.jp/business/nyuusatsu/1005619/1032726/index.html"],
    "豊橋市": ["https://www.city.toyohashi.lg.jp/7386.htm"],
    "春日井市": ["https://www.city.kasugai.lg.jp/business/jigyooshirase/index.html"],
    "津島市": ["https://www.city.tsushima.lg.jp/shisei/zaisei/nyuusatsukeiyaku/proposal/index.html"],
    "東海市": ["https://www.city.tokai.aichi.jp/business/1002934/1002964/index.html"],
    "四日市市": ["https://www.city.yokkaichi.lg.jp/www/genre/1586427407309/index.html"],
    "亀山市": ["https://www.city.kameyama.mie.jp/categories/bunya/business/nyusatsu/kokoku/"],
    "近江八幡市": ["https://www.city.omihachiman.lg.jp/shigoto/nyusatsu/proposal/index.html"],
    "明石市": ["https://www.city.akashi.lg.jp/seisaku/kouhou_ka/shise/nyusatsu/joho/nyusatsu/itiran.html"],
    # --- 🆕 追加：地方中枢・県庁所在地 ---
    "小樽市": ["https://www.city.otaru.lg.jp/categories/bunya/nyusatu_keiyaku/nyusatu_koujiigai/bosyu/"],
    "千歳市": ["https://www.city.chitose.lg.jp/96/98_183/98_183_1008/"],
    "塩竈市": ["https://www.city.shiogama.miyagi.jp/life/5/46/303/"],
    "呉市": ["https://www.city.kure.lg.jp/life/2/99/421/"],
    "太宰府市": ["https://www.city.dazaifu.lg.jp/life/4/26/127/"],
    "宇都宮市": ["https://www.city.utsunomiya.lg.jp/sangyo/nyusatsu/koubo/index.html"],
    "松山市": ["https://www.city.matsuyama.ehime.jp/shisei/denshinyusatsu/gyoumuitaku/info/r7itaku/index.html"],
    "鹿児島市": ["https://www.city.kagoshima.lg.jp/shise/nyusatsu/nyusatsu/itakusonota.html"],
    "郡山市": ["https://www.city.koriyama.lg.jp/site/keiyakuportal/list87-226.html"],
    "松江市": ["https://www.city.matsue.lg.jp/boshuu/index.html"],
    "徳島市": ["https://www.city.tokushima.tokushima.jp/shisei/keizai/nyusatsu/chotatsu/proposal/index.html"],
    "高知市": ["https://www.city.kochi.kochi.jp/life/2/190/1510/"],
    "高崎市": ["https://www.city.takasaki.gunma.jp/life/4/47/229/index-2.html"],
    "湯沢市": ["https://www.city-yuzawa.jp/life/2/23/151/"],
    "上越市": ["https://www.city.joetsu.niigata.jp/life/3/19/564/"],
    "今治市": ["https://www.city.imabari.ehime.jp/top_jigyosha.html"],
    "青森市": ["https://www.city.aomori.aomori.jp/sangyo_koyou/jigyosha/1004700/index.html"],
    "秋田市": ["https://www.city.akita.lg.jp/jigyosha/sonota-nyusatsu-keiyaku/index.html"],
    "山形市": ["https://www.city.yamagata-yamagata.lg.jp/jigyosya/nyusatsu/1006744/index.html"],
    "水戸市": ["https://www.city.mito.lg.jp/soshiki/list8-1.html"],
    "前橋市": ["https://www.city.maebashi.gunma.jp/sangyo_business/9/2/index.html"],
    "福井市": ["https://www.city.fukui.lg.jp/sigoto/keiyaku/proposal/index.html"],
    "甲府市": ["https://www.city.kofu.yamanashi.jp/keyaku/business/nyusatsu/nyusatsu-sonota-kobogata.html"],
    "長野市": ["https://www.city.nagano.nagano.jp/menu/7/2/7/6/1/index.html"],
    "津市": ["https://www.info.city.tsu.mie.jp/sangyou_shigoto/nyuusatsu_keiyaku/1004182/index.html"],
    "大津市": ["https://www.city.otsu.lg.jp/b/nk/pr/re/index.html"],
    "和歌山市": ["https://www.city.wakayama.wakayama.jp/jigyou/1009212/index.html"],
    "鳥取市": ["https://www.city.tottori.lg.jp/www/genre/1612833109748/index.html"],
    "山口市": ["https://www.city.yamaguchi.lg.jp/life/2/18/92/"],
    "高松市": ["https://www.city.takamatsu.kagawa.jp/jigyosha/nyusatsu/sections/proposal/r7/kohyo/index.html"],
    "佐賀市": ["https://www.city.saga.lg.jp/main/597.html"],
    "長崎市": ["https://www.city.nagasaki.lg.jp/life/5/38/164/"],
    "大分市": ["https://www.city.oita.oita.jp/shigotosangyo/proposal/proposal/kobogata/index.html"],
    "宮崎市": ["https://www.city.miyazaki.miyazaki.jp/business/bid/information/"],
    "那覇市": ["https://www.city.naha.okinawa.jp/business/touroku/1003701/1007363/index.html"],
}

def get_latest_urls_via_google(pref_name: str, base_url: str) -> List[str]:
    api_key = os.getenv('GOOGLE_API_KEY')
    cx = os.getenv('CUSTOM_SEARCH_ENGINE_ID')
    if not api_key or not cx: return []
    domain = base_url.split('/')[2]
    # クエリ強化：公募・案件・募集を反映
    query = f"site:{domain} (映像 OR 動画 OR 撮影 OR 配信 OR プロモーション OR 作成) (募集 OR 案件 OR 公募)"
    logger.info(f"🔍 Google検索実行: {query}")
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {'key': api_key, 'cx': cx, 'q': query, 'num': 10}
    try:
        response = requests.get(search_url, params=params, timeout=10)
        items = response.json().get('items', [])
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
    # 1. 映像制作そのものを指す言葉
    video_keywords = ['動画', '映像', '配信', '撮影', 'プロモーション', '作成', '制作']
    
    # 🆕 2. 【お宝救済用】案件がまとまって入っている可能性があるリスト系キーワード
    list_keywords = ['案件一覧', '募集一覧', '入札公告', '公募公告', '委託公告', '調達予定', '公募', '案件', '募集']
    
    results = []
    found_pag_urls = []
    try:
        logger.info(f"{pref_name}: 調査中 -> {url}")
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept-Language': 'ja,ja-JP;q=0.9,en-US;q=0.8,en;q=0.7'
        }
        response = requests.get(url, headers=headers, timeout=20, verify=False)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            parent_text = link.parent.get_text(strip=True) if link.parent else ''
            # 文字を正規化（全角半角の揺れを吸収）
            combined_text = unicodedata.normalize('NFKC', text + parent_text)
            
            # 除外キーワード（これらのみの場合はスルー）
            exclude_keywords = ["質問", "回答", "公表", "結果", "落札", "入札状況", "R6", "R7", "2024", "2025"]
            
            # 判定A: リンク名に直接「映像」等のキーワードが入っている
            is_video_link = any(k in combined_text for k in video_keywords)
            
            # 🆕 判定B: リンク名が「案件」「公募」等のリスト名で、かつ「PDF」である
            is_list_pdf = any(lk in combined_text for lk in list_keywords) and (".pdf" in combined_text.lower() or "pdf" in combined_text.lower())

            if is_video_link or is_list_pdf:
                # 令和8年を含まない過去年度や結果報告は除外（ただし令和8があれば救済）
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

        # 直接巡回で1件もヒットしなかった場合のみGoogle救済
        if not pref_combined_results:
            logger.info(f"{pref_name}: ヒットなし。Google検索APIで最終救済...")
            google_urls = get_latest_urls_via_google(pref_name, start_urls[0])
            for fb_url in google_urls:
                data = scrape_prefecture_page(pref_name, fb_url)
                for res in data["results"]:
                    if res['url'] not in seen_project_urls:
                        seen_project_urls.add(res['url'])
                        pref_combined_results.append(res)
                
        all_results[pref_name] = pref_combined_results
    return all_results
