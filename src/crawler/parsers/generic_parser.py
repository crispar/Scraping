#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generic Web Page Parser
Parse content from any web page
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import logging
from typing import Dict, Any, Optional
from urllib.parse import urlparse

from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter
from crawler.utils.proxy_config import ProxyConfig


class GenericParser(BaseParser):
    """
    Generic web page parser
    Extracts main content from any web page
    """

    def __init__(self, log_level: int = logging.INFO, format_preset: str = None):
        """
        Initialize generic parser

        Args:
            log_level: Logging level
            format_preset: Format preset (ignored, for compatibility)
        """
        super().__init__(max_workers=1, log_level=log_level)

        self.rate_limiter = SimpleRateLimiter(delay=1.0)

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }

    def parse_single(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single web page

        Args:
            url: Web page URL

        Returns:
            Parsed data dictionary
        """
        try:
            self.logger.info(f"Parsing web page: {url}")

            # Rate limiting
            self.rate_limiter.wait()

            # Fetch page
            response = requests.get(url, headers=self.headers, proxies=ProxyConfig.get_proxies(), timeout=10)
            response.raise_for_status()
            response.encoding = response.apparent_encoding or 'utf-8'

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Extract title BEFORE cleanup - try h1 first, then title tag
            h1 = soup.find('h1')
            if h1:
                title = h1.get_text().strip()
            else:
                title_tag = soup.find('title')
                title = title_tag.get_text().strip() if title_tag else urlparse(url).netloc

            # Remove script, style, and navigation elements
            for element in soup(["script", "style", "nav", "footer", "header", "aside", "form", "iframe"]):
                element.decompose()

            # Remove common navigation and social media elements
            for class_name in ['nav', 'menu', 'sidebar', 'social', 'share', 'related', 'comments', 'ad', 'advertisement']:
                for element in soup.find_all(class_=lambda x: x and class_name in str(x).lower()):
                    element.decompose()

            # Try to find main content
            content = self._extract_main_content(soup)

            # Extract metadata
            author = self._extract_author(soup)
            date = self._extract_date(soup)
            description = self._extract_description(soup)

            result = {
                'url': url,
                'title': title,
                'author': author,
                'date': date,
                'description': description,
                'content': content,
                'parser': 'generic',
                'timestamp': datetime.now().isoformat(),
                'status': 'success'
            }

            self.logger.info(f"Successfully parsed: {url}")
            return result

        except Exception as e:
            self.logger.error(f"Failed to parse {url}: {e}")
            return {
                'url': url,
                'title': None,
                'author': None,
                'date': None,
                'description': None,
                'content': None,
                'parser': 'generic',
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'status': 'error'
            }

    def _extract_main_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from page"""

        # First, try to extract from JSON-LD
        json_content = self._extract_from_json_ld(soup)
        if json_content and len(json_content) > 100:
            return json_content

        # Try common content containers
        selectors = [
            'article',
            '[role="main"]',
            'main',
            '.post-content',
            '.article-content',
            '.article-body',
            '.entry-content',
            '#content',
            '.content',
            '.story-body',
            '.post-body'
        ]

        for selector in selectors:
            content = soup.select_one(selector)
            if content:
                # Remove unwanted elements
                for unwanted in content.find_all(['script', 'style', 'nav', 'aside', 'footer', 'header']):
                    unwanted.decompose()

                # Get all text elements
                paragraphs = []
                seen_text = set()

                for elem in content.find_all(['p', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'blockquote']):
                    text = elem.get_text().strip()

                    # Skip short text or duplicates
                    if len(text) < 20 or text in seen_text:
                        continue

                    # Skip common unwanted phrases
                    skip_phrases = ['subscribe', 'sign up', 'newsletter', 'advertisement', 'read more']
                    if any(skip in text.lower() for skip in skip_phrases):
                        continue

                    seen_text.add(text)
                    paragraphs.append(text)

                if paragraphs:
                    text = '\n\n'.join(paragraphs)
                    if len(text) > 100:
                        return text

        # Fallback: get all paragraphs from body
        paragraphs = []
        seen_text = set()

        for p in soup.find_all('p'):
            text = p.get_text().strip()
            if len(text) > 20 and text not in seen_text:
                seen_text.add(text)
                paragraphs.append(text)

        if paragraphs:
            return '\n\n'.join(paragraphs[:50])  # Limit to first 50 paragraphs

        return "No content found"

    def _extract_from_json_ld(self, soup: BeautifulSoup) -> str:
        """Try to extract content from JSON-LD metadata"""
        try:
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    import json
                    data = json.loads(script.string)

                    # Handle both single objects and arrays
                    if isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict):
                                content = self._extract_article_body(item)
                                if content:
                                    return content
                    elif isinstance(data, dict):
                        content = self._extract_article_body(data)
                        if content:
                            return content

                except (json.JSONDecodeError, AttributeError):
                    continue
        except Exception:
            pass
        return ""

    def _extract_article_body(self, data: dict) -> str:
        """Extract article body from JSON-LD object"""
        if data.get('@type') in ['Article', 'NewsArticle', 'BlogPosting']:
            # Try articleBody first
            if 'articleBody' in data:
                return data['articleBody']

            # Try description
            if 'description' in data and len(data['description']) > 100:
                return data['description']

        # Recursively check @graph
        if '@graph' in data:
            for item in data['@graph']:
                if isinstance(item, dict):
                    content = self._extract_article_body(item)
                    if content:
                        return content

        return ""

    def _extract_author(self, soup: BeautifulSoup) -> str:
        """Extract author from metadata"""

        # Try meta tags
        author_meta = soup.find('meta', {'name': 'author'}) or \
                     soup.find('meta', {'property': 'article:author'})
        if author_meta:
            return author_meta.get('content', 'Unknown')

        # Try common author selectors
        selectors = ['.author', '.byline', '[rel="author"]', '.writer']
        for selector in selectors:
            author = soup.select_one(selector)
            if author:
                return author.get_text().strip()

        return 'Unknown'

    def _extract_date(self, soup: BeautifulSoup) -> str:
        """Extract publication date"""

        # Try meta tags
        date_meta = soup.find('meta', {'property': 'article:published_time'}) or \
                   soup.find('meta', {'name': 'publish-date'}) or \
                   soup.find('meta', {'name': 'date'})
        if date_meta:
            return date_meta.get('content', 'Unknown')

        # Try common date selectors
        selectors = ['.date', '.published', 'time', '.post-date']
        for selector in selectors:
            date = soup.select_one(selector)
            if date:
                # Check for datetime attribute first
                if date.has_attr('datetime'):
                    return date['datetime']
                return date.get_text().strip()

        return 'Unknown'

    def _extract_description(self, soup: BeautifulSoup) -> str:
        """Extract page description"""

        desc_meta = soup.find('meta', {'name': 'description'}) or \
                   soup.find('meta', {'property': 'og:description'})
        if desc_meta:
            return desc_meta.get('content', '')

        return ''

    def parse_multiple(self, urls, output_dir: str = None):
        """Not implemented for generic parser"""
        raise NotImplementedError("Generic parser does not support batch processing")

    def _get_logger_name(self) -> str:
        """Get logger name for this parser"""
        return 'generic_parser'

    def save_results(self, results, output_dir: str = None):
        """Save results (not implemented for generic parser)"""
        raise NotImplementedError("Generic parser does not support saving results")
