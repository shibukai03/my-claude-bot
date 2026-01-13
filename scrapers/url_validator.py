"""URL検証・重複チェック"""

import logging
import hashlib
from typing import Set, List

logger = logging.getLogger(__name__)


class URLValidator:
    """URL検証クラス"""
    
    def __init__(self):
        self.processed_urls: Set[str] = set()
    
    def is_new_url(self, url: str) -> bool:
        """URLが新規かどうか判定"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return url_hash not in self.processed_urls
    
    def mark_as_processed(self, url: str):
        """URLを処理済みとしてマーク"""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        self.processed_urls.add(url_hash)
    
    def filter_new_urls(self, urls: List[str]) -> List[str]:
        """新規URLのみをフィルタリング"""
        new_urls = [url for url in urls if self.is_new_url(url)]
        logger.info(f"URL重複チェック: {len(urls)}件中{len(new_urls)}件が新規")
        return new_urls
```
