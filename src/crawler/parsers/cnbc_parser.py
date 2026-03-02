"""CNBC Parser - Extracts article content from CNBC"""

import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
import requests
from datetime import datetime
from crawler.core.base_parser import BaseParser
from crawler.core.common_parser_mixin import CommonParserMixin
from crawler.core.parse_result import ParseResultBuilder
from crawler.utils.rate_limiter import SimpleRateLimiter
from crawler.utils.proxy_config import ProxyConfig


class CNBCParser(BaseParser, CommonParserMixin):
    """Parser for CNBC articles"""

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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.logger.info(f"CNBCParser initialized")

    def _get_logger_name(self) -> str:
        return "cnbc_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single CNBC article"""
        self.logger.info(f"Parsing CNBC article: {url}")

        try:
            # Rate limiting
            self.rate_limiter.wait()

            # Fetch page
            response = requests.get(url, headers=self.headers, proxies=ProxyConfig.get_proxies(), timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract JSON-LD data
            json_ld_data = self.extract_json_ld(soup, self.logger)
            
            # Build result
            builder = ParseResultBuilder(url, 'cnbc')

            # Extract fields
            builder.with_title(self.extract_title(soup))
            builder.with_author(self.extract_author(soup, json_ld_data))
            builder.with_date(self.extract_date(soup, json_ld_data))
            builder.with_content(self.extract_content(soup))
            builder.with_description(self.extract_description(soup))

            # Build and return as dict
            result = builder.build()
            
            # Add timestamp as it was in the original implementation
            result_dict = result.to_dict()
            result_dict['timestamp'] = datetime.now().isoformat()

            self.logger.info(f"Successfully parsed: {url}")
            return result_dict

        except Exception as e:
            self.logger.error(f"Error parsing {url}: {str(e)}")
            return {
                'url': url,
                'status': 'error',
                'error': str(e),
                'title': 'Error',
                'author': 'Unknown',
                'date': 'Unknown',
                'content': f"Failed to parse: {str(e)}"
            }

    def parse_multiple(self, urls, output_dir: str = None):
        """Not implemented for CNBC parser"""
        raise NotImplementedError("CNBC parser does not support batch processing")

    def save_results(self, results: list, output_file: str = None) -> None:
        """Save parsing results to file"""
        raise NotImplementedError("CNBC parser does not support saving results")
