"""
Common Parser Mixin

Provides shared HTML extraction methods used across multiple parsers.
This mixin eliminates ~500+ lines of duplicated code.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup


class CommonParserMixin:
    """
    Mixin class providing common extraction methods for HTML parsers.

    This class contains reusable methods for:
    - JSON-LD extraction
    - Meta tag extraction
    - Title extraction
    - Author extraction
    - Date extraction
    - Content extraction from HTML

    Usage:
        class MyParser(BaseParser, CommonParserMixin):
            def parse_single(self, url):
                soup = BeautifulSoup(html, 'html.parser')
                title = self.extract_title(soup)
                author = self.extract_author(soup)
                ...
    """

    @staticmethod
    def extract_json_ld(soup: BeautifulSoup, logger: Optional[logging.Logger] = None) -> List[Dict[str, Any]]:
        """
        Extract all JSON-LD data from script tags.

        Args:
            soup: BeautifulSoup object
            logger: Optional logger for debugging

        Returns:
            List of parsed JSON-LD objects
        """
        json_ld_data = []

        for script in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(script.string)

                # Handle both single objects and arrays
                if isinstance(data, list):
                    json_ld_data.extend(data)
                elif isinstance(data, dict):
                    json_ld_data.append(data)

            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                if logger:
                    logger.debug(f"Failed to parse JSON-LD: {e}")
                continue

        return json_ld_data

    @staticmethod
    def extract_from_json_ld(json_ld_data: List[Dict[str, Any]],
                            key: str,
                            types: Optional[List[str]] = None) -> Optional[Any]:
        """
        Extract a specific field from JSON-LD data.

        Args:
            json_ld_data: List of JSON-LD objects
            key: Key to extract (e.g., 'headline', 'author', 'datePublished')
            types: Filter by @type (e.g., ['Article', 'NewsArticle'])

        Returns:
            Extracted value or None
        """
        for data in json_ld_data:
            if not isinstance(data, dict):
                continue

            # Filter by type if specified
            if types:
                data_type = data.get('@type', '')
                if not any(t in data_type for t in types):
                    # Check @graph
                    if '@graph' in data:
                        for item in data['@graph']:
                            if isinstance(item, dict):
                                item_type = item.get('@type', '')
                                if any(t in item_type for t in types) and key in item:
                                    return item[key]
                    continue

            # Try direct key
            if key in data:
                return data[key]

            # Try @graph
            if '@graph' in data:
                for item in data['@graph']:
                    if isinstance(item, dict) and key in item:
                        return item[key]

        return None

    @staticmethod
    def extract_title(soup: BeautifulSoup) -> str:
        """
        Extract article title from HTML.

        Tries in order:
        1. og:title meta tag
        2. First h1 tag
        3. title tag
        4. Returns 'Unknown'

        Args:
            soup: BeautifulSoup object

        Returns:
            Article title
        """
        # Try og:title
        og_title = soup.find('meta', {'property': 'og:title'})
        if og_title and og_title.get('content'):
            return og_title['content'].strip()

        # Try h1
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()

        # Try title tag
        title_tag = soup.find('title')
        if title_tag:
            return title_tag.get_text().strip()

        return 'Unknown'

    @staticmethod
    def extract_author(soup: BeautifulSoup, json_ld_data: Optional[List[Dict]] = None) -> str:
        """
        Extract author from JSON-LD or meta tags.

        Args:
            soup: BeautifulSoup object
            json_ld_data: Optional JSON-LD data

        Returns:
            Author name or 'Unknown'
        """
        # Try JSON-LD first
        if json_ld_data:
            author = CommonParserMixin.extract_from_json_ld(
                json_ld_data,
                'author',
                types=['Article', 'NewsArticle', 'BlogPosting']
            )

            if author:
                # Handle different author formats
                if isinstance(author, dict):
                    name = author.get('name')
                    if name:
                        return name
                    # If author is just an @id reference, skip to HTML extraction
                elif isinstance(author, list):
                    if len(author) > 0:
                        first_author = author[0]
                        if isinstance(first_author, dict):
                            name = first_author.get('name')
                            if name:
                                return name
                            # If it's just @id reference, skip to HTML
                        elif isinstance(first_author, str):
                            return first_author
                elif isinstance(author, str):
                    return author

        # Try meta tags
        author_meta = soup.find('meta', {'name': 'author'}) or \
                     soup.find('meta', {'property': 'article:author'})
        if author_meta and author_meta.get('content'):
            return author_meta['content'].strip()

        # Try common CSS selectors
        for selector in ['.author', '.byline', '[rel="author"]', '.writer']:
            author_elem = soup.select_one(selector)
            if author_elem:
                return author_elem.get_text().strip()

        # Try elements with 'author' in class name
        author_elem = soup.find(['span', 'div', 'a'], class_=lambda x: x and 'author' in str(x).lower())
        if author_elem:
            return author_elem.get_text().strip()

        return 'Unknown'

    @staticmethod
    def extract_date(soup: BeautifulSoup, json_ld_data: Optional[List[Dict]] = None) -> str:
        """
        Extract publication date from JSON-LD or meta tags.

        Args:
            soup: BeautifulSoup object
            json_ld_data: Optional JSON-LD data

        Returns:
            Publication date or 'Unknown'
        """
        # Try JSON-LD first
        if json_ld_data:
            for key in ['datePublished', 'publishedDate', 'dateCreated']:
                date = CommonParserMixin.extract_from_json_ld(
                    json_ld_data,
                    key,
                    types=['Article', 'NewsArticle', 'BlogPosting']
                )
                if date:
                    return str(date)

        # Try meta tags
        date_meta = soup.find('meta', {'property': 'article:published_time'}) or \
                   soup.find('meta', {'name': 'publish-date'}) or \
                   soup.find('meta', {'name': 'date'}) or \
                   soup.find('meta', {'property': 'article:modified_time'})

        if date_meta and date_meta.get('content'):
            return date_meta['content'].strip()

        # Try time tag with datetime attribute
        time_tag = soup.find('time')
        if time_tag:
            if time_tag.has_attr('datetime'):
                return time_tag['datetime']
            return time_tag.get_text().strip()

        # Try common CSS selectors
        for selector in ['.date', '.published', '.post-date', '.timestamp']:
            date_elem = soup.select_one(selector)
            if date_elem:
                if date_elem.has_attr('datetime'):
                    return date_elem['datetime']
                return date_elem.get_text().strip()

        return 'Unknown'

    @staticmethod
    def extract_content(soup: BeautifulSoup,
                       selectors: Optional[List[tuple]] = None,
                       min_length: int = 100) -> str:
        """
        Extract main article content from HTML.

        Args:
            soup: BeautifulSoup object
            selectors: Optional list of (tag, attrs) tuples to try
            min_length: Minimum content length to accept

        Returns:
            Extracted content or "No content found"
        """
        # Default selectors if none provided
        if selectors is None:
            selectors = [
                ('article', {}),
                ('div', {'class': 'article-content'}),
                ('div', {'class': 'entry-content'}),
                ('div', {'class': 'post-content'}),
                ('div', {'class': 'article-body'}),
                ('main', {}),
                ('[role="main"]', {}),
            ]

        # Try each selector
        for tag_selector in selectors:
            if isinstance(tag_selector, tuple):
                tag, attrs = tag_selector
                if attrs:
                    container = soup.find(tag, attrs)
                else:
                    container = soup.find(tag) if isinstance(tag, str) else soup.select_one(tag)
            else:
                # String selector (CSS)
                container = soup.select_one(tag_selector)

            if not container:
                continue

            # Remove unwanted elements
            for unwanted in container.find_all(['script', 'style', 'nav', 'aside',
                                               'footer', 'header', 'form', 'iframe']):
                unwanted.decompose()

            # Extract paragraphs
            paragraphs = []
            seen_text = set()

            for elem in container.find_all(['p', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
                text = elem.get_text().strip()

                # Skip short or duplicate text
                if len(text) < 20 or text in seen_text:
                    continue

                # Skip unwanted phrases
                skip_phrases = ['subscribe', 'sign up', 'newsletter',
                               'advertisement', 'read more', 'click here']
                if any(skip in text.lower() for skip in skip_phrases):
                    continue

                seen_text.add(text)
                paragraphs.append(text)

            if paragraphs:
                content = '\n\n'.join(paragraphs)
                if len(content) >= min_length:
                    return content

        # Fallback: get all paragraphs from body
        paragraphs = []
        seen_text = set()

        for p in soup.find_all('p'):
            text = p.get_text().strip()
            if len(text) > 30 and text not in seen_text:
                seen_text.add(text)
                paragraphs.append(text)

        if paragraphs:
            content = '\n\n'.join(paragraphs[:50])  # Limit to first 50
            if len(content) >= min_length:
                return content

        return "No content found"

    @staticmethod
    def extract_description(soup: BeautifulSoup) -> str:
        """
        Extract page description from meta tags.

        Args:
            soup: BeautifulSoup object

        Returns:
            Description or empty string
        """
        desc_meta = soup.find('meta', {'name': 'description'}) or \
                   soup.find('meta', {'property': 'og:description'})

        if desc_meta and desc_meta.get('content'):
            return desc_meta['content'].strip()

        return ''
