"""TechCrunch Parser - Extracts article content from TechCrunch"""

import logging
from typing import Dict, Any
from bs4 import BeautifulSoup
import requests
from crawler.core.base_parser import BaseParser
from crawler.core.common_parser_mixin import CommonParserMixin
from crawler.core.parse_result import ParseResultBuilder
from crawler.utils.rate_limiter import SimpleRateLimiter
from crawler.utils.proxy_config import ProxyConfig


class TechCrunchParser(BaseParser, CommonParserMixin):
    """Parser for TechCrunch articles"""

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
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.logger.info(f"TechCrunchParser initialized")

    def _get_logger_name(self) -> str:
        return "techcrunch_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single TechCrunch article"""
        self.logger.info(f"Parsing TechCrunch article: {url}")

        try:
            self.rate_limiter.wait()

            response = requests.get(
                url,
                headers=self.headers,
                timeout=30,
                proxies=ProxyConfig.get_proxies()
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract JSON-LD data
            json_ld_data = self.extract_json_ld(soup, self.logger)
            
            # Build result using builder pattern
            builder = ParseResultBuilder(url, 'techcrunch')

            # Extract fields using Mixin methods
            builder.with_title(self.extract_title(soup))
            builder.with_author(self.extract_author(soup, json_ld_data))
            builder.with_date(self.extract_date(soup, json_ld_data))
            builder.with_content(self.extract_content(soup))
            builder.with_description(self.extract_description(soup))

            # Build and return as dictionary for backward compatibility
            result = builder.build()
            self.logger.info(f"Successfully parsed: {url}")
            
            return result.to_dict()

        except Exception as e:
            self.logger.error(f"Error parsing {url}: {str(e)}")
            return {
                'status': 'error',
                'url': url,
                'error': str(e),
                'parser': 'techcrunch'
            }

    def parse_multiple(self, urls, output_dir: str = None):
        """Not implemented for TechCrunch parser"""
        raise NotImplementedError("TechCrunch parser does not support batch processing")

    def save_results(self, results, output_file: str):
        """Not implemented for TechCrunch parser"""
        raise NotImplementedError("TechCrunch parser does not support saving results")
