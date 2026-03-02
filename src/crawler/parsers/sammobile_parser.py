"""SamMobile Parser

This module provides a parser for extracting articles from SamMobile.
"""

import logging
from typing import Dict, Any
import requests
from bs4 import BeautifulSoup
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter
from crawler.utils.article_extractor import MetaTagExtractor, JsonLdExtractor
from crawler.utils.proxy_config import ProxyConfig


class SamMobileParser(BaseParser):
    """Parser for SamMobile articles"""

    def __init__(self, max_workers: int = None, delay: float = None,
                 log_level: int = logging.INFO, format_preset: str = None):
        super().__init__(max_workers=max_workers or 1, log_level=log_level)
        self.delay = delay or 2.0
        self.rate_limiter = SimpleRateLimiter(delay=self.delay)
        self.logger.info(f"SamMobileParser initialized")

    def _get_logger_name(self) -> str:
        return "sammobile_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single SamMobile article

        Args:
            url: URL of the SamMobile article

        Returns:
            Dict containing article data (title, author, date, content, etc.)
        """
        self.logger.info(f"Parsing SamMobile article: {url}")
        self.rate_limiter.wait()

        try:
            soup = self.fetch_html(url)

            # Extract metadata from JSON-LD (for title, author, date)
            json_ld_data = JsonLdExtractor.extract_article_data(soup, self.logger)

            title = json_ld_data.get('title') if json_ld_data else None
            author = json_ld_data.get('author') if json_ld_data else None
            date = json_ld_data.get('date') if json_ld_data else None

            # Fallback to meta tags
            if not title:
                title = MetaTagExtractor.extract_title(soup)
            if not author:
                author = MetaTagExtractor.extract_author(soup)
            if not date:
                date = MetaTagExtractor.extract_date(soup)

            # Extract content from all <p> tags
            # SamMobile has div.content elements, get all paragraphs from all of them
            content_divs = soup.find_all('div', class_='content')
            paragraphs = []
            for div in content_divs:
                for p in div.find_all('p'):
                    text = p.get_text(strip=True)
                    if len(text) > 50:  # Only include substantial paragraphs
                        paragraphs.append(text)

            content = '\n\n'.join(paragraphs) if paragraphs else 'No content found'

            return {
                'status': 'success',
                'url': url,
                'title': title or 'Unknown',
                'author': author or 'SamMobile',
                'date': date or 'Unknown',
                'content': content,
                'parser': 'sammobile'
            }

        except requests.RequestException as e:
            self.logger.error(f"Error fetching {url}: {str(e)}")
            return {
                'status': 'error',
                'url': url,
                'error': str(e),
                'parser': 'sammobile'
            }
        except Exception as e:
            self.logger.error(f"Unexpected error parsing {url}: {str(e)}")
            return {
                'status': 'error',
                'url': url,
                'error': str(e),
                'parser': 'sammobile'
            }
