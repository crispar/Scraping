"""
InterviewQuery Parser
Parses articles from interviewquery.com
"""

import logging
from typing import Dict, Any
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter


class InterviewQueryParser(BaseParser):
    """Parser for InterviewQuery articles"""

    def __init__(self, max_workers=None, delay=None, log_level=logging.INFO, format_preset=None):
        super().__init__(max_workers=max_workers or 1, log_level=log_level)
        self.delay = delay or 1.0
        self.rate_limiter = SimpleRateLimiter(delay=self.delay)
        self.logger.info(f"InterviewQueryParser initialized")

    def _get_logger_name(self) -> str:
        return "interviewquery_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single InterviewQuery article"""
        self.logger.info(f"Parsing InterviewQuery article: {url}")
        self.rate_limiter.wait()

        # InterviewQuery uses page_container_content class for main content
        custom_selectors = [
            ('div', {'class': lambda x: x and 'page_container_content' in ' '.join(x) if isinstance(x, list) else 'page_container_content' in x if x else False}),
            ('div', {'class': lambda x: x and 'page_container' in ' '.join(x) if isinstance(x, list) else 'page_container' in x if x else False}),
        ]

        return self.parse_with_extractor(
            url=url,
            parser_name='interviewquery',
            default_author="InterviewQuery",
            custom_content_selectors=custom_selectors
        )
