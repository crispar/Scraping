"""PC Gamer Parser

This module provides a parser for extracting articles from PC Gamer.
"""

import logging
from typing import Dict, Any
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter


class PCGamerParser(BaseParser):
    """Parser for PC Gamer articles"""

    def __init__(self, max_workers: int = None, delay: float = None,
                 log_level: int = logging.INFO, format_preset: str = None):
        super().__init__(max_workers=max_workers or 1, log_level=log_level)
        self.delay = delay or 2.0
        self.rate_limiter = SimpleRateLimiter(delay=self.delay)
        self.logger.info(f"PCGamerParser initialized")

    def _get_logger_name(self) -> str:
        return "pcgamer_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single PC Gamer article using ArticleParser utility

        Args:
            url: URL of the PC Gamer article

        Returns:
            Dict containing article data (title, author, date, content, etc.)
        """
        self.logger.info(f"Parsing PC Gamer article: {url}")
        self.rate_limiter.wait()

        # PC Gamer works well with ArticleParser's default settings
        custom_selectors = [
            ('div', {'id': 'article-body'}),
            ('div', {'class': 'article-body'}),
        ]

        return self.parse_with_extractor(
            url=url,
            parser_name='pcgamer',
            default_author='PC Gamer',
            custom_content_selectors=custom_selectors
        )
