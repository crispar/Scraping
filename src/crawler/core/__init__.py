"""
Core 모듈

추상화 레이어와 핵심 설정을 제공합니다.
"""

from crawler.core.base_parser import BaseParser
from crawler.core.config import (
    RedditConfig,
    NaverBlogConfig,
    LogConfig,
    FileConfig
)

__all__ = [
    'BaseParser',
    'RedditConfig',
    'NaverBlogConfig',
    'LogConfig',
    'FileConfig',
]
