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

# --- 47都道府県 ＋ 20政令市 ＋ 東京23区 ＋ 新規追加 70件以上の自治体 ---
PREFECTURE_BID_PAGES = {
    # --- 既存の広域自治体 ---
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
    "神奈川県": ["https://www.pref.kanagawa.jp/search.html?q=%E5%85%AC%E5%8B%9F&sa=%E6%A4%9C%E7%B4%A2&cx=007296304677419487325%3Afufp31hx7qk&ie=UTF-8&cof=FORID%3A9#gsc.tab=0&gsc.q=%E5%85%A5%E6%9C%AD&gsc.sort=date"],
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
    "鹿児島県": ["https://www.pref.kagoshima.jp/jigyosha/saishin/index.html", "https://www.pref.kagoshima.jp/search/result.html?q=%E5%85%AC%E5%8B%9F&sa=%E6%A4%9C%E7%B4%A2&cx=010935469551604429717%3Afammeppf88m&ie=UTF-8&cof=FORID%3A9"],
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

    # --- 🆕 今回の追加分（約70件） ---
    "函館市": ["https://www.city.hakodate.hokkaido.jp/search.html?keyword=%E3%83%97%E3%83%AD%E3%83%9D%E3%83%BC%E3%82%B6%E3%83%AB&started_at=&closed_at=&per=30&order=display_updated_at_desc&kind=title&site_category_id=&site_group_id="],
    "旭川市": ["https://www.city.asahikawa.hokkaido.jp/500/565/566/5681/index.html"],
    "苫小牧市": ["https://www.city.tomakomai.hokkaido.jp/shisei/zaisei/kojikeiyaku/puropozaruboshu/"],
    "八戸市": ["https://www.city.hachinohe.aomori.jp/jigyoshamuke/nyusatsu_keiyaku/kobojoho/index.html"],
    "石巻市": ["https://www.city.ishinomaki.lg.jp/d0020/d0010/d0040/040/010/index.html"],
    "藤沢市": ["https://www.city.fujisawa.kanagawa.jp/shigoto/nyusatsu/proposal/index.html"],
    "横須賀市": ["https://www.city.yokosuka.kanagawa.jp/shisei/keiyaku/index.html"],
    "調布市": ["https://www.city.chofu.lg.jp/sangyou/nyuusatsu/proposal/guideline/index.html"],
    "越谷市": ["https://www.city.koshigaya.saitama.jp/kurashi_shisei/jigyosha/koukokubosyuu/oshirase/index.html"],
    "川越市": ["https://www.city.kawagoe.saitama.jp/sangyo/nyusatsu/1011749/1011776/1017300/index.html"],
    "久留米市": ["https://www.city.kurume.fukuoka.jp/1090sangyou/2010nyuusatsu/3110proposal/"],
    "佐世保市": ["https://www.city.sasebo.lg.jp/jigyosha/kejiban/index.html"],
    "別府市": ["https://www.city.beppu.oita.jp/sangyou/nyuusatu_keiyaku/itaku/"],
    "延岡市": ["https://www.city.nobeoka.miyazaki.jp/life/2/20/86/"],
    "都城市": ["https://www.google.com/search?q=%E9%83%BD%E5%9F%8E%E5%B8%82%20%E5%85%AC%E5%8B%9F%E5%9E%8B%E3%83%97%E3%83%AD%E3%83%9D%E3%83%BC%E3%82%B6%E3%83%AB", "https://www.city.miyakonojo.miyazaki.jp/life/4/48/255/"],
    "飯塚市": ["https://www.city.iizuka.lg.jp/sangyo/proposal/index.html"],
    "大牟田市": ["https://www.city.omuta.lg.jp/list01149.html"],
    "諫早市": ["https://www.city.isahaya.nagasaki.jp/life/5/21/90/"],
    "沖縄市": ["https://www.city.okinawa.okinawa.jp/sangyou/nyusatsukeiyaku/nyusatsujouhou/proposal/index.html"],
    "石垣市": ["https://www.city.ishigaki.okinawa.jp/soshiki/kikaku_seisaku/2/2/index.html"],
    "天草市": ["https://www.city.amakusa.kumamoto.jp/list00725.html"],
    "ニセコ町": ["https://www.town.niseko.lg.jp/boshu/"],
    "いわき市": ["https://www.city.iwaki.lg.jp/www/genre/1000100000273/index.html"],
    "会津若松市": ["https://www.city.aizuwakamatsu.fukushima.jp/category/bunya/nyusatsujoho/03_kobo_kokoku/more@docs_1.html"],
    "つくば市": ["https://www.city.tsukuba.lg.jp/nusatsu/joho/1005222/index.html"],
    "日立市": ["https://www.city.hitachi.lg.jp/sangyo_business/nyusatsu_keiyaku/1002992/index.html"],
    "船橋市": ["https://www.city.funabashi.lg.jp/jigyou/nyusatsu/001/index.html"],
    "市川市": ["https://www.city.ichikawa.lg.jp/catpage/cat_00140023.html"],
    "柏市": ["https://www.city.kashiwa.lg.jp/jigyosha/tender_contract/proposal/boshuchu/index.html"],
    "成田市": ["https://www.city.narita.chiba.jp/business/index0259.html"],
    "川口市": ["https://www.city.kawaguchi.lg.jp/jigyoshamuke/nyusatsu_keiyakujoho/puropokikaku/index.html"],
    "熊谷市": ["https://www.city.kumagaya.lg.jp/about/jigyousya/keiyaku/koubopropo/bosyuu/index.html"],
    "町田市": ["https://www.city.machida.tokyo.jp/jigyousha/nyusatsu/puropo/kobogata/index.html"],
    "武蔵野市": ["https://www.city.musashino.lg.jp/shiseijoho/keiyaku_nyusatsu/kohyoanken/proposal_joho/index.html"],
    "三鷹市": ["https://www.city.mitaka.lg.jp/c_categories/index08001.html"],
    "茅ヶ崎市": ["https://www.city.chigasaki.kanagawa.jp/about/update.html"],
    "厚木市": ["https://www.city.atsugi.kanagawa.jp/shigoto_sangyo/nyusatsu_keiyaku/2/2/index.html"],
    "鎌倉市": ["https://www.city.kamakura.kanagawa.jp/shisei/boshuu/jigyousha/index.html"],
    "富山市": ["https://www.city.toyama.lg.jp/business/nyusatsu/1014598/1014599.html"],
    "長岡市": ["https://www.city.nagaoka.niigata.jp/sangyou/cate09/propo/r07propo.html"],
    "松本市": ["https://www.city.matsumoto.nagano.jp/site/nyusatsu-keiyaku/list473-1677.html"],
    "軽井沢町": ["https://www.town.karuizawa.lg.jp/life/4/16/84/"],
    "沼津市": ["https://www.city.numazu.shizuoka.jp/business/proposal/"],
    "熱海市": ["https://www.city.atami.lg.jp/jigyosha/nyusatsu/1001735/index.html"],
    "富士市": ["https://www.city.fuji.shizuoka.jp/shigoto/nyusatsu/gyomuitaku/boshuchu/index.html"],
    "豊田市": ["https://www.city.toyota.aichi.jp/jigyousha/proposal/1030252/index.html"],
    "岡崎市": ["https://www.city.okazaki.lg.jp/1400/1401/1413/index.html"],
    "安城市": ["https://www.city.anjo.aichi.jp/zigyo/nyusatsu/keiyaku/hacchuukeiji/index.html"],
    "桑名市": ["https://www.city.kuwana.lg.jp/shigoto/nyuusatsu/nyuusatsu/proposal/index.html"],
    "姫路市": ["https://www.city.himeji.lg.jp/sangyo/category/4-3-2-1-3-3-2-0-0-0.html"],
    "西宮市": ["https://www.nishi.or.jp/jigyoshajoho/keiyaku/nyusatsu/puropozarutou/proposalkobo/index.html"],
    "尼崎市": ["https://www.city.amagasaki.hyogo.jp/sangyo/zigyousya/co_bosyu/index.html"],
    "加古川市": ["https://www.city.kakogawa.lg.jp/jigyoshanokatae/nyusatsukeiyaku/zigyosyabosyu/buppin_gyomuitaku_poropoto/puropo/index.html"],
    "吹田市": ["https://www.city.suita.osaka.jp/sangyo/1017983/1018018/1038310/index.html"],
    "高槻市": ["https://www.city.takatsuki.osaka.jp/site/nyusatsu-keiyaku/index-2.html"],
    "枚方市": ["https://www.city.hirakata.osaka.jp/0000008211.html"],
    "東大阪市": ["https://www.city.higashiosaka.lg.jp/category/19-16-0-0-0-0-0-0-0-0.html"],
    "草津市": ["https://www.city.kusatsu.shiga.jp/kurashi/sangyobusiness/nyusatsu/proposal/boshuu/index.html"],
    "彦根市": ["https://www.city.hikone.lg.jp/jigyosha/chodo_nyusatsu/6/2/index.html"],
    "橿原市": ["https://www.city.kashihara.nara.jp/soshiki/1019/gyomu/1/1/2/2899.html"],
    "生駒市": ["https://www.city.ikoma.lg.jp/0000002375.html"],
    "倉敷市": ["https://www.city.kurashiki.okayama.jp/business/contract/1013065/1014315/1014415/index.html", "https://www.city.kurashiki.okayama.jp/business/contract/1013065/1014309/index.html", "https://www.city.kurashiki.okayama.jp/business/contract/1013065/1014314/index.html"],
    "福山市": ["https://www.city.fukuyama.hiroshima.jp/soshiki/list5-2.html"],
    "尾道市": ["https://www.city.onomichi.hiroshima.jp/life/2/35/190/"],
    "東広島市": ["https://www.city.higashihiroshima.lg.jp/sangyo/nyusatsu/1/index.html"],
    "下関市": ["https://www.city.shimonoseki.lg.jp/site/nyuusatu/list98-509.html"],
    "宇部市": ["https://www.city.ube.yamaguchi.jp/boshu/boshuu_shigoto/boshu_nyuusatsu/index.html"],
    "丸亀市": ["https://www.city.marugame.lg.jp/life/5/24/115/"],
    "西条市": ["https://www.city.saijo.ehime.jp/soshiki/list7-1.html"],
    "宇和島市": ["https://www.city.uwajima.ehime.jp/life/6/34/125/"],
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
    "小樽市": ["https://www.city.otaru.lg.jp/categories/bunya/nyusatu_keiyaku/nyusatu_koujiigai/bosyu/"],
    "室蘭市": ["https://www.city.muroran.lg.jp/administration/?category=75"],
    "釧路市": ["https://www.city.kushiro.lg.jp/sangyou/nyuusatsu/1006670/1008393/index.html"],
    "帯広市": ["https://www.city.obihiro.hokkaido.jp/sangyo/keiyaku/proposal/index.html"],
    "網走市": ["https://www.city.abashiri.hokkaido.jp/life/3/index-2.html"],
    "稚内市": ["https://www.city.wakkanai.hokkaido.jp/lifeevent/jigyousya.html"],
    "石狩市": ["https://www.city.ishikari.hokkaido.jp/sangyo/keiyaku/index.html"],
    "根室市": ["https://www.city.nemuro.hokkaido.jp/13/1384.html"],
    "富良野市": ["https://www.city.furano.hokkaido.jp/life/sangyoshigoto/nyusatsukeiyaku/"],
    "紋別市": ["https://mombetsu.jp/news/?category=51"],
    "弘前市": ["http://city.hirosaki.aomori.jp/jouhou/keiyaku/other/index.html"],
    "黒石市": ["http://www.city.kuroishi.aomori.jp/shisei/nyusatsu/index.html"],
    "三沢市": ["https://www.city.misawa.lg.jp/index.cfm/10,0,37,678,html"],
    "むつ市": ["https://www.city.mutsu.lg.jp/work/bid/proposal/"],
    "平川市": ["https://www.city.hirakawa.lg.jp/shigoto/keiyaku/proposal/"],
    "盛岡市": ["https://www.city.morioka.iwate.jp/jigyousha/"],
    "大船渡市": ["https://www.city.ofunato.iwate.jp/genre/category/business/nyusatsu/proposal"],
    "北上市": ["https://www.city.kitakami.iwate.jp/life/shisei/nyusatsu_keiyaku/proposal/index.html"],
    "八幡平市": ["https://www.city.hachimantai.lg.jp/life/2/25/129/"],
    "陸前高田市": ["https://www.city.rikuzentakata.iwate.jp/soshiki/zaiseika/zaiseikakari/2/1/r8_nyuusatsu/9371.html"],
    "奥州市": ["https://www.city.oshu.iwate.jp/shigoto_sangyo/nyusatsu_keiyaku/5/index.html"],
    "花巻市": ["https://www.city.hanamaki.iwate.jp/search/site.html?cx=017381559455419021349%3Agtowm4nsosw&ie=UTF-8&q=%E3%83%97%E3%83%AD%E3%83%9D%E3%83%BC%E3%82%B6%E3%83%AB&x=28&y=19&siteurl=www.city.hanamaki.iwate.jp%2Fbusiness%2Fnyusatsu_keiyaku%2Findex.html&ref=www.city.hanamaki.iwate.jp%2Fshisetsu%2F1023618.html&ss=0j0j1"],
    "遠野市": ["https://www.city.tono.iwate.jp/index.cfm/44,html?cx=011994033889960828962%3A-estwl_9xuy&ie=UTF-8&q=%E3%83%97%E3%83%AD%E3%83%9D%E3%83%BC%E3%82%B6%E3%83%AB&sa.x=68&sa.y=8"],
    "二戸市": ["https://www.city.ninohe.lg.jp/Info/2172"],
    "気仙沼市": ["https://www.kesennuma.miyagi.jp/li/business/020/030/index.html", "https://www.kesennuma.miyagi.jp/li/business/020/010/index.html"],
    "名取市": ["https://www.city.natori.miyagi.jp/life/5/23/99/"],
    "多賀城市": ["https://www.city.tagajo.miyagi.jp/koho/shise/shigoto/proposal/index.html"],
    "登米市": ["https://www.city.tome.miyagi.jp/shisejoho/nyusatsukeyaku/koubogataproposalindex.html"],
    "東松島市": ["https://www.city.higashimatsushima.miyagi.jp/jigyosya/keiyaku-nyusatsu/jigyosyabosyu/index.html"],
    "富谷市": ["https://www.tomiya-city.miyagi.jp/information/sangyou/nyusatsu/"],
    "能代市": ["https://www.city.noshiro.lg.jp/city/nyusatsu/kokoku-kobo/7-proposal/"],
    "横手市": ["https://www.city.yokote.lg.jp/shigoto/1001164/1001363/1005293/index.html"],
    "由利本荘市": ["https://www.city.yurihonjo.lg.jp/1001504/1002133/1002145/1002153/index.html"],
    "大仙市": ["https://www.city.daisen.lg.jp/genre/business/nyusatsu/nyusatsu-latest"],
    "にかほ市": ["https://www.city.nikaho.akita.jp/gyosei/shigoto_sangyo/nyusatsu_keiyaku/proposal/index.html"],
    "羽後町": ["https://www.town.ugo.lg.jp/business/index.html?category_id=38"],
    "仙北市": ["https://www.city.semboku.akita.jp/news_topics/whatsnew_list.php"],
    "北秋田市": ["https://www.city.kitaakita.akita.jp/genre/sangyou/updated-list"],
    "米沢市": ["https://www.city.yonezawa.yamagata.jp/category/shigoto_sangyo/1/1/index.html"],
    "酒田市": ["https://www.city.sakata.lg.jp/shisei/nyusatsu/nyuusatukoukoku.html#cmsFB78F"],
    "新庄市": ["https://www.city.shinjo.yamagata.jp/g/kigyo/010/030/index.html"],
    "寒河江市": ["https://www.city.sagae.yamagata.jp/jigyou/nyusatsu/koukoku/index.html"],
    "天童市": ["https://www.city.tendo.yamagata.jp/busiindust/nyusatsu/"],
    "須賀川市": ["https://www.city.sukagawa.fukushima.jp/jigyosya/nyusatsu/1010736/index.html"],
    "喜多方市": ["https://www.city.kitakata.fukushima.jp/life/2/12/164/"],
    "相馬市": ["https://www.city.soma.fukushima.jp/shigoto_sangyo/nyusatsu_keiyaku/index.html"],
    "田村市": ["https://www.city.tamura.lg.jp/life/4/34/158/"],
    "南相馬市": ["https://www.city.minamisoma.lg.jp/portal/business/nyusatsu_keiyaku/3/1/index.html"],
    "土浦市": ["https://www.city.tsuchiura.lg.jp/shigoto-sangyo/nyusatsu-keiyaku/proposal-no-jisshi/"],
    "古河市": ["https://www.city.ibaraki-koga.lg.jp/boshu_list.html"],
    "石岡市": ["https://www.city.ishioka.lg.jp/shigoto_sangyo_machi/hacchu/proposal/"],
    "龍ケ崎市": ["https://www.city.ryugasaki.ibaraki.jp/jigyosha/nyusatsu/index.html"],
    "常総市": ["https://www.city.joso.lg.jp/kurashi_gyousei/jigyousha/nyusatsu_keiyaku/koubo/"],
    "常陸太田市": ["https://www.city.hitachiota.ibaraki.jp/page/dir009852.html"],
    "北茨城市": ["https://www.city.kitaibaraki.lg.jp/category/bunya/jigyo/more@docs-shinchaku.html"],
    "牛久市": ["https://www.city.ushiku.lg.jp/search.php?cx=012768706773039010864%3Avxw-xs2qiry&ie=UTF-8&q=%E3%83%97%E3%83%AD%E3%83%9D%E3%83%BC%E3%82%B6%E3%83%AB&sa=%E6%A4%9C%E7%B4%A2#gsc.tab=0&gsc.q=%E3%83%97%E3%83%AD%E3%83%9D%E3%83%BC%E3%82%B6%E3%83%AB&gsc.sort=date"],
    "ひたちなか市": ["https://www.city.hitachinaka.lg.jp/business/nyusatsu/1007211/index.html"],
    "鹿嶋市": ["https://www.city.kashima.ibaraki.jp/life/11/index-2.html"],
    "潮来市": ["https://www.city.itako.lg.jp/page/dir008509.html"],
    "守谷市": ["https://www.city.moriya.ibaraki.jp/sangyo_business/nyusatsu/1004161/index.html"],
    "筑西市": ["https://www.city.chikusei.lg.jp/jigyousha/proposal/proposal-project/"],
    "坂東市": ["https://www.city.bando.lg.jp/page/dir007235.html"],
    "かすみがうら市": ["https://www.city.kasumigaura.lg.jp/sp/page/dir011173.html"],
    "神栖市": ["https://www.city.kamisu.ibaraki.jp/business/bid/1002595/index.html"],
    "鉾田市": ["https://www.city.hokota.lg.jp/page/dir004645.html"],
    "つくばみらい市": ["https://www.city.tsukubamirai.lg.jp/business/bid/proposal/"],
    "足利市": ["https://www.city.ashikaga.tochigi.jp/industory/000060/000323/000738/index.html"],
    "栃木市": ["https://www.pref.tochigi.lg.jp/kensei/nyuusatsu/koubo-itaku/index.html"],
    "佐野市": ["https://www.city.sano.lg.jp/kurashi_gyosei/shiseijoho_nyusatsu/nyusatsu_keiyakujoho/index.html"],
    "日光市": ["https://www.city.nikko.lg.jp/shigoto_sangyo/nyusatsu_keiyaku/2/index.html"],
    "小山市": ["https://www.city.oyama.tochigi.jp/sangyou-sigoto/nyuusatsu-keiyaku/etc/"],
    "真岡市": ["https://www.city.moka.lg.jp/shigoto_sangyo/nyusatsu/6/index.html"],
    "大田原市": ["https://www.city.ohtawara.tochigi.jp/tag/%E3%83%97%E3%83%AD%E3%83%9D%E3%83%BC%E3%82%B6%E3%83%AB/"],
    "矢板市": ["https://www.city.yaita.tochigi.jp/life/10/13/97/"],
    "那須塩原市": ["https://www.city.nasushiobara.tochigi.jp/jigyoshamuke/1/index.html"],
    "さくら市": ["https://www.city.tochigi-sakura.lg.jp/business/000045/000263/index.html#genreContentsList"],
    "那須烏山市": ["https://www.city.nasukarasuyama.lg.jp/page/dir003823.html"],
    "下野市": ["https://www.city.shimotsuke.lg.jp/0409/genre2-3-001.html"],
    "桐生市": ["https://www.city.kiryu.lg.jp/sangyou/nyusatsu/koubo/index.html"],
    "伊勢崎市": ["https://www.city.isesaki.lg.jp/sangyo_nyusatsu_kaihatsu/nyusatsu_keiyaku/proposal/index.html"],
    "沼田市": ["https://www.city.numata.gunma.jp/jigyosha/nyusatsu/1012747/index.html"],
    "富岡市": ["https://www.city.tomioka.lg.jp/www/genre/1001050000103/index.html"],
    "安中市": ["https://www.city.annaka.lg.jp/life/4/26/179/"],
    "みどり市": ["https://www.city.midori.gunma.jp/sangyou/1001649/1001806/index.html"],
    "狭山市": ["https://www.city.sayama.saitama.jp/jigyo/koubo/sonota/index.html"],
    "羽生市": ["https://www.city.hanyu.lg.jp/categories/bunya/jigyosha/nyusatsu/more@docs-shinchaku.html"],
    "深谷市": ["https://www.city.fukaya.saitama.jp/business/nyusatsukeiyaku/hachu/index.html"],
    "上尾市": ["https://www.city.ageo.lg.jp/life/3/19/104/"],
    "草加市": ["https://www.city.soka.saitama.jp/li/050/070/030/050/index.html"],
    "蕨市": ["https://www.city.warabi.saitama.jp/shisei/shigoto/nyusatsu/1011148/index.html"],
    "朝霞市": ["https://www.city.asaka.lg.jp/life/2/54/297/"],
    "志木市": ["https://www.city.shiki.lg.jp/life/2/24/121/index-2.html"],
    "和光市": ["https://www.city.wako.lg.jp/result/search.html?cx=016656837258886753236%3Ah6ikgp0hk-u&ie=UTF-8&q=%E3%83%97%E3%83%AD%E3%83%9D%E3%83%BC%E3%82%B6%E3%83%AB"],
    "桶川市": ["https://www.city.okegawa.lg.jp/jigyosha/nyusatsu/koubo/index.html"],
    "久喜市": ["https://www.city.kuki.lg.jp/shisei/jigyo/nyusatsu_keiyaku/1002295/index.html"],
    "北本市": ["https://www.city.kitamoto.lg.jp/jigyosha/nyusatsu/proposal/index.html"],
    "富士見市": ["https://www.city.fujimi.saitama.jp/60jigyo/17nyuusatsu/proposal/index.html"],
    "蓮田市": ["https://www.city.hasuda.saitama.jp/search/result.html?q=%E3%83%97%E3%83%AD%E3%83%9D%E3%83%BC%E3%82%B6%E3%83%AB&sa=%E6%A4%9C%E7%B4%A2&cx=016322574973829382585%3Avczv66smyas&ie=UTF-8&cof=FORID%3A9"],
    "ふじみ野市": ["https://www.city.fujimino.saitama.jp/jigyoshanohohe/nyusatsukanrenjoho/hattyujoho/kobogataproposaljoho/index.html"],
    "本庄市": ["https://www.city.honjo.lg.jp/shigoto_sangyo/nyusatsu_keiyaku/kobogatapuropozaru/index.html"],
    "加須市": ["https://www.city.kazo.lg.jp/shigoto_sangyo/nyusatsu_keiyaku/proposal/index.html"],
    "東松山市": ["https://www.city.higashimatsuyama.lg.jp/life/2/24/132/"],
    "春日部市": ["https://www.city.kasukabe.lg.jp/jigyoshamuke/nyusatsu_keiyaku/nyusatsukokokuichiran/index.html"],
    "坂戸市": ["https://www.city.sakado.lg.jp/life/2/index-2.html"],
    "吉川市": ["https://www.city.yoshikawa.saitama.jp/index.cfm/27,0,185,html"],
    "八潮市": ["https://www.city.yashio.lg.jp/jigyosha/nyusatsu_keiyaku/hatchujoho/index.html"],
    "館山市": ["https://www.city.tateyama.chiba.jp/kankei/page100033.html"],
    "木更津市": ["https://www.city.kisarazu.lg.jp/shigoto_sangyo/nyusatsu_keiyaku_proposal/boshuchu/index.html"],
    "習志野市": ["https://www.city.narashino.lg.jp/jigyosha/proposal/annai/index.html"],
    "勝浦市": ["https://www.city.katsuura.lg.jp/life/5/20/82/"],
    "流山市": ["https://www.city.nagareyama.chiba.jp/business/1005422/1035560/index.html"],
    "我孫子市": ["https://www.city.abiko.chiba.jp/jigyousha/nyusatsukeiyaku/r7_nyusatsujoho/proposal_r7.html"],
    "鎌ケ谷市": ["https://www.city.kamagaya.chiba.jp/smph/jigyosha/nyuusatu_menu/proposal/poropo_boshu/index.html"],
    "浦安市": ["https://www.city.urayasu.lg.jp/shisei/jigyosha/proposal/index.html"],
    "富津市": ["https://www.city.futtsu.lg.jp/category/3-1-8-0-0-0-0-0-0-0.html"],
    "佐倉市": ["https://www.city.sakura.lg.jp/global/shigoto_sangyo/gyousyabosyu/proposal_1/index.html"],
    "四街道市": ["https://www.city.yotsukaido.chiba.jp/smph/shisei/jigyosyahamuke/bosyu/index.html"],
    "野田市": ["https://www.city.noda.chiba.jp/jigyousha/nyusatsu/joho/index.html"],
    "茂原市": ["https://www.city.mobara.chiba.jp/category/5-1-1-0-0-0-0-0-0-0.html"],
    "鴨川市": ["https://www.city.kamogawa.lg.jp/life/9/32/"],
    "君津市": ["https://www.city.kimitsu.lg.jp/life/4/17/306/"],
    "市原市": ["https://www.city.ichihara.chiba.jp/2ndCategoryIndex?categoryId=40103000"],
    "八千代市": ["https://www.city.yachiyo.lg.jp/life/2/23/114"],
    "香取市": ["https://www.city.katori.lg.jp/government/keiyaku/proposal/index.html"],
    "いすみ市": ["https://www.city.isumi.lg.jp/gyosei/shigoto_sangyo/nyusatsu_keiyakujoho/proposal/index.html"],
    "富里市": ["https://www.city.tomisato.lg.jp/category/3-1-6-0-0-0-0-0-0-0.html"],
    "大網白里市": ["https://www.city.oamishirasato.lg.jp/category/63-17-2-0-0-0-0-0-0-0.html"],
    "南房総市": ["https://www.city.minamiboso.chiba.jp/category/12-1-1-0-0-0-0-0-0-0.html"],
    "印西市": ["https://www.city.inzai.lg.jp/category/2-16-1-0-0.html"],
    "白井市": ["https://www.city.shiroi.chiba.jp/sangyo/nyusatsu/n05/index.html"],
    "府中市": ["https://www.city.fuchu.tokyo.jp/jigyosha/keyaku/proposal/proposal_boshu/index.html"],
    "小金井市": ["https://www.city.koganei.lg.jp/smph/shisei/jigyoshamuke/info/index.html"],
    "日野市": ["https://www.city.hino.lg.jp/shisei/nyusatsu/proposal/index.html"],
    "東村山市": ["https://www.city.higashimurayama.tokyo.jp/kurashi/jigyo/bosyu/proposal/index.html"],
    "国分寺市": ["https://www.city.kokubunji.tokyo.jp/nyusatsu/1034929/index.html"],
    "国立市": ["https://www.city.kunitachi.tokyo.jp/machi/nyusatsu/1/1/index.html"],
    "東大和市": ["https://www.city.higashiyamato.lg.jp/business/nyusatsu/1004014/index.html"],
    "清瀬市": ["https://www.city.kiyose.lg.jp/sigotosangyou/keiyakunyuusatu/1007732/index.html"],
    "東久留米市": ["https://www.city.higashikurume.lg.jp/shisei/jigyosha/1007219/index.html"],
    "武蔵村山市": ["https://www.city.musashimurayama.lg.jp/shisei/boshu/shiteikanri/index.html"],
    "西東京市": ["https://www.city.nishitokyo.lg.jp/siseizyoho/jigyo/index.html"],
    "逗子市": ["https://www.city.zushi.kanagawa.jp/jigyosha/nyusatsu/1004803/index.html"],
    "秦野市": ["https://www.city.hadano.kanagawa.jp/shigoto-sangyo-machizukuri/nyusatsu-keiyaku/2/index.html"],
    "大和市": ["https://www.city.yamato.lg.jp/gyosei/shigoto_sangyo_machizukuri/nyusatsu_keiyaku/proposal/index.html"],
    "伊勢原市": ["https://www.city.isehara.kanagawa.jp/categories/bunya/sangyo_machidukuri/nyusatsu/proposal_conduct/"],
    "海老名市": ["https://www.city.ebina.kanagawa.jp/shisei/nyusatsu/proposal/index.html"],
    "座間市": ["https://www.city.zama.kanagawa.jp/sangyo/keiyaku/proposal/index.html"],
    "柏崎市": ["https://www.city.kashiwazaki.lg.jp/sangyo_business/nyusatsu_keiyaku/proposal/index.html"],
    "新発田市": ["https://www.city.shibata.lg.jp/jigyosha/nyusatsu/1006477/index.html"],
    "加茂市": ["https://www.city.kamo.niigata.jp/shigoto/nyusatsu/proposal/"],
    "十日町市": ["https://www.city.tokamachi.lg.jp/shigoto_sangyo/nyusatsu_koji/proposal/index.html"],
    "佐渡市": ["https://www.city.sado.niigata.jp/site/proposal/list76-189.html"],
    "妙高市": ["https://www.city.myoko.niigata.jp/city-info/apply/proposal/"],
    "南魚沼市": ["https://www.city.minamiuonuma.niigata.jp/business/nyusatsu/nyusatsukoukoku/"],
    "高岡市": ["https://www.city.takaoka.toyama.jp/gyosei/sangyo_business/nyusatsu_keiyaku/1/index.html"],
    "立山町": ["https://www.town.tateyama.toyama.jp/shigoto_sangyo/nyusatsu_keiyaku/1/index.html"],
    "小松市": ["https://www.city.komatsu.lg.jp/soshiki/1011/proposal_info/index.html"],
    "北杜市": ["https://www.city.hokuto.yamanashi.jp/life/biz/bosyu/"],
    "中央市": ["https://www.city.chuo.yamanashi.jp/machi/keizai/nyusatsukankei/nyusatsujouhou/13287.html"],
    "上田市": ["https://www.city.ueda.nagano.jp/life/4/32/265/"],
    "須坂市": ["https://www.city.suzaka.nagano.jp/gyosei/zaisei_gyosei/8/3/index.html"],
    "安曇野市": ["https://www.city.azumino.nagano.jp/site/nyu-kei/list303-1108.html"],
    "土岐市": ["https://www.city.toki.lg.jp/sangyo/nyusatsu/1004883/index.html"],
    "本巣市": ["https://www.city.motosu.lg.jp/category/3-1-3-0-0-0-0-0-0-0.html"],
    "郡上市": ["https://www.city.gujo.gifu.jp/business/puroposal/"],
    "美濃市": ["https://www.city.mino.gifu.jp/kurashi/kobo-boshu-kokuchi/"],
    "各務原市": ["https://www.city.kakamigahara.lg.jp/business/keiyaku/1009970/index.html"],
    "海津市": ["https://www.city.kaizu.lg.jp/shisei/category/2-1-4-0-0-0-0-0-0-0.html"],
    "三島市": ["https://www.city.mishima.shizuoka.jp/web_subcontentlist060609.html"],
    "富士宮市": ["https://www.city.fujinomiya.lg.jp/sangyo/joho/nyusatsu/proposal/index.html"],
    "磐田市": ["https://www.city.iwata.shizuoka.jp/sangyou_business/nyuusatsu_keiyaku/1006361/index.html"],
    "焼津市": ["https://www.city.yaizu.lg.jp/business/bid-contract/info/proposal/index.html"],
    "掛川市": ["https://www.city.kakegawa.shizuoka.jp/gyosei/shinchaku/boshu/"],
    "藤枝市": ["https://www.city.fujieda.shizuoka.jp/sangyo/proposal/index.html"],
    "袋井市": ["https://www.city.fukuroi.shizuoka.jp/soshiki/kodomoseisaku/kikakukakari/puropo-zaru/index.html"],
    "下田市": ["https://www.city.shimoda.shizuoka.jp/contents/newinfo/index.html"],
    "伊豆市": ["https://www.city.izu.shizuoka.jp/boshu_list.html"],
    "牧之原市": ["https://www.city.makinohara.shizuoka.jp/soshiki/list8-1.html"],
    "碧南市": ["https://www.city.hekinan.lg.jp/soshiki/soumu/gyosei/1_3/18937.html"],
    "常滑市": ["https://www.city.tokoname.aichi.jp/jigyosha/proposal/index.html"],
    "小牧市": ["http://www.city.komaki.aichi.jp/admin/jigyousha/koukoku/1/jigyoushaboshuu/index.html"],
    "大府市": ["https://www.city.obu.aichi.jp/jigyo/news_jigyo/index.html"],
    "知立市": ["https://www.city.chiryu.aichi.jp/jigyosha/nyusatsu/puropo/index.html"],
    "尾張旭市": ["https://www.city.owariasahi.lg.jp/site/nyusatsu-keiyaku/10706.html"],
    "清須市": ["https://www.city.kiyosu.aichi.jp/jigyosha_joho/nyusatsu_joho/proposal/index.html"],
    "蒲郡市": ["https://www.city.gamagori.lg.jp/life/2/74/230/"],
    "犬山市": ["https://www.city.inuyama.aichi.jp/jigyo/proposal/index.html"],
    "江南市": ["https://www.city.konan.lg.jp/jigyou/proposal/index.html"],
    "瀬戸市": ["https://www.city.seto.aichi.jp/bunya/proposal-info.html"],
    "半田市": ["https://www.city.handa.lg.jp/jigyosha/nyusatsu/1003688/index.html"],
    "あま市": ["https://www.city.ama.aichi.jp/bussiness/nyusatsu/1006732/index.html"],
    "長久手市": ["https://www.city.nagakute.lg.jp/shigoto_sangyo/nyusatsu_keiyaku/puropo/index.html"],
    "松阪市": ["https://www.city.matsusaka.mie.jp/site/buppin05/propo.html"],
    "鳥羽市": ["https://www.city.toba.mie.jp/shigoto_sangyo/nyusatsu_keiyaku/proposal/index.html"],
    "志摩市": ["https://www.city.shima.mie.jp/jigyoshamuke/nyusatsu/4554.html"],
    "守山市": ["https://www.city.moriyama.lg.jp/sangyo_business/nyusatsukeiyuaku/1011216/index.html"],
    "甲賀市": ["https://www.city.koka.lg.jp/dd.aspx?moduleid=1099&_PickUp_para=15"],
    "野洲市": ["https://www.city.yasu.lg.jp/shigoto-sangyo/nyusatsu-keiyaku/proposal/index.html"],
    "湖南市": ["https://www.city.shiga-konan.lg.jp/shigoto/nyusatsu_keiyaku/puropozaru/index.html"],
    "米原市": ["https://www.city.maibara.lg.jp/sangyo/nyusatu/koubogata/index.html"],
    "福知山市": ["https://www.city.fukuchiyama.lg.jp/site/nyusatsukeiyaku/list64-181.html"],
    "舞鶴市": ["https://www.city.maizuru.kyoto.jp/shigoto/category/5-10-9-0-0-0-0-0-0-0.html"],
    "綾部市": ["https://www.city.ayabe.lg.jp/category/6-5-10-0-0-0-0-0-0-0.html"],
    "亀岡市": ["https://www.city.kameoka.kyoto.jp/life/6/32/253/"],
    "長岡京市": ["https://www.city.nagaokakyo.lg.jp/category/3-1-0-0-0-0-0-0-0-0.html"],
    "京田辺市": ["https://www.city.kyotanabe.lg.jp/category/4-1-9-0-0-0-0-0-0-0.html"],
    "京丹後市": ["https://www.city.kyotango.lg.jp/top/soshiki/somu/nyusatsu/1/proposal/index.html"],
    "与謝野町": ["https://www.town.yosano.lg.jp/work/bid/proposal/"],
    "大東市": ["https://www.city.daito.lg.jp/life/6/31/188/"],
    "四條畷市": ["https://www.city.shijonawate.lg.jp/life/8/50/236/"],
    "豊能町": ["https://www.town.toyono.osaka.jp/business/nyuusatsu-keiyaku/proposal/"],
    "八尾市": ["https://www.city.yao.osaka.jp/sangyou_business/nyusatsu_keiyaku/1012821/index.html"],
    "富田林市": ["https://www.city.tondabayashi.lg.jp/life/4/21/86/"],
    "岸和田市": ["https://www.city.kishiwada.lg.jp/life/4/23/102/"],
    "泉南市": ["https://www.city.sennan.lg.jp/business/nyusatu/koubo/index.html"],
    "和泉市": ["https://www.city.osaka-izumi.lg.jp/bizisan/nyusatsu/index.html"],
    "洲本市": ["https://www.city.sumoto.lg.jp/life/2/14/51/"],
    "伊丹市": ["http://www.city.itami.lg.jp/business_sangyo/5/puropo/index.html"],
    "西脇市": ["https://www.city.nishiwaki.lg.jp/jigyousyamuke/nyusatsukeiyaku/koubogatapuropo/index.html"],
    "川西市": ["https://www.city.kawanishi.hyogo.jp/business/nyusatsu/1004244/1004245/index.html"],
    "三田市": ["https://www.city.sanda.lg.jp/shigoto_sangyo/nyusatsu_keiyaku/proposal/index.html"],
    "御所市": ["https://www.city.gose.nara.jp/category/6-9-8-0-0-0-0-0-0-0.html"],
    "葛城市": ["https://www.city.katsuragi.nara.jp/shigoto_sangyo/teianboshu/index.html"],
    "米子市": ["https://www.city.yonago.lg.jp/dd.aspx?moduleid=4142&_PickUp_para=1"],
    "出雲市": ["https://www.city.izumo.shimane.jp/www/genre/1752214796728/index.html"],
    "益田市": ["https://www.city.masuda.lg.jp/shigoto_sangyo/nyusatsu_keiyaku/kobogataproposal/index.html"],
    "観音寺市": ["https://www.city.kanonji.kagawa.jp/life/13/87/290/"],
    "宿毛市": ["https://www.city.sukumo.kochi.jp/05/03/"],
    "周南市": ["https://www.city.shunan.lg.jp/life/6/28/135/"],
    "小松島市": ["https://www.city.komatsushima.lg.jp/sangyo/nyusatsu/information/"],
    "玉野市": ["https://www.city.tamano.lg.jp/life/2/15/60/"],
    "筑後市": ["https://www.city.chikugo.lg.jp/shigoto/_3716/_31017/"],
    "宗像市": ["https://www.city.munakata.lg.jp/list00313.html"],
    "福津市": ["https://www.city.fukutsu.lg.jp/sangyou/nyusatsu/proposal/index.html"],
    "春日市": ["https://www.city.kasuga.fukuoka.jp/shisei/nyuusatsu/nyuusatsu/1003940/index.html"],
    "唐津市": ["https://www.city.karatsu.lg.jp/life/7/45/index-2.html"],
    "鳥栖市": ["https://www.city.tosu.lg.jp/life/5/23/96/"],
    "嬉野市": ["https://www.city.ureshino.lg.jp/news_nyusatsu.html"],
    "大村市": ["https://www.city.omura.nagasaki.jp/shise/nyusatsu/koubo/index.html"],
    "対馬市": ["https://www.city.tsushima.nagasaki.jp/boshu_list.html"],
    "五島市": ["https://www.city.goto.nagasaki.jp/bosyu.html"],
    "玉名市": ["https://www.city.tamana.lg.jp/q/list/127.html"],
    "合志市": ["https://www.city.koshi.lg.jp/list00368.html"],
    "荒尾市": ["https://www.city.arao.lg.jp/shisei/nyusatsu/kobo-proposal/"],
    "佐伯市": ["https://www.city.saiki.oita.jp/list00367.html"],
    "うるま市": ["https://www.city.uruma.lg.jp/1001005000/contents/proposal.html"],
    "浦添市": ["https://www.city.urasoe.lg.jp/category/bunya/nyusatsu/kobo/more@docs_1.html"],
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
