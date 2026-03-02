"""Give Up Internet Parser

This module provides a parser for extracting articles from Give Up Internet.
"""

import logging
from typing import Dict, Any
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter


class GiveUpInternetParser(BaseParser):
    """Parser for Give Up Internet articles"""

    def __init__(self, max_workers: int = None, delay: float = None,
                 log_level: int = logging.INFO, format_preset: str = None):
        super().__init__(max_workers=max_workers or 1, log_level=log_level)
        self.delay = delay or 2.0
        self.rate_limiter = SimpleRateLimiter(delay=self.delay)
        self.logger.info(f"GiveUpInternetParser initialized")

    def _get_logger_name(self) -> str:
        return "giveupinternet_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single Give Up Internet article using ArticleParser utility

        Args:
            url: URL of the Give Up Internet article

        Returns:
            Dict containing article data (title, author, date, content, etc.)
        """
        self.logger.info(f"Parsing Give Up Internet article: {url}")
        self.rate_limiter.wait()

        # Give Up Internet works well with ArticleParser's default settings
        custom_selectors = [
            ('div', {'class': 'entry-content'}),
            ('article', {}),
        ]

        return self.parse_with_extractor(
            url=url,
            parser_name='giveupinternet',
            default_author='Give Up Internet',
            custom_content_selectors=custom_selectors
        )
