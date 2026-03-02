"""
ZME Science Parser
Parses articles from ZME Science (zmescience.com)
"""

import logging
import warnings
from typing import Dict, Any
from bs4 import BeautifulSoup
import requests
import urllib3
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter
from crawler.utils.article_extractor import ArticleParser


class ZMEScienceParser(BaseParser):
    """Parser for ZME Science articles"""

    def __init__(self, max_workers=None, delay=None, log_level=logging.INFO, format_preset=None):
        super().__init__(max_workers=max_workers or 1, log_level=log_level)
        self.delay = delay or 1.0
        self.rate_limiter = SimpleRateLimiter(delay=self.delay)
        self.logger.info(f"ZMEScienceParser initialized")

    def _get_logger_name(self) -> str:
        return "zmescience_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single ZME Science article"""
        self.logger.info(f"Parsing ZME Science article: {url}")

        try:
            self.rate_limiter.wait()

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            # ZME Science has SSL certificate issues - disable verification only for this request
            # and suppress only the specific warning for this call
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=urllib3.exceptions.InsecureRequestWarning)
                response = requests.get(url, headers=headers, timeout=30, verify=False)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Use ArticleParser utility for extraction
            result = ArticleParser.parse_article(
                soup=soup,
                url=url,
                parser_name='zmescience',
                default_author='ZME Science',
                logger=self.logger
            )

            self.logger.info(f"Successfully parsed: {url}")
            return result

        except Exception as e:
            self.logger.error(f"Error parsing {url}: {str(e)}")
            return {
                'status': 'error',
                'url': url,
                'error': str(e),
                'parser': 'zmescience'
            }
