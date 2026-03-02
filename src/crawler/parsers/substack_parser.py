"""Substack Parser - Extracts article content from Substack"""

import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
import json
import requests
import re
from datetime import datetime
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter
from crawler.utils.proxy_config import ProxyConfig


class SubstackParser(BaseParser):
    """Parser for Substack articles"""

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
        self.logger.info(f"SubstackParser initialized")

    def _get_logger_name(self) -> str:
        return "substack_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single Substack article"""
        self.logger.info(f"Parsing Substack article: {url}")

        try:
            # Rate limiting
            self.rate_limiter.wait()

            # Fetch page with proxy support
            response = requests.get(url, headers=self.headers, proxies=ProxyConfig.get_proxies(), timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Try to extract JSON data from script tags
            json_data = self._extract_json_data(soup, response.text)

            if json_data:
                title = json_data.get('title', 'No title')
                author = self._extract_author_from_json(json_data)
                date = json_data.get('post_date', 'Unknown')

                # Extract content from body_html
                body_html = json_data.get('body_html', '')
                content = self._extract_content_from_html(body_html)
            else:
                # Fallback to HTML parsing
                title = self._extract_title(soup)
                author = self._extract_author_from_html(soup)
                date = self._extract_date(soup)
                content = self._extract_content_from_soup(soup)

            result = {
                'url': url,
                'status': 'success',
                'title': title,
                'author': author,
                'date': date,
                'content': content,
                'timestamp': datetime.now().isoformat()
            }

            self.logger.info(f"Successfully parsed: {url}")
            return result

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

    def _extract_json_data(self, soup: BeautifulSoup, html_text: str) -> Optional[Dict]:
        """Extract JSON data from page"""
        try:
            # Look for window._preloads pattern
            pattern = r'window\._preloads\s*=\s*JSON\.parse\("(.+?)"\)'
            matches = re.search(pattern, html_text)

            if matches:
                json_str = matches.group(1)
                # Unescape the JSON string
                json_str = json_str.encode().decode('unicode_escape')
                data = json.loads(json_str)

                # Navigate to post data
                if isinstance(data, dict):
                    # Try different paths to find post data
                    post_data = data.get('post', {})
                    if post_data:
                        return post_data

                    # Try alternate structure
                    for key, value in data.items():
                        if isinstance(value, dict) and 'title' in value:
                            return value

            # Try to find JSON-LD
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    if isinstance(data, dict) and data.get('@type') in ['Article', 'BlogPosting']:
                        return {
                            'title': data.get('headline', 'No title'),
                            'body_html': data.get('articleBody', ''),
                            'post_date': data.get('datePublished', 'Unknown')
                        }
                except:
                    continue

        except Exception as e:
            self.logger.warning(f"Error extracting JSON data: {str(e)}")

        return None

    def _extract_author_from_json(self, json_data: Dict) -> str:
        """Extract author from JSON data"""
        try:
            # Try publishedBylines array
            bylines = json_data.get('publishedBylines', [])
            if bylines and len(bylines) > 0:
                return bylines[0].get('name', 'Unknown')

            # Try direct author field
            author = json_data.get('author', {})
            if isinstance(author, dict):
                return author.get('name', 'Unknown')
            elif isinstance(author, str):
                return author

        except:
            pass
        return 'Unknown'

    def _extract_content_from_html(self, body_html: str) -> str:
        """Extract clean text content from HTML body"""
        if not body_html:
            return "No content found"

        try:
            soup = BeautifulSoup(body_html, 'html.parser')

            # Remove unwanted elements
            for element in soup.find_all(['script', 'style', 'button']):
                element.decompose()

            paragraphs = []
            seen_text = set()

            # Extract text from paragraphs
            for p in soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'li']):
                text = p.get_text().strip()

                # Skip short or duplicate text
                if len(text) < 20 or text in seen_text:
                    continue

                seen_text.add(text)
                paragraphs.append(text)

            return '\n\n'.join(paragraphs) if paragraphs else "No content found"

        except Exception as e:
            self.logger.warning(f"Error extracting content from HTML: {str(e)}")
            return "No content found"

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract title from HTML"""
        # Try h1
        h1 = soup.find('h1', class_='post-title')
        if h1:
            return h1.get_text().strip()

        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()

        # Try meta tag
        meta_title = soup.find('meta', property='og:title')
        if meta_title:
            return meta_title.get('content', 'No title')

        # Fallback to title tag
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()

        return 'No title'

    def _extract_author_from_html(self, soup: BeautifulSoup) -> str:
        """Extract author from HTML"""
        # Try author meta
        author_meta = soup.find('meta', {'name': 'author'})
        if author_meta:
            return author_meta.get('content', 'Unknown')

        # Try author link
        author_link = soup.find('a', class_='author')
        if author_link:
            return author_link.get_text().strip()

        return 'Unknown'

    def _extract_date(self, soup: BeautifulSoup) -> str:
        """Extract date from HTML"""
        # Try time tag
        time_tag = soup.find('time')
        if time_tag:
            return time_tag.get('datetime', time_tag.get_text().strip())

        # Try meta tag
        date_meta = soup.find('meta', property='article:published_time')
        if date_meta:
            return date_meta.get('content', 'Unknown')

        return 'Unknown'

    def _extract_content_from_soup(self, soup: BeautifulSoup) -> str:
        """Extract content from BeautifulSoup object (fallback)"""
        # Try to find article body
        article = soup.find('article')
        if not article:
            article = soup.find('div', class_='body')
        if not article:
            article = soup.find('div', class_='post-content')

        if not article:
            return "No content found"

        # Remove unwanted elements
        for element in article.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'button']):
            element.decompose()

        paragraphs = []
        seen_text = set()

        for p in article.find_all(['p', 'h2', 'h3', 'li']):
            text = p.get_text().strip()

            if len(text) < 20 or text in seen_text:
                continue

            # Skip common unwanted phrases
            skip_phrases = [
                'subscribe', 'sign up', 'newsletter', 'share',
                'comment', 'follow', 'like'
            ]
            if any(skip in text.lower() for skip in skip_phrases):
                continue

            seen_text.add(text)
            paragraphs.append(text)

        return '\n\n'.join(paragraphs) if paragraphs else "No content found"

    def parse_multiple(self, urls, output_dir: str = None):
        """Not implemented for Substack parser"""
        raise NotImplementedError("Substack parser does not support batch processing")

    def save_results(self, results: list, output_file: str = None) -> None:
        """Save parsing results to file"""
        raise NotImplementedError("Substack parser does not support saving results")
