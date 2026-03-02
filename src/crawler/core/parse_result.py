"""
Parse Result Data Classes

Provides standardized result structures for parser outputs.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass
class ParseResult:
    """
    Standardized result structure for parser outputs.

    This ensures consistency across all 42 parsers and provides
    type safety and auto-completion support.

    Attributes:
        url: The URL that was parsed
        status: Parse status ('success' or 'error')
        title: Article/post title
        author: Author name
        date: Publication date
        content: Main content text
        parser: Name of the parser used
        timestamp: When the parsing was performed
        description: Optional meta description
        error: Optional error message (when status='error')
        metadata: Optional additional metadata
    """
    url: str
    status: str
    title: str
    author: str
    date: str
    content: str
    parser: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    description: str = ""
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary format (backward compatible).

        Returns:
            Dictionary representation
        """
        result = asdict(self)
        # Remove None values for backward compatibility
        return {k: v for k, v in result.items() if v is not None}

    @classmethod
    def success(cls,
                url: str,
                title: str,
                author: str,
                date: str,
                content: str,
                parser: str,
                description: str = "",
                metadata: Optional[Dict[str, Any]] = None) -> 'ParseResult':
        """
        Create a successful parse result.

        Args:
            url: The URL that was parsed
            title: Article title
            author: Author name
            date: Publication date
            content: Main content
            parser: Parser name
            description: Optional meta description
            metadata: Optional additional data

        Returns:
            ParseResult with status='success'
        """
        return cls(
            url=url,
            status='success',
            title=title,
            author=author,
            date=date,
            content=content,
            parser=parser,
            description=description,
            metadata=metadata
        )

    @classmethod
    def error(cls,
              url: str,
              error_message: str,
              parser: str) -> 'ParseResult':
        """
        Create an error parse result.

        Args:
            url: The URL that failed
            error_message: Error description
            parser: Parser name

        Returns:
            ParseResult with status='error'
        """
        return cls(
            url=url,
            status='error',
            title='Error',
            author='Unknown',
            date='Unknown',
            content=f"Failed to parse: {error_message}",
            parser=parser,
            error=error_message
        )


class ParseResultBuilder:
    """
    Builder pattern for creating ParseResult objects.

    Provides a fluent interface for constructing results step-by-step.

    Example:
        result = (ParseResultBuilder(url, parser_name)
                  .with_title(title)
                  .with_author(author)
                  .with_content(content)
                  .build())
    """

    def __init__(self, url: str, parser: str):
        """
        Initialize builder with required fields.

        Args:
            url: The URL being parsed
            parser: Parser name
        """
        self._url = url
        self._parser = parser
        self._title = 'Unknown'
        self._author = 'Unknown'
        self._date = 'Unknown'
        self._content = ''
        self._description = ''
        self._metadata = None

    def with_title(self, title: str) -> 'ParseResultBuilder':
        """Set title."""
        self._title = title or 'Unknown'
        return self

    def with_author(self, author: str) -> 'ParseResultBuilder':
        """Set author."""
        self._author = author or 'Unknown'
        return self

    def with_date(self, date: str) -> 'ParseResultBuilder':
        """Set publication date."""
        self._date = date or 'Unknown'
        return self

    def with_content(self, content: str) -> 'ParseResultBuilder':
        """Set main content."""
        self._content = content or ''
        return self

    def with_description(self, description: str) -> 'ParseResultBuilder':
        """Set meta description."""
        self._description = description or ''
        return self

    def with_metadata(self, metadata: Dict[str, Any]) -> 'ParseResultBuilder':
        """Set additional metadata."""
        self._metadata = metadata
        return self

    def build(self) -> ParseResult:
        """
        Build the ParseResult object.

        Returns:
            Constructed ParseResult with status='success'
        """
        return ParseResult.success(
            url=self._url,
            title=self._title,
            author=self._author,
            date=self._date,
            content=self._content,
            parser=self._parser,
            description=self._description,
            metadata=self._metadata
        )

    def build_error(self, error_message: str) -> ParseResult:
        """
        Build an error result.

        Args:
            error_message: Error description

        Returns:
            ParseResult with status='error'
        """
        return ParseResult.error(
            url=self._url,
            error_message=error_message,
            parser=self._parser
        )
