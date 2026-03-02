"""Axios Parser - Extracts article content from Axios

Uses cloudscraper to bypass Cloudflare bot protection.
"""

import logging
from typing import Dict, Any
from bs4 import BeautifulSoup
import cloudscraper
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter
from crawler.utils.proxy_config import ProxyConfig
from crawler.utils.article_extractor import ArticleParser


class AxiosParser(BaseParser):
    """Parser for Axios articles"""

    def __init__(
        self,
        max_workers: int = None,
        delay: float = None,
        log_level: int = logging.INFO,
        format_preset: str = None
    ):
        super().__init__(max_workers=max_workers or 1, log_level=log_level)
        self.delay = delay or 2.0
        self.rate_limiter = SimpleRateLimiter(delay=self.delay)
        # Use cloudscraper to bypass Cloudflare protection
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'windows',
                'desktop': True
            }
        )
        self.logger.info(f"AxiosParser initialized with cloudscraper")

    def _get_logger_name(self) -> str:
        return "axios_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single Axios article"""
        self.logger.info(f"Parsing Axios article: {url}")

        try:
            self.rate_limiter.wait()

            # Use cloudscraper to bypass Cloudflare
            proxies = ProxyConfig.get_proxies()
            if proxies:
                self.scraper.proxies.update(proxies)

            response = self.scraper.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Use ArticleParser utility for extraction
            result = ArticleParser.parse_article(
                soup=soup,
                url=url,
                parser_name='axios',
                default_author='Axios',
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
                'parser': 'axios'
            }
