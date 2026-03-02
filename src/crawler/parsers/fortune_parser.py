#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Fortune Parser
Specialized parser for Fortune articles
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
import re
from typing import Dict, Any, Optional

from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter
from crawler.utils.proxy_config import ProxyConfig


class FortuneParser(BaseParser):
    """
    Fortune specialized parser
    Extracts content from Fortune articles
    """

    def __init__(self, log_level: int = logging.INFO, format_preset: str = None):
        """
        Initialize Fortune parser

        Args:
            log_level: Logging level
            format_preset: Format preset (ignored, for compatibility)
        """
        super().__init__(max_workers=1, log_level=log_level)

        self.rate_limiter = SimpleRateLimiter(delay=1.0)

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }

    def parse_single(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single Fortune article

        Args:
            url: Fortune article URL

        Returns:
            Parsed data dictionary
        """
        try:
            self.logger.info(f"Parsing Fortune article: {url}")

            # Rate limiting
            self.rate_limiter.wait()

            # Fetch page with proxy support
            proxies = ProxyConfig.get_proxies()
            response = requests.get(url, headers=self.headers, proxies=proxies, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract title - h1 before cleanup
            h1 = soup.find('h1')
            title = h1.get_text().strip() if h1 else 'No title'

            # Remove unwanted elements
            for element in soup(['script', 'style', 'nav', 'footer', 'header', 'aside', 'form', 'iframe']):
                element.decompose()

            # Remove Fortune-specific clutter
            for selector in ['.advertisement', '.related-articles', '.social-share']:
                for elem in soup.select(selector):
                    elem.decompose()

            # Extract main content
            content = self._extract_content(soup)

            # Extract metadata
            author = self._extract_author(soup)
            date = self._extract_date(soup)

            result = {
                'url': url,
                'title': title,
                'author': author,
                'date': date,
                'content': content,
                'parser': 'fortune',
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            }

            self.logger.info(f"Successfully parsed Fortune article: {url}")
            return result

        except Exception as e:
            self.logger.error(f"Failed to parse {url}: {e}")
            return {
                'url': url,
                'title': None,
                'author': None,
                'date': None,
                'content': None,
                'parser': 'fortune',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'status': 'error'
            }

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main article content"""

        # Fortune uses article tag
        article = soup.find('article')
        if not article:
            # Fallback to main content div
            article = soup.find('div', class_='article-content') or \
                     soup.find('div', class_='entry-content')

        if not article:
            return "No content found"

        # Get paragraphs, skip duplicates and short text
        paragraphs = []
        seen_text = set()

        for p in article.find_all('p'):
            text = p.get_text().strip()

            # Skip short text, ads, and duplicates
            if len(text) < 30:
                continue
            if text in seen_text:
                continue
            if any(skip in text.lower() for skip in [
                'subscribe', 'sign up', 'newsletter', 'advertisement',
                'read more', 'click here', 'terms of use'
            ]):
                continue

            seen_text.add(text)
            paragraphs.append(text)

        if paragraphs:
            return '\n\n'.join(paragraphs)

        # Fallback: get all text from article
        text = article.get_text(separator='\n\n', strip=True)
        if len(text) > 100:
            return text

        return "No content found"

    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extract author name"""

        # Try meta tag first
        author_meta = soup.find('meta', {'name': 'author'}) or \
                     soup.find('meta', {'property': 'article:author'})
        if author_meta:
            return author_meta.get('content', 'Unknown')

        # Try byline elements
        byline = soup.find('span', class_='author') or \
                soup.find('a', rel='author') or \
                soup.find('div', class_='byline')
        if byline:
            return byline.get_text().strip()

        return 'Unknown'

    def _extract_date(self, soup: BeautifulSoup) -> str:
        """Extract publication date"""

        # Try meta tag
        date_meta = soup.find('meta', {'property': 'article:published_time'}) or \
                   soup.find('meta', {'name': 'publishdate'})
        if date_meta:
            return date_meta.get('content', 'Unknown')

        # Try time element
        time_elem = soup.find('time')
        if time_elem:
            if time_elem.has_attr('datetime'):
                return time_elem['datetime']
            return time_elem.get_text().strip()

        return 'Unknown'

    def parse_multiple(self, urls, output_dir: str = None):
        """Not implemented for Fortune parser"""
        raise NotImplementedError("Fortune parser does not support batch processing")

    def _get_logger_name(self) -> str:
        """Get logger name for this parser"""
        return 'fortune_parser'

    def save_results(self, results, output_dir: str = None):
        """Save results (not implemented for Fortune parser)"""
        raise NotImplementedError("Fortune parser does not support saving results")
