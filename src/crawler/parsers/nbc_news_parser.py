"""NBC News Parser - Extracts article content from NBC News"""

import logging
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup
import json
import requests
from datetime import datetime
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter
from crawler.utils.proxy_config import ProxyConfig


class NBCNewsParser(BaseParser):
    """Parser for NBC News articles using JSON-LD metadata"""

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
        self.logger.info(f"NBCNewsParser initialized")

    def _get_logger_name(self) -> str:
        return "nbc_news_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single NBC News article"""
        self.logger.info(f"Parsing NBC News article: {url}")

        try:
            # Rate limiting
            self.rate_limiter.wait()

            # Fetch page with proxy support
            response = requests.get(url, headers=self.headers, proxies=ProxyConfig.get_proxies(), timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'

            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')

            # Try to find JSON-LD data
            json_ld = self._extract_json_ld(soup)

            if json_ld:
                title = json_ld.get('headline', 'No title')
                author = self._extract_author(json_ld)
                date = json_ld.get('datePublished', 'Unknown')
                content = json_ld.get('articleBody', '')

                # If no articleBody in JSON-LD, try HTML extraction
                if not content or len(content) < 100:
                    content = self._extract_content_from_html(soup)
            else:
                # Fallback to HTML parsing
                title = self._extract_title(soup)
                author = self._extract_author_from_html(soup)
                date = 'Unknown'
                content = self._extract_content_from_html(soup)

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

    def _extract_json_ld(self, soup: BeautifulSoup) -> Optional[Dict]:
        """Extract JSON-LD metadata from the page"""
        try:
            # Find all script tags with type application/ld+json
            for script in soup.find_all('script', type='application/ld+json'):
                try:
                    data = json.loads(script.string)
                    # Look for NewsArticle or Article type
                    if isinstance(data, dict):
                        if data.get('@type') in ['NewsArticle', 'Article']:
                            return data
                        # Sometimes it's wrapped in @graph
                        if '@graph' in data:
                            for item in data['@graph']:
                                if item.get('@type') in ['NewsArticle', 'Article']:
                                    return item
                    elif isinstance(data, list):
                        for item in data:
                            if item.get('@type') in ['NewsArticle', 'Article']:
                                return item
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            self.logger.warning(f"Error extracting JSON-LD: {str(e)}")
        return None

    def _extract_author(self, json_ld: Dict) -> str:
        """Extract author from JSON-LD data"""
        try:
            author = json_ld.get('author', {})
            if isinstance(author, dict):
                return author.get('name', 'Unknown')
            elif isinstance(author, list) and len(author) > 0:
                if isinstance(author[0], dict):
                    return author[0].get('name', 'Unknown')
                return str(author[0])
            return str(author) if author else 'Unknown'
        except:
            return 'Unknown'

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract title from HTML"""
        # Try headline-title-text class
        title_elem = soup.find('p', class_='headline-title-text')
        if title_elem:
            return title_elem.get_text().strip()

        # Try h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()

        # Fallback to title tag
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()

        return 'No title'

    def _extract_author_from_html(self, soup: BeautifulSoup) -> str:
        """Extract author from HTML"""
        # Try byline
        byline = soup.find('span', class_='byline-name')
        if byline:
            return byline.get_text().strip()

        # Try author meta tag
        author_meta = soup.find('meta', {'name': 'author'})
        if author_meta:
            return author_meta.get('content', 'Unknown')

        return 'Unknown'

    def _extract_content_from_html(self, soup: BeautifulSoup) -> str:
        """Extract content from HTML as fallback"""
        # Try article tag
        article = soup.find('article')
        if not article:
            article = soup.find('div', class_='article-body')

        if not article:
            return "No content found"

        # Remove unwanted elements
        for element in article.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            element.decompose()

        paragraphs = []
        seen_text = set()

        for p in article.find_all(['p', 'h2', 'h3']):
            text = p.get_text().strip()

            # Skip short text
            if len(text) < 20:
                continue

            # Skip duplicates
            if text in seen_text:
                continue

            # Skip common navigation/promotional text
            skip_phrases = [
                'sign up', 'newsletter', 'subscribe', 'advertisement',
                'read more', 'click here', 'follow us', 'share this'
            ]
            if any(skip in text.lower() for skip in skip_phrases):
                continue

            seen_text.add(text)
            paragraphs.append(text)

        return '\n\n'.join(paragraphs) if paragraphs else "No content found"

    def parse_multiple(self, urls, output_dir: str = None):
        """Not implemented for NBC News parser"""
        raise NotImplementedError("NBC News parser does not support batch processing")

    def save_results(self, results: list, output_file: str = None) -> None:
        """Save parsing results to file"""
        raise NotImplementedError("NBC News parser does not support saving results")
