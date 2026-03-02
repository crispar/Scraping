"""
Data Center Knowledge Parser
Parses articles from datacenterknowledge.com
"""

import logging
from typing import Dict, Any
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter


class DataCenterKnowledgeParser(BaseParser):
    """Parser for Data Center Knowledge articles"""

    def __init__(self, max_workers=None, delay=None, log_level=logging.INFO, format_preset=None):
        super().__init__(max_workers=max_workers or 1, log_level=log_level)
        self.delay = delay or 1.0
        self.rate_limiter = SimpleRateLimiter(delay=self.delay)
        self.logger.info(f"DataCenterKnowledgeParser initialized")

    def _get_logger_name(self) -> str:
        return "datacenterknowledge_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single Data Center Knowledge article"""
        self.logger.info(f"Parsing Data Center Knowledge article: {url}")
        self.rate_limiter.wait()

        # Data Center Knowledge uses section.Layout-Section for article content
        custom_selectors = [
            ('section', {'class': 'Layout-Section'}),
            ('section', {}),  # Fallback to any section
        ]

        return self.parse_with_extractor(
            url=url,
            parser_name='datacenterknowledge',
            default_author="Data Center Knowledge",
            custom_content_selectors=custom_selectors
        )
