"""
Deadline Parser
Parses articles from deadline.com
"""

import logging
from typing import Dict, Any
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter


class DeadlineParser(BaseParser):
    """Parser for Deadline articles"""

    def __init__(self, max_workers=None, delay=None, log_level=logging.INFO, format_preset=None):
        super().__init__(max_workers=max_workers or 1, log_level=log_level)
        self.delay = delay or 1.0
        self.rate_limiter = SimpleRateLimiter(delay=self.delay)
        self.logger.info(f"DeadlineParser initialized")

    def _get_logger_name(self) -> str:
        return "deadline_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single Deadline article"""
        self.logger.info(f"Parsing Deadline article: {url}")
        self.rate_limiter.wait()

        # Deadline uses standard article tag for content
        custom_selectors = [
            ('article', {}),
        ]

        return self.parse_with_extractor(
            url=url,
            parser_name='deadline',
            default_author="Deadline",
            custom_content_selectors=custom_selectors
        )
