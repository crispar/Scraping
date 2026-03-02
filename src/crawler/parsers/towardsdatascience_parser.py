"""Towards Data Science Parser - Extracts article content from Towards Data Science (Medium)"""

import logging
from typing import Dict, Any
from bs4 import BeautifulSoup
import json
import requests
from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter
from crawler.utils.proxy_config import ProxyConfig


class TowardsDataScienceParser(BaseParser):
    """Parser for Towards Data Science articles (Medium platform)"""

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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        self.logger.info(f"TowardsDataScienceParser initialized")

    def _get_logger_name(self) -> str:
        return "towardsdatascience_parser"

    def parse_single(self, url: str) -> Dict[str, Any]:
        """Parse a single Towards Data Science article"""
        self.logger.info(f"Parsing Towards Data Science article: {url}")

        try:
            self.rate_limiter.wait()

            response = requests.get(
                url,
                headers=self.headers,
                timeout=30,
                proxies=ProxyConfig.get_proxies()
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Try JSON-LD first
            json_ld_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_ld_scripts:
                try:
                    data = json.loads(script.string)
                    if isinstance(data, list):
                        data = data[0]

                    if data.get('@type') in ['NewsArticle', 'Article', 'BlogPosting']:
                        content = self._extract_content_from_html(soup)

                        return {
                            'status': 'success',
                            'url': url,
                            'title': data.get('headline', 'Unknown'),
                            'author': self._extract_author(data),
                            'date': data.get('datePublished', 'Unknown'),
                            'content': content,
                            'parser': 'towardsdatascience'
                        }
                except json.JSONDecodeError:
                    continue

            # Fallback to HTML parsing
            title = self._extract_title(soup)
            author = self._extract_author_from_html(soup)
            date = self._extract_date(soup)
            content = self._extract_content_from_html(soup)

            self.logger.info(f"Successfully parsed: {url}")

            return {
                'status': 'success',
                'url': url,
                'title': title,
                'author': author,
                'date': date,
                'content': content,
                'parser': 'towardsdatascience'
            }

        except Exception as e:
            self.logger.error(f"Error parsing {url}: {str(e)}")
            return {
                'status': 'error',
                'url': url,
                'error': str(e),
                'parser': 'towardsdatascience'
            }

    def _extract_author(self, data: dict) -> str:
        if 'author' in data:
            author = data['author']
            if isinstance(author, dict):
                return author.get('name', 'Unknown')
            elif isinstance(author, list) and len(author) > 0:
                if isinstance(author[0], dict):
                    return author[0].get('name', 'Unknown')
                return str(author[0])
            return str(author)
        return 'Unknown'

    def _extract_title(self, soup: BeautifulSoup) -> str:
        # Try h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)

        # Try og:title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content']

        # Try title tag
        title = soup.find('title')
        if title:
            return title.get_text(strip=True)

        return 'Unknown'

    def _extract_author_from_html(self, soup: BeautifulSoup) -> str:
        # Try author meta
        meta_author = soup.find('meta', {'name': 'author'})
        if meta_author and meta_author.get('content'):
            return meta_author['content']

        # Try Medium-specific author link
        author_link = soup.find('a', {'data-testid': 'authorName'})
        if author_link:
            return author_link.get_text(strip=True)

        # Try byline
        byline = soup.find(['span', 'div', 'a'], class_=lambda x: x and 'author' in str(x).lower())
        if byline:
            return byline.get_text(strip=True)

        return 'Unknown'

    def _extract_date(self, soup: BeautifulSoup) -> str:
        # Try article:published_time
        published = soup.find('meta', property='article:published_time')
        if published and published.get('content'):
            return published['content']

        # Try time tag
        time_tag = soup.find('time')
        if time_tag and time_tag.get('datetime'):
            return time_tag['datetime']

        return 'Unknown'

    def _extract_content_from_html(self, soup: BeautifulSoup) -> str:
        # Try article tag
        article = soup.find('article')
        if not article:
            article = soup.find('div', class_=lambda x: x and ('article-content' in str(x).lower() or 'post-content' in str(x).lower()))
        if not article:
            article = soup.find('main')

        if not article:
            return "No content found"

        # Remove unwanted elements
        for element in article.find_all(['script', 'style', 'nav', 'header', 'footer', 'aside', 'button', 'form', 'iframe']):
            element.decompose()

        # Remove ads and social elements
        for class_pattern in ['ad-', 'social', 'share', 'newsletter', 'related', 'sidebar', 'comment']:
            for elem in article.find_all(class_=lambda x: x and class_pattern in str(x).lower()):
                elem.decompose()

        # Extract text from paragraphs
        paragraphs = article.find_all(['p', 'h2', 'h3', 'h4'])
        content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

        return content if content else "No content found"

    def parse_multiple(self, urls, output_dir: str = None):
        """Not implemented for Towards Data Science parser"""
        raise NotImplementedError("Towards Data Science parser does not support batch processing")

    def save_results(self, results, output_file: str):
        """Not implemented for Towards Data Science parser"""
        raise NotImplementedError("Towards Data Science parser does not support saving results")
