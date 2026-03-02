"""
The Hindu Parser
Parses articles from thehindu.com
"""

import logging
from typing import Dict, Any
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter


class TheHinduParser(BaseParser):
    """Parser for The Hindu news articles"""

    def __init__(self, max_workers=None, delay=None, log_level=logging.INFO, format_preset=None):
        super().__init__(max_workers=max_workers or 1, log_level=log_level)
        self.delay = delay or 1.0
        self.rate_limiter = SimpleRateLimiter(delay=self.delay)
        self.logger.info(f"TheHinduParser initialized")

    def _get_logger_name(self) -> str:
        return "thehindu_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single The Hindu article"""
        self.logger.info(f"Parsing The Hindu article: {url}")
        self.rate_limiter.wait()

        # The Hindu uses articlebodycontent class for main content
        custom_selectors = [
            ('div', {'class': 'articlebodycontent'}),
            ('article', {}),
        ]

        return self.parse_with_extractor(
            url=url,
            parser_name='thehindu',
            default_author="The Hindu",
            custom_content_selectors=custom_selectors
        )
