"""
404 Media Parser
Parses articles from 404 Media (404media.co)
"""

import logging
from typing import Dict, Any
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter


class FourZeroFourParser(BaseParser):
    """Parser for 404 Media articles"""

    def __init__(self, max_workers=None, delay=None, log_level=logging.INFO, format_preset=None):
        super().__init__(max_workers=max_workers or 1, log_level=log_level)
        self.delay = delay or 1.0
        self.rate_limiter = SimpleRateLimiter(delay=self.delay)
        self.logger.info(f"FourZeroFourParser initialized")

    def _get_logger_name(self) -> str:
        return "fourzerofour_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single 404 Media article"""
        self.logger.info(f"Parsing 404 Media article: {url}")
        self.rate_limiter.wait()

        return self.parse_with_extractor(
            url=url,
            parser_name='404media',
            default_author='404 Media'
        )
