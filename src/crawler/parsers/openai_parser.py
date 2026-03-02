"""
OpenAI Parser
Parses articles from openai.com
"""

import logging
from typing import Dict, Any
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter


class OpenAIParser(BaseParser):
    """Parser for OpenAI blog articles"""

    DEFAULT_HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://openai.com/',
    }

    def __init__(self, max_workers=None, delay=None, log_level=logging.INFO, format_preset=None):
        super().__init__(max_workers=max_workers or 1, log_level=log_level)
        self.delay = delay or 1.0
        self.rate_limiter = SimpleRateLimiter(delay=self.delay)
        self.logger.info(f"OpenAIParser initialized")

    def _get_logger_name(self) -> str:
        return "openai_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single OpenAI blog article"""
        self.logger.info(f"Parsing OpenAI article: {url}")
        self.rate_limiter.wait()

        # OpenAI uses article and main tags for content
        custom_selectors = [
            ('article', {}),
            ('main', {}),
        ]

        return self.parse_with_extractor(
            url=url,
            parser_name='openai',
            default_author="OpenAI",
            custom_content_selectors=custom_selectors,
            headers=self.DEFAULT_HEADERS
        )
