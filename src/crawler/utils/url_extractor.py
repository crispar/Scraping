"""
URL Extractor 모듈

다양한 소스에서 URL을 추출하는 유틸리티 함수를 제공합니다.
"""

import re
import logging
from typing import List, Optional
from crawler.constants import RedditConstants
from crawler.utils.logger_config import setup_logger


class URLExtractor:
    """URL 추출 유틸리티 클래스"""

    @staticmethod
    def extract_reddit_urls(text: str) -> List[str]:
        """
        텍스트에서 Reddit URL을 추출하여 리스트로 반환

        Args:
            text: Reddit URL이 포함된 텍스트

        Returns:
            Reddit URL 리스트 (중복 제거됨)
        """
        # URL 추출
        urls = re.findall(RedditConstants.URL_PATTERN, text)

        # URL 중복 제거 및 정리
        unique_urls = list(dict.fromkeys(urls))

        return unique_urls

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit

    @staticmethod
    def extract_reddit_urls_from_file(file_path: str, logger: Optional[logging.Logger] = None) -> List[str]:
        """
        파일에서 Reddit URL 추출

        Args:
            file_path: 입력 파일 경로
            logger: 로거 객체 (선택)

        Returns:
            Reddit URL 리스트
        """
        # 로거가 없으면 새로 생성
        if logger is None:
            logger = setup_logger('reddit_url_extractor')

        try:
            # Check file size before reading
            import os
            file_size = os.path.getsize(file_path)
            if file_size > URLExtractor.MAX_FILE_SIZE:
                logger.error(f"File too large ({file_size} bytes). Maximum allowed: {URLExtractor.MAX_FILE_SIZE} bytes")
                return []

            logger.info(f"Extracting Reddit URLs from file: {file_path}")
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

            urls = URLExtractor.extract_reddit_urls(text)

            logger.info(f"추출된 Reddit URL ({len(urls)}개):")
            for i, url in enumerate(urls, 1):
                logger.info(f"{i}. {url}")

            return urls

        except Exception as e:
            logger.error(f"파일 읽기 오류: {str(e)}")
            return []
