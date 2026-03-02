"""Dexerto Parser - Extracts article content from Dexerto"""

import logging
from typing import Dict, Any
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter


class DexertoParser(BaseParser):
    """Parser for Dexerto articles"""

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
        self.logger.info(f"DexertoParser initialized")

    def _get_logger_name(self) -> str:
        return "dexerto_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single Dexerto article"""
        self.logger.info(f"Parsing Dexerto article: {url}")

        self.rate_limiter.wait()

        return self.parse_with_extractor(
            url=url,
            parser_name='dexerto',
            default_author='Dexerto',
            use_paragraphs=True  # Dexerto works better with paragraph extraction
        )
