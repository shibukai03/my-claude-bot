"""ロギング設定"""

import logging
import os


def setup_logger():
    """ロガーをセットアップ"""
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # コンソール出力
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger
