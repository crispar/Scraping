#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Naver News Parser
Parse content from Naver News articles
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import re
from typing import Dict, Any, Optional

from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter


class NaverNewsParser(BaseParser):
    """
    Naver News parser
    Extracts content from Naver News articles
    """

    def __init__(self, log_level: int = logging.INFO, format_preset: str = None):
        """
        Initialize Naver News parser

        Args:
            log_level: Logging level
            format_preset: Format preset (ignored, for compatibility)
        """
        super().__init__(max_workers=1, log_level=log_level)

        self.rate_limiter = SimpleRateLimiter(delay=1.0)

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

    def parse_single(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single Naver News article

        Args:
            url: Naver News article URL

        Returns:
            Parsed data dictionary
        """
        try:
            self.logger.info(f"Parsing Naver News: {url}")

            # Rate limiting
            self.rate_limiter.wait()

            # Fetch page
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'

            # Parse HTML
            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract title
            title_elem = soup.select_one('#title_area') or soup.select_one('.media_end_head_headline')
            title = title_elem.get_text().strip() if title_elem else 'No title'

            # Extract content
            article_elem = soup.select_one('#dic_area') or soup.select_one('#articeBody') or soup.select_one('.article_body')

            if article_elem:
                # Remove unwanted elements
                for elem in article_elem.select('em, strong.media_end_summary'):
                    elem.decompose()

                content = article_elem.get_text().strip()
                # Clean up whitespace
                content = re.sub(r'\n\s*\n', '\n\n', content)
            else:
                content = 'No content found'

            # Extract metadata
            press = self._extract_press(soup)
            author = self._extract_author(soup)
            date = self._extract_date(soup)
            category = self._extract_category(soup, url)

            result = {
                'url': url,
                'title': title,
                'press': press,
                'author': author,
                'date': date,
                'category': category,
                'content': content,
                'parser': 'naver_news',
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            }

            self.logger.info(f"Successfully parsed Naver News: {url}")
            return result

        except Exception as e:
            self.logger.error(f"Failed to parse {url}: {e}")
            return {
                'url': url,
                'title': None,
                'press': None,
                'author': None,
                'date': None,
                'category': None,
                'content': None,
                'parser': 'naver_news',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'status': 'error'
            }

    def _extract_press(self, soup: BeautifulSoup) -> str:
        """Extract press name"""
        press_elem = soup.select_one('.media_end_head_top_logo img') or \
                    soup.select_one('.press_logo img') or \
                    soup.select_one('.media_end_linked_more_point')

        if press_elem:
            if press_elem.name == 'img':
                return press_elem.get('alt', 'Unknown')
            return press_elem.get_text().strip()

        return 'Unknown'

    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extract author name"""
        author_elem = soup.select_one('.media_end_head_journalist_name') or \
                     soup.select_one('.byline_s') or \
                     soup.select_one('.reporter')

        if author_elem:
            author = author_elem.get_text().strip()
            # Remove common suffixes
            author = re.sub(r'\s*(기자|특파원|앵커|에디터)\s*$', '', author)
            return author

        return 'Unknown'

    def _extract_date(self, soup: BeautifulSoup) -> str:
        """Extract publication date"""
        date_elem = soup.select_one('.media_end_head_info_datestamp_time') or \
                   soup.select_one('._ARTICLE_DATE_TIME') or \
                   soup.select_one('.sponsor span.t11')

        if date_elem:
            # Check for data-date-time attribute
            if date_elem.has_attr('data-date-time'):
                return date_elem['data-date-time']
            return date_elem.get_text().strip()

        return 'Unknown'

    def _extract_category(self, soup: BeautifulSoup, url: str) -> str:
        """Extract article category"""
        # Try breadcrumb
        category_elem = soup.select_one('.media_end_categorize_item') or \
                       soup.select_one('.section_group')

        if category_elem:
            return category_elem.get_text().strip()

        # Extract from URL sid parameter
        sid_match = re.search(r'sid=(\d+)', url)
        if sid_match:
            sid_map = {
                '100': '정치',
                '101': '경제',
                '102': '사회',
                '103': '생활/문화',
                '104': '세계',
                '105': 'IT/과학'
            }
            return sid_map.get(sid_match.group(1), 'Unknown')

        return 'Unknown'

    def parse_multiple(self, urls, output_dir: str = None):
        """Not implemented for Naver News parser"""
        raise NotImplementedError("Naver News parser does not support batch processing")

    def _get_logger_name(self) -> str:
        """Get logger name for this parser"""
        return 'naver_news_parser'

    def save_results(self, results, output_dir: str = None):
        """Save results (not implemented for Naver News parser)"""
        raise NotImplementedError("Naver News parser does not support saving results")
