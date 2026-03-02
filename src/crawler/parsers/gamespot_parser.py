"""GameSpot Parser - Extracts article content from GameSpot"""

import logging
from typing import Dict, Any
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter


class GameSpotParser(BaseParser):
    """Parser for GameSpot articles"""

    def __init__(
        self,
        max_workers: int = None,
        delay: float = None,
        log_level: int = logging.INFO,
        format_preset: str = None
    ):
        super().__init__(max_workers=max_workers or 1, log_level=log_level)
        self.delay = delay or 1.0
        self.rate_limiter = SimpleRateLimiter(delay=self.delay)
        self.logger.info(f"GameSpotParser initialized")

    def _get_logger_name(self) -> str:
        return "gamespot_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single GameSpot article"""
        self.logger.info(f"Parsing GameSpot article: {url}")

        self.rate_limiter.wait()

        # Custom selectors for GameSpot
        custom_selectors = [
            ('div', {'class': 'content-entity-body'}),
            ('div', {'class': 'js-content-entity-body'}),
        ]

        return self.parse_with_extractor(
            url=url,
            parser_name='gamespot',
            default_author='GameSpot',
            custom_content_selectors=custom_selectors
        )
