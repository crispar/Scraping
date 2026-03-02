"""
Tom's Hardware Parser
Parses articles from Tom's Hardware (tomshardware.com)
"""

import logging
from typing import Dict, Any
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter


class TomsHardwareParser(BaseParser):
    """Parser for Tom's Hardware articles"""

    def __init__(self, max_workers=None, delay=None, log_level=logging.INFO, format_preset=None):
        super().__init__(max_workers=max_workers or 1, log_level=log_level)
        self.delay = delay or 1.0
        self.rate_limiter = SimpleRateLimiter(delay=self.delay)
        self.logger.info(f"TomsHardwareParser initialized")

    def _get_logger_name(self) -> str:
        return "tomshardware_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single Tom's Hardware article"""
        self.logger.info(f"Parsing Tom's Hardware article: {url}")
        self.rate_limiter.wait()

        custom_selectors = [
            ('div', {'id': 'article-body'}),
            ('div', {'class': 'text-copy'}),
        ]

        return self.parse_with_extractor(
            url=url,
            parser_name='tomshardware',
            default_author="Tom's Hardware",
            custom_content_selectors=custom_selectors
        )
