"""
The Drive Parser
Parses articles from The Drive (thedrive.com)
"""

import logging
from typing import Dict, Any
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter


class TheDriveParser(BaseParser):
    """Parser for The Drive articles"""

    def __init__(self, max_workers=None, delay=None, log_level=logging.INFO, format_preset=None):
        super().__init__(max_workers=max_workers or 1, log_level=log_level)
        self.delay = delay or 1.0
        self.rate_limiter = SimpleRateLimiter(delay=self.delay)
        self.logger.info(f"TheDriveParser initialized")

    def _get_logger_name(self) -> str:
        return "thedrive_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single The Drive article"""
        self.logger.info(f"Parsing The Drive article: {url}")
        self.rate_limiter.wait()

        custom_selectors = [
            ('section', {'class': 'entry-content'}),
            ('div', {'class': 'article-body'}),
        ]

        return self.parse_with_extractor(
            url=url,
            parser_name='thedrive',
            default_author='The Drive',
            custom_content_selectors=custom_selectors
        )
