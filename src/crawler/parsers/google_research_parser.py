"""
Google Research Parser
Parses articles from research.google
"""

import logging
from typing import Dict, Any
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter


class GoogleResearchParser(BaseParser):
    """Parser for Google Research blog articles"""

    def __init__(self, max_workers=None, delay=None, log_level=logging.INFO, format_preset=None):
        super().__init__(max_workers=max_workers or 1, log_level=log_level)
        self.delay = delay or 1.0
        self.rate_limiter = SimpleRateLimiter(delay=self.delay)
        self.logger.info(f"GoogleResearchParser initialized")

    def _get_logger_name(self) -> str:
        return "google_research_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single Google Research blog article"""
        self.logger.info(f"Parsing Google Research article: {url}")
        self.rate_limiter.wait()

        # Google Research uses main tag for content
        custom_selectors = [
            ('main', {}),
        ]

        return self.parse_with_extractor(
            url=url,
            parser_name='google_research',
            default_author="Google Research",
            custom_content_selectors=custom_selectors
        )
