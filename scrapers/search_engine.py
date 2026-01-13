"""検索エンジン（DuckDuckGo）"""

import time
import logging
from typing import List, Dict
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)


def search_prefecture_projects(domain: str, keywords: List[str], max_results: int = 20) -> List[Dict]:
    """
    都道府県ドメイン内で案件を検索
    """
    all_results = []
    seen_urls = set()
    
    for keyword in keywords:
        query = f'site:{domain} {keyword} (入札 OR 公募 OR 調達 OR 募集)'
        logger.info(f"検索クエリ: {query}")
        
        try:
            with DDGS() as ddgs:
                search_results = ddgs.text(
                    query,
                    max_results=max_results,
                    region='jp-jp',
                )
                
                for result in search_results:
                    url = result.get('href', '')
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append({
                            'title': result.get('title', ''),
                            'url': url,
                            'snippet': result.get('body', '')
                        })
        except Exception as e:
            logger.error(f"検索エラー: {e}")
        
        time.sleep(1)
    
    logger.info(f"{domain}: 合計{len(all_results)}件取得")
    return all_results
```
