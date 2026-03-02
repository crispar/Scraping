"""Business Insider Parser

This module provides a parser for extracting articles from Business Insider.
"""

import logging
from typing import Dict, Any
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter


class BusinessInsiderParser(BaseParser):
    """Parser for Business Insider articles"""

    def __init__(self, max_workers: int = None, delay: float = None,
                 log_level: int = logging.INFO, format_preset: str = None):
        super().__init__(max_workers=max_workers or 1, log_level=log_level)
        self.delay = delay or 2.0
        self.rate_limiter = SimpleRateLimiter(delay=self.delay)
        self.logger.info(f"BusinessInsiderParser initialized")

    def _get_logger_name(self) -> str:
        return "businessinsider_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single Business Insider article using ArticleParser utility

        Args:
            url: URL of the Business Insider article

        Returns:
            Dict containing article data (title, author, date, content, etc.)
        """
        self.logger.info(f"Parsing Business Insider article: {url}")
        self.rate_limiter.wait()

        # Business Insider works well with ArticleParser's default settings
        custom_selectors = [
            ('div', {'class': 'content-lock-content'}),
            ('div', {'class': 'post-content'}),
        ]

        return self.parse_with_extractor(
            url=url,
            parser_name='businessinsider',
            default_author='Business Insider',
            custom_content_selectors=custom_selectors
        )
