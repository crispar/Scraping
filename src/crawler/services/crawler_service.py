import logging
from dataclasses import dataclass
from typing import Dict, Any
from crawler.factory import ParserFactory

# 파서들이 본문을 못 찾았을 때 content 에 넣는 자리표시 문자열
NO_CONTENT_PLACEHOLDER = 'No content found'


def _has_body(raw_result: Dict[str, Any]) -> bool:
    """추출 결과에 사용자에게 보여줄 본문이 있는지 판정.

    레딧 링크/이미지 게시물처럼 본문은 비어 있어도 댓글이 결과인 경우는 본문 있음으로 본다.
    """
    content = (raw_result.get('content') or '').strip()
    if content and content != NO_CONTENT_PLACEHOLDER:
        return True
    return bool(raw_result.get('comments'))


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
            if status == 'success' and not _has_body(raw_result):
                # 파서는 페이지를 받았지만 본문 선택자가 맞지 않은 경우 — 성공으로
                # 보이면 빈 결과를 그대로 복사해 가게 되므로 실패로 알린다.
                return ExtractionResult(
                    success=False,
                    message="Extraction failed: 페이지는 받았지만 본문을 찾지 못했습니다 "
                            "(사이트 구조 변경 또는 로그인·봇 차단 페이지일 수 있음)",
                    formatted_text=formatted_text,
                    raw_result=raw_result,
                    platform=platform,
                )
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
