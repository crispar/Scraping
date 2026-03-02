"""
Crawler 패키지

웹 크롤링 및 파싱을 위한 통합 패키지입니다.
"""

__version__ = '2.0.0'
__author__ = 'Your Name'

# 주요 클래스들을 패키지 레벨에서 임포트 가능하게
from crawler.core.base_parser import BaseParser
from crawler.factory import ParserFactory

__all__ = [
    'BaseParser',
    'ParserFactory',
]
