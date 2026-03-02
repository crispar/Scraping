import logging
from dataclasses import dataclass
from typing import Dict, Any
from crawler.factory import ParserFactory


@dataclass
class ExtractionResult:
    """Structured result from content extraction."""
    success: bool
    message: str
    formatted_text: str
    raw_result: Dict[str, Any]
    platform: str


class CrawlerService:
    """
    Service layer for crawler operations.
    Encapsulates business logic for platform detection and content extraction.
    """

    def __init__(self):
        self.logger = logging.getLogger('crawler_service')

    def detect_platform(self, url: str) -> str:
        return ParserFactory.detect_platform(url)

    def extract_content(self, url: str) -> ExtractionResult:
        """
        Extracts content from the given URL.

        Returns:
            ExtractionResult with success flag, message, formatted text,
            raw result dict, and detected platform.
        """
        platform = self.detect_platform(url)
        self.logger.info(f"Detected platform: {platform} for URL: {url}")

        try:
            parser = ParserFactory.create_parser(platform)
            raw_result = parser.parse_single(url)
            formatted_text = parser.format_result(raw_result)

            status = raw_result.get('status', '')
            if status == 'success':
                return ExtractionResult(
                    success=True,
                    message="Extraction completed successfully!",
                    formatted_text=formatted_text,
                    raw_result=raw_result,
                    platform=platform,
                )
            else:
                error_msg = raw_result.get('error', raw_result.get('status', 'Unknown error'))
                return ExtractionResult(
                    success=False,
                    message=f"Extraction failed: {error_msg}",
                    formatted_text=formatted_text,
                    raw_result=raw_result,
                    platform=platform,
                )

        except Exception as e:
            self.logger.error(f"Error during extraction: {str(e)}", exc_info=True)
            return ExtractionResult(
                success=False,
                message=f"Error: {str(e)}",
                formatted_text="",
                raw_result={
                    'url': url, 'status': 'error', 'title': 'Unknown',
                    'author': 'Unknown', 'date': 'Unknown', 'content': '',
                    'parser': platform,
                },
                platform=platform,
            )
