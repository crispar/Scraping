"""
Engadget Parser
Parses articles from Engadget (engadget.com)
"""

import logging
from typing import Dict, Any
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter


class EngadgetParser(BaseParser):
    """Parser for Engadget articles"""

    def __init__(self, max_workers=None, delay=None, log_level=logging.INFO, format_preset=None):
        super().__init__(max_workers=max_workers or 1, log_level=log_level)
        self.delay = delay or 1.0
        self.rate_limiter = SimpleRateLimiter(delay=self.delay)
        self.logger.info(f"EngadgetParser initialized")

    def _get_logger_name(self) -> str:
        return "engadget_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single Engadget article"""
        self.logger.info(f"Parsing Engadget article: {url}")
        self.rate_limiter.wait()

        custom_selectors = [
            ('div', {'class': 'article-content'}),
            ('div', {'class': 'caas-body'}),
        ]

        return self.parse_with_extractor(
            url=url,
            parser_name='engadget',
            default_author='Engadget',
            custom_content_selectors=custom_selectors
        )
