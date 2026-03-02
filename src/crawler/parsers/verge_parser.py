#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
The Verge Parser
Specialized parser for The Verge articles
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


class VergeParser(BaseParser):
    """
    The Verge specialized parser
    Extracts content from The Verge articles
    """

    def __init__(self, log_level: int = logging.INFO, format_preset: str = None):
        """
        Initialize Verge parser

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
        Parse a single Verge article

        Args:
            url: Verge article URL

        Returns:
            Parsed data dictionary
        """
        try:
            self.logger.info(f"Parsing Verge article: {url}")

            # Rate limiting
            self.rate_limiter.wait()

            # Fetch page with proxy support
            response = requests.get(url, headers=self.headers, proxies=ProxyConfig.get_proxies(), timeout=10)
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

            # Remove Verge-specific clutter
            for selector in ['.c-header', '.c-footer', '.l-sidebar', '.m-ad', '.c-related-list']:
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
                'parser': 'verge',
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            }

            self.logger.info(f"Successfully parsed Verge article: {url}")
            return result

        except Exception as e:
            self.logger.error(f"Failed to parse {url}: {e}")
            return {
                'url': url,
                'title': None,
                'author': None,
                'date': None,
                'content': None,
                'parser': 'verge',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'status': 'error'
            }

    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main article content"""

        # The Verge uses specific article structure
        article = soup.find('article')
        if not article:
            return "No content found"

        # Get paragraphs from article, skip duplicates
        paragraphs = []
        seen_text = set()

        for p in article.find_all('p'):
            text = p.get_text().strip()
            # Skip short text, navigation text, and duplicates
            if len(text) < 30:
                continue
            if text in seen_text:
                continue
            if any(skip in text.lower() for skip in ['share this story', 'most popular', 'read more']):
                continue

            seen_text.add(text)
            paragraphs.append(text)

        if paragraphs:
            return '\n\n'.join(paragraphs)

        return "No content found"

    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extract author name"""

        # Try meta tag first
        author_meta = soup.find('meta', {'name': 'author'}) or \
                     soup.find('meta', {'property': 'article:author'})
        if author_meta:
            return author_meta.get('content', 'Unknown')

        # Try byline
        byline = soup.find('span', class_='c-byline__author-name') or \
                soup.find('a', rel='author')
        if byline:
            return byline.get_text().strip()

        return 'Unknown'

    def _extract_date(self, soup: BeautifulSoup) -> str:
        """Extract publication date"""

        # Try meta tag
        date_meta = soup.find('meta', {'property': 'article:published_time'})
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
        """Not implemented for Verge parser"""
        raise NotImplementedError("Verge parser does not support batch processing")

    def _get_logger_name(self) -> str:
        """Get logger name for this parser"""
        return 'verge_parser'

    def save_results(self, results, output_dir: str = None):
        """Save results (not implemented for Verge parser)"""
        raise NotImplementedError("Verge parser does not support saving results")
