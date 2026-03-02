"""Article Content Extractor Utilities

This module provides common utilities for extracting article metadata and content
from various news and blog websites.
"""

import json
import logging
import html
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup, Tag


class JsonLdExtractor:
    """Extracts metadata from JSON-LD structured data"""

    @staticmethod
    def extract_article_data(soup: BeautifulSoup, logger: logging.Logger = None) -> Optional[Dict[str, Any]]:
        """
        Extract article data from JSON-LD scripts

        Args:
            soup: BeautifulSoup object
            logger: Optional logger for debugging

        Returns:
            Dict with keys: title, author, date, content (or None if not found)
        """
        json_ld_scripts = soup.find_all('script', type='application/ld+json')

        for script in json_ld_scripts:
            try:
                data = json.loads(script.string)

                # Handle @graph structure
                if isinstance(data, dict) and '@graph' in data:
                    for item in data['@graph']:
                        if item.get('@type') in ['NewsArticle', 'Article', 'BlogPosting']:
                            data = item
                            break

                # Handle list structure
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and item.get('@type') in ['NewsArticle', 'Article', 'BlogPosting']:
                            data = item
                            break

                # Check if we have an article type
                if isinstance(data, dict) and data.get('@type') in ['NewsArticle', 'Article', 'BlogPosting']:
                    title = data.get('headline') or data.get('name')
                    author = JsonLdExtractor._extract_author(data)
                    content = data.get('articleBody')

                    result = {
                        'title': html.unescape(title) if title else None,
                        'author': html.unescape(author) if author else None,
                        'date': data.get('datePublished') or data.get('dateCreated') or data.get('dateModified'),
                        'content': html.unescape(content) if content else None
                    }

                    if logger:
                        logger.info("Successfully extracted data from JSON-LD")

                    return result

            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                if logger:
                    logger.debug(f"Failed to parse JSON-LD: {e}")
                continue

        return None

    @staticmethod
    def _extract_author(data: Dict) -> Optional[str]:
        """Extract author name from various JSON-LD author formats"""
        author_data = data.get('author')

        if not author_data:
            return None

        # Handle dict format
        if isinstance(author_data, dict):
            return author_data.get('name')

        # Handle list format
        elif isinstance(author_data, list) and len(author_data) > 0:
            if isinstance(author_data[0], dict):
                return author_data[0].get('name')
            else:
                return str(author_data[0])

        # Handle string format
        elif isinstance(author_data, str):
            return author_data

        return None


class MetaTagExtractor:
    """Extracts metadata from HTML meta tags"""

    @staticmethod
    def extract_title(soup: BeautifulSoup) -> Optional[str]:
        """Extract title from meta tags or title tag"""
        # Try og:title
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content']

        # Try twitter:title
        twitter_title = soup.find('meta', {'name': 'twitter:title'})
        if twitter_title and twitter_title.get('content'):
            return twitter_title['content']

        # Try h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text(strip=True)

        # Try title tag
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text(strip=True)

        return None

    @staticmethod
    def extract_author(soup: BeautifulSoup) -> Optional[str]:
        """Extract author from meta tags"""
        # Try author meta tag
        author_meta = soup.find('meta', {'name': 'author'})
        if author_meta and author_meta.get('content'):
            return author_meta['content']

        # Try article:author
        article_author = soup.find('meta', property='article:author')
        if article_author and article_author.get('content'):
            return article_author['content']

        return None

    @staticmethod
    def extract_date(soup: BeautifulSoup) -> Optional[str]:
        """Extract publication date from meta tags"""
        # Try article:published_time
        pub_time = soup.find('meta', property='article:published_time')
        if pub_time and pub_time.get('content'):
            return pub_time['content']

        # Try datePublished
        date_pub = soup.find('meta', {'itemprop': 'datePublished'})
        if date_pub and date_pub.get('content'):
            return date_pub['content']

        # Try publication_date
        pub_date = soup.find('meta', {'name': 'publication_date'})
        if pub_date and pub_date.get('content'):
            return pub_date['content']

        return None


class ContentExtractor:
    """Extracts main article content from HTML"""

    # Common selectors for article content
    ARTICLE_SELECTORS = [
        ('article', {}),
        ('div', {'class': 'article-body'}),
        ('div', {'class': 'article-content'}),
        ('div', {'class': 'entry-content'}),
        ('div', {'class': 'post-content'}),
        ('div', {'class': 'content-body'}),
        ('div', {'itemprop': 'articleBody'}),
        ('div', {'class': 'story-body'}),
        ('main', {}),
    ]

    # Elements to remove before extraction
    UNWANTED_TAGS = ['script', 'style', 'aside', 'nav', 'footer', 'iframe', 'form']

    @staticmethod
    def extract_content(
        soup: BeautifulSoup,
        custom_selectors: List[tuple] = None,
        use_paragraphs: bool = False
    ) -> Optional[str]:
        """
        Extract main article content from HTML

        Args:
            soup: BeautifulSoup object
            custom_selectors: Optional list of (tag, attrs) tuples to try first
            use_paragraphs: If True, extract and join <p> tags instead of full text

        Returns:
            Extracted content text or None
        """
        selectors = (custom_selectors or []) + ContentExtractor.ARTICLE_SELECTORS

        for tag_name, attrs in selectors:
            element = soup.find(tag_name, attrs)

            if element:
                # Remove unwanted elements
                for unwanted_tag in ContentExtractor.UNWANTED_TAGS:
                    for unwanted in element.find_all(unwanted_tag):
                        unwanted.decompose()

                # Extract paragraphs if requested
                if use_paragraphs:
                    paragraphs = element.find_all('p')
                    if paragraphs:
                        content = '\n\n'.join([
                            p.get_text(strip=True)
                            for p in paragraphs
                            if p.get_text(strip=True)
                        ])
                        if content:
                            return content

                # Otherwise get all text
                content = element.get_text(separator='\n\n', strip=True)
                if content:
                    return content

        return None


class ArticleParser:
    """Complete article parser combining all extractors"""

    @staticmethod
    def parse_article(
        soup: BeautifulSoup,
        url: str,
        parser_name: str,
        default_author: str = 'Unknown',
        custom_content_selectors: List[tuple] = None,
        use_paragraphs: bool = False,
        logger: logging.Logger = None
    ) -> Dict[str, Any]:
        """
        Parse article using all available extraction methods

        Args:
            soup: BeautifulSoup object
            url: Article URL
            parser_name: Name of the parser (for result dict)
            default_author: Default author name if not found
            custom_content_selectors: Custom selectors for content extraction
            use_paragraphs: Whether to extract content from paragraphs
            logger: Optional logger

        Returns:
            Dict with keys: status, url, title, author, date, content, parser
        """
        # Try JSON-LD first
        json_ld_data = JsonLdExtractor.extract_article_data(soup, logger)

        title = None
        author = None
        date = None
        content = None

        # Use JSON-LD data if available
        if json_ld_data:
            title = json_ld_data.get('title')
            author = json_ld_data.get('author')
            date = json_ld_data.get('date')
            content = json_ld_data.get('content')

        # Fallback to meta tags
        if not title:
            title = MetaTagExtractor.extract_title(soup)

        if not author:
            author = MetaTagExtractor.extract_author(soup)

        if not date:
            date = MetaTagExtractor.extract_date(soup)

        # Extract content from HTML if not in JSON-LD
        if not content:
            content = ContentExtractor.extract_content(
                soup,
                custom_selectors=custom_content_selectors,
                use_paragraphs=use_paragraphs
            )

        return {
            'status': 'success',
            'url': url,
            'title': title or 'Unknown',
            'author': author or default_author,
            'date': date or 'Unknown',
            'content': content or 'No content found',
            'parser': parser_name
        }
