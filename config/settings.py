"""システム設定"""

import os

# スプレッドシート設定
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID', '')
CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')

# スクレイピング設定
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1
MAX_RETRIES = 3
USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# ログ設定
LOG_LEVEL = 'INFO'
LOG_FILE = 'logs/scraping.log'

# 検索エンジン設定
SEARCH_ENGINE = 'duckduckgo'
```
