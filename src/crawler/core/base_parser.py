"""
추상 베이스 파서 클래스

모든 파서가 구현해야 하는 공통 인터페이스를 정의합니다.
Template Method Pattern을 사용하여 파싱 플로우를 표준화합니다.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import logging
import pandas as pd
import requests
from bs4 import BeautifulSoup
from crawler.utils.logger_config import setup_logger
from crawler.utils.proxy_config import ProxyConfig
from crawler.utils.article_extractor import ArticleParser


class BaseParser(ABC):
    """
    모든 파서의 추상 베이스 클래스

    Template Method Pattern을 사용하여 파싱 플로우를 정의합니다.
    하위 클래스는 추상 메서드를 구현해야 합니다.
    """

    def __init__(self, max_workers: int = 3, log_level: int = logging.INFO):
        """
        베이스 파서 초기화

        Args:
            max_workers: 동시 처리 스레드 수
            log_level: 로깅 레벨
        """
        self.max_workers = max_workers
        self.logger = setup_logger(self._get_logger_name(), level=log_level)
        self.logger.info(f"{self.__class__.__name__} initialized with max_workers={max_workers}")

    @abstractmethod
    def _get_logger_name(self) -> str:
        """
        로거 이름 반환

        Returns:
            로거 이름
        """
        pass

    @abstractmethod
    def parse_single(self, url: str) -> Dict[str, Any]:
        """
        단일 URL 파싱 (추상 메서드)

        Args:
            url: 파싱할 URL

        Returns:
            파싱 결과 딕셔너리 (반드시 'url'과 'status' 키 포함)
        """
        pass

    def format_result(self, result: Dict[str, Any]) -> str:
        """
        파싱 결과를 읽기 좋은 문자열로 포맷팅 (기본 구현)

        Args:
            result: 파싱 결과 딕셔너리

        Returns:
            포맷팅된 문자열
        """
        lines = []
        lines.append(f"Title: {result.get('title', 'N/A')}")
        lines.append(f"Source: {self._get_logger_name()}")
        lines.append(f"Author: {result.get('author', 'Unknown')}")
        lines.append(f"Date: {result.get('date', 'Unknown')}")
        lines.append("\n" + "=" * 80 + "\n")
        lines.append("Content:\n")
        lines.append(result.get('content', 'N/A'))
        return "\n".join(lines)

    def parse_multiple(self, urls: List[str], output_dir: str = None) -> pd.DataFrame:
        """
        여러 URL 파싱 (기본 구현)

        Args:
            urls: URL 리스트
            output_dir: 결과 저장 디렉토리 (선택사항)

        Returns:
            파싱 결과 DataFrame
        """
        results = []
        for url in urls:
            try:
                result = self.parse_single(url)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error parsing {url}: {e}")
                results.append(self.create_error_result(url, e))

        return pd.DataFrame(results)

    def save_results(self, results: Any, output_file: str) -> None:
        """
        파싱 결과 저장 (기본 구현)

        Args:
            results: 파싱 결과 (DataFrame 또는 리스트)
            output_file: 저장 파일 경로
        """
        if isinstance(results, pd.DataFrame):
            results.to_csv(output_file, index=False, encoding='utf-8-sig')
            self.logger.info(f"Results saved to {output_file}")
        elif isinstance(results, list):
            df = pd.DataFrame(results)
            df.to_csv(output_file, index=False, encoding='utf-8-sig')
            self.logger.info(f"Results saved to {output_file}")
        else:
            raise ValueError("Results must be DataFrame or list")

    def fetch_html(
        self,
        url: str,
        headers: Dict[str, str] = None,
        timeout: int = 30
    ) -> BeautifulSoup:
        """
        URL에서 HTML을 가져와 BeautifulSoup 객체 반환

        Args:
            url: 가져올 URL
            headers: HTTP 헤더
            timeout: 타임아웃 (초)

        Returns:
            BeautifulSoup 객체

        Raises:
            requests.RequestException: HTTP 요청 실패 시
        """
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        if headers:
            default_headers.update(headers)

        response = requests.get(
            url,
            headers=default_headers,
            timeout=timeout,
            proxies=ProxyConfig.get_proxies()
        )
        response.raise_for_status()

        return BeautifulSoup(response.text, 'html.parser')

    def parse_with_extractor(
        self,
        url: str,
        parser_name: str,
        default_author: str = 'Unknown',
        custom_content_selectors: List[tuple] = None,
        use_paragraphs: bool = False,
        headers: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        ArticleParser를 사용한 표준 파싱

        Args:
            url: 파싱할 URL
            parser_name: 파서 이름
            default_author: 기본 작성자 이름
            custom_content_selectors: 커스텀 컨텐츠 선택자
            use_paragraphs: 단락별 추출 여부
            headers: 추가 HTTP 헤더

        Returns:
            파싱 결과 딕셔너리
        """
        try:
            soup = self.fetch_html(url, headers=headers)

            return ArticleParser.parse_article(
                soup=soup,
                url=url,
                parser_name=parser_name,
                default_author=default_author,
                custom_content_selectors=custom_content_selectors,
                use_paragraphs=use_paragraphs,
                logger=self.logger
            )

        except requests.RequestException as e:
            self.logger.error(f"Error fetching {url}: {str(e)}")
            return {
                'status': 'error',
                'url': url,
                'error': str(e),
                'parser': parser_name
            }
        except Exception as e:
            self.logger.error(f"Unexpected error parsing {url}: {str(e)}")
            return {
                'status': 'error',
                'url': url,
                'error': str(e),
                'parser': parser_name
            }

    def get_success_count(self, results: pd.DataFrame) -> int:
        """
        성공한 파싱 결과 개수 반환

        Args:
            results: 파싱 결과 DataFrame

        Returns:
            성공 개수
        """
        return len(results[results['status'] == 'success'])

    def create_error_result(self, url: str, error: Exception) -> Dict[str, Any]:
        """
        에러 결과 객체 생성

        Args:
            url: 에러가 발생한 URL
            error: 예외 객체

        Returns:
            에러 정보가 담긴 딕셔너리
        """
        return {
            'url': url,
            'status': f'error: {str(error)}'
        }
