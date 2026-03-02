"""
Strategies 모듈

Strategy 패턴을 사용한 출력 전략들을 제공합니다.
"""

from crawler.strategies.output_strategy import (
    OutputStrategy,
    CSVOutputStrategy,
    JSONOutputStrategy,
    TextOutputStrategy,
    RedditTextOutputStrategy,
    RedditSimpleTextOutputStrategy,
    NaverBlogTextOutputStrategy,
    OutputStrategyFactory
)

__all__ = [
    'OutputStrategy',
    'CSVOutputStrategy',
    'JSONOutputStrategy',
    'TextOutputStrategy',
    'RedditTextOutputStrategy',
    'RedditSimpleTextOutputStrategy',
    'NaverBlogTextOutputStrategy',
    'OutputStrategyFactory',
]
