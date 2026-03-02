"""
Wired Parser
Parses articles from Wired (wired.com)
"""

import logging
from typing import Dict, Any
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter


class WiredParser(BaseParser):
    """Parser for Wired articles"""

    def __init__(self, max_workers=None, delay=None, log_level=logging.INFO, format_preset=None):
        super().__init__(max_workers=max_workers or 1, log_level=log_level)
        self.delay = delay or 1.0
        self.rate_limiter = SimpleRateLimiter(delay=self.delay)
        self.logger.info(f"WiredParser initialized")

    def _get_logger_name(self) -> str:
        return "wired_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single Wired article"""
        self.logger.info(f"Parsing Wired article: {url}")
        self.rate_limiter.wait()

        custom_selectors = [
            ('div', {'class': 'article__body'}),
            ('div', {'class': 'body__inner-container'}),
        ]

        return self.parse_with_extractor(
            url=url,
            parser_name='wired',
            default_author='Wired',
            custom_content_selectors=custom_selectors
        )
