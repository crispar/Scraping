"""
네이버 블로그 파서 (리팩토링 버전)

OOAD 원칙을 준수하며 기존 동작을 100% 유지합니다.
"""

import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import time
from datetime import datetime
import os
import logging
from typing import Dict, List, Any, Optional

from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter
from crawler.utils.file_manager import FileManager
from crawler.strategies.output_strategy import OutputStrategyFactory
from crawler.core.config import NaverBlogConfig
from crawler.constants import NaverBlogConstants, ParsingStatus, OutputConstants


class NaverBlogParser(BaseParser):
    """
    네이버 블로그 파서 클래스 (리팩토링)

    BaseParser를 상속하여 네이버 블로그 특화 파싱 기능을 구현합니다.
    """

    def __init__(self, max_workers: int = None, delay: float = None,
                 log_level: int = logging.INFO, format_preset: str = None):
        """
        네이버 블로그 파서 초기화

        Args:
            max_workers: 동시에 처리할 최대 스레드 수 (None이면 설정 기본값)
            delay: 요청 간 딜레이 (초) (None이면 설정 기본값)
            log_level: 로깅 레벨
            format_preset: 출력 포맷 프리셋 (무시됨, 호환성 유지용)
        """
        # 설정 로드
        self.config = NaverBlogConfig()
        if max_workers is not None:
            self.config.max_workers = max_workers
        if delay is not None:
            self.config.delay = delay

        # 베이스 클래스 초기화
        super().__init__(max_workers=self.config.max_workers, log_level=log_level)

        # Rate limiter 초기화
        self.rate_limiter = SimpleRateLimiter(delay=self.config.delay, logger=self.logger)

        # HTTP 헤더 설정
        self.headers = {
            'User-Agent': NaverBlogConstants.USER_AGENT
        }

        # 파일 매니저 초기화
        self.file_manager = FileManager(self.logger)

        # 출력 전략 초기화
        self.output_strategies = OutputStrategyFactory.create_naver_strategies(self.logger)

        self.logger.info(
            f"NaverBlogParser initialized with max_workers={self.config.max_workers}, "
            f"delay={self.config.delay}s"
        )

    def _get_logger_name(self) -> str:
        """로거 이름 반환"""
        return 'naver_blog_parser'

    def format_result(self, result: Dict[str, Any]) -> str:
        """
        네이버 블로그 파싱 결과를 포맷팅

        Args:
            result: 파싱 결과 딕셔너리

        Returns:
            포맷팅된 문자열
        """
        lines = []
        lines.append(f"Title: {result.get('title', 'N/A')}")
        lines.append(f"Author: {result.get('author', 'N/A')}")
        lines.append(f"Date: {result.get('date', 'N/A')}")
        lines.append(f"Category: {result.get('category', 'N/A')}")
        lines.append("\n" + "=" * 80 + "\n")
        lines.append("Content:\n")
        lines.append(result.get('content', 'N/A'))
        return "\n".join(lines)

    def get_real_url(self, url: str) -> str:
        """
        실제 블로그 컨텐츠 URL 가져오기

        Args:
            url: 블로그 포스트 URL

        Returns:
            실제 블로그 컨텐츠 URL
        """
        try:
            response = requests.get(url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')
            iframe = soup.find('iframe', id=NaverBlogConstants.IFRAME_ID)
            real_url = NaverBlogConstants.BASE_URL + iframe['src'] if iframe and iframe.get('src') else url
            self.logger.debug(f"Real URL for {url}: {real_url}")
            return real_url
        except Exception as e:
            self.logger.error(f"Error getting real URL for {url}: {str(e)}")
            return url

    def parse_content(self, soup: BeautifulSoup) -> str:
        """
        블로그 본문 내용 파싱

        Args:
            soup: 블로그 페이지의 BeautifulSoup 객체

        Returns:
            파싱된 블로그 본문 내용
        """
        try:
            content = []
            paragraphs = soup.find_all('p', {'id': re.compile(NaverBlogConstants.PARAGRAPH_ID_PATTERN)})
            self.logger.debug(f"Found {len(paragraphs)} paragraphs with id matching 'SE-'")

            if not paragraphs:
                # 백업 전략: 다른 방법으로 콘텐츠 찾기
                self.logger.debug("No paragraphs found with primary strategy, trying backup strategy")
                paragraphs = soup.find_all('div', {'class': re.compile(NaverBlogConstants.MAIN_CONTAINER_CLASS_PATTERN)})

            for p in paragraphs:
                text = p.get_text(strip=True)
                if text:
                    content.append(text)

            if not content:
                self.logger.debug("No content extracted from paragraphs, trying backup strategy")
                # Strategy 2: Main container text
                container = soup.find('div', {'class': re.compile(NaverBlogConstants.MAIN_CONTAINER_CLASS_PATTERN)})
                if container:
                    # Try to find text nodes within container
                    text_elements = container.find_all(['p', 'div', 'span'], class_=re.compile(r'se-text|se-module-text'))
                    for elem in text_elements:
                        text = elem.get_text(strip=True)
                        if text:
                            content.append(text)

            content_text = '\n'.join(content)
            self.logger.debug(f"Parsed content length: {len(content_text)} characters")
            return content_text
        except Exception as e:
            self.logger.error(f"Error parsing content: {str(e)}")
            return ""

    def parse_single(self, url: str) -> Dict[str, Any]:
        """
        단일 블로그 포스트 파싱 (BaseParser 인터페이스 구현)

        Args:
            url: 블로그 포스트 URL

        Returns:
            파싱된 블로그 정보
        """
        return self.parse_single_blog(url)

    def parse_single_blog(self, url: str) -> Dict[str, Any]:
        """
        단일 블로그 포스트 파싱 (기존 메서드명 유지)

        Args:
            url: 블로그 포스트 URL

        Returns:
            파싱된 블로그 정보
        """
        self.logger.info(f"Parsing blog: {url}")
        try:
            real_url = self.get_real_url(url)
            response = requests.get(real_url, headers=self.headers)
            soup = BeautifulSoup(response.text, 'html.parser')

            title = soup.find('title').text if soup.find('title') else "제목 없음"
            self.logger.debug(f"Found title: {title}")

            content = self.parse_content(soup)

            date_elem = soup.find('span', {'class': re.compile(NaverBlogConstants.DATE_CLASS_PATTERN)})
            date = date_elem.text.strip() if date_elem else None
            self.logger.debug(f"Found date: {date}")

            result = {
                'url': url,
                'title': title,
                'content': content,
                'date': date,
                'status': ParsingStatus.SUCCESS
            }

            self.logger.info(f"Successfully parsed blog: {url}")
            return result
        except Exception as e:
            self.logger.error(f"Error parsing blog {url}: {str(e)}")
            return {
                'url': url,
                'title': None,
                'content': None,
                'date': None,
                'status': f'{ParsingStatus.ERROR_PREFIX}{str(e)}'
            }

    def save_results(self, results: Any, output_dir: str) -> None:
        """
        파싱 결과 저장

        Args:
            results: 파싱 결과 (DataFrame 또는 리스트)
            output_dir: 결과 저장할 디렉토리
        """
        try:
            # 오래된 파일 자동 정리 (1일 이상)
            deleted_count = self.file_manager.delete_old_files(output_dir, days=1)
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old files from {output_dir}")

            self.logger.info(f"Saving parsing results to directory: {output_dir}")

            # DataFrame으로 변환
            if isinstance(results, list):
                df = pd.DataFrame(results)
            else:
                df = results

            # 파일 경로 생성
            csv_path = self.file_manager.build_output_path(
                output_dir, OutputConstants.PREFIX_NAVER, OutputConstants.EXT_CSV
            )
            txt_path = self.file_manager.build_output_path(
                output_dir, OutputConstants.PREFIX_NAVER, OutputConstants.EXT_TXT
            )

            # 각 전략으로 저장
            self.output_strategies['csv'].save(df, csv_path)
            self.output_strategies['txt'].save(df, txt_path)

            self.logger.info(f"파싱 완료! 결과가 다음 파일들에 저장되었습니다:")
            self.logger.info(f"CSV 파일: {csv_path}")
            self.logger.info(f"텍스트 파일: {txt_path}")

        except Exception as e:
            self.logger.error(f"Error saving results: {str(e)}")
            raise

    def parse_multiple(self, urls: List[str], output_dir: str) -> pd.DataFrame:
        """
        여러 블로그 포스트 파싱 (BaseParser 인터페이스 구현)

        Args:
            urls: 블로그 포스트 URL 리스트
            output_dir: 결과 저장 디렉토리

        Returns:
            파싱 결과 DataFrame
        """
        return self.parse_multiple_blogs(urls, output_dir)

    def parse_multiple_blogs(self, urls: List[str], output_dir: str = None, batch_size: int = None) -> pd.DataFrame:
        """
        여러 블로그 포스트 배치 파싱 (병렬 처리 및 메모리 효율적)

        Args:
            urls: 블로그 포스트 URL 리스트
            output_dir: 결과 저장할 디렉토리 (None이면 설정 기본값)
            batch_size: 배치 크기 (None이면 설정 기본값)

        Returns:
            파싱 결과 DataFrame
        """
        if output_dir is None:
            output_dir = self.config.output_dir
        if batch_size is None:
            batch_size = self.config.batch_size

        self.logger.info(f"Starting to parse {len(urls)} blogs with batch size {batch_size}")
        self.file_manager.ensure_directory(output_dir)

        all_results = []
        total_success = 0

        # 배치 처리로 메모리 효율성 확보
        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i+batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(urls) + batch_size - 1) // batch_size

            self.logger.info(f"Processing batch {batch_num}/{total_batches}: {len(batch_urls)} URLs")

            # 배치 내 병렬 처리 (ThreadPoolExecutor 사용)
            batch_results = []
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                # Future 객체 생성
                future_to_url = {executor.submit(self.parse_single_blog, url): url for url in batch_urls}
                
                for future in future_to_url:
                    url = future_to_url[future]
                    try:
                        result = future.result()
                        batch_results.append(result)
                        
                        if result['status'] == ParsingStatus.SUCCESS:
                            total_success += 1
                            
                        self.logger.info(f"처리 완료: {result['url']}")
                        
                        # Rate limiting (스레드 안전하게 적용하기 위해 간단한 sleep)
                        time.sleep(self.config.delay)
                        
                    except Exception as e:
                        self.logger.error(f"Exception parsing {url}: {e}")
                        batch_results.append({
                            'url': url,
                            'status': f'{ParsingStatus.ERROR_PREFIX}{str(e)}'
                        })

            all_results.extend(batch_results)

            # 중간 배치 저장 (메모리 관리)
            if i + batch_size < len(urls):
                self.logger.info(f"Saving intermediate batch {batch_num}")
                batch_df = pd.DataFrame(batch_results)

                # 배치 파일 경로
                batch_path = self.file_manager.build_output_path(
                    output_dir,
                    f"{OutputConstants.PREFIX_NAVER}_batch",
                    OutputConstants.EXT_CSV,
                    suffix=f"_{batch_num}"
                )

                # CSV로 저장
                self.output_strategies['csv'].save(batch_df, batch_path)
                self.logger.info(f"Saved batch to: {batch_path}")

        # 최종 결과
        df = pd.DataFrame(all_results)
        self.save_results(df, output_dir)

        self.logger.info(f"총 {len(urls)}개 중 {total_success}개 성공적으로 파싱됨")

        return df


# 하위 호환성을 위한 함수 (기존 코드에서 사용)
def delete_old_files(directory: str, days: int = 1, logger: Optional[logging.Logger] = None) -> int:
    """
    지정된 날짜 이전의 파일 삭제 (하위 호환성 함수)

    Args:
        directory: 파일을 삭제할 디렉토리
        days: 기준 날짜 (일)
        logger: 로거 객체 (선택)

    Returns:
        삭제된 파일 개수
    """
    from crawler.utils.file_manager import delete_old_files as delete_files
    return delete_files(directory, days, logger)


# 사용 예시 (기존과 동일하게 동작)
if __name__ == "__main__":
    from crawler.utils.logger_config import setup_logger

    # 메인 로거 설정
    main_logger = setup_logger('naver_blog_main')

    try:
        urls = [
            "https://blog.naver.com/jkhan012/224023701724"
        ]

        main_logger.info("Starting Naver Blog parsing process")
        parsed_blogs_folder = "parsed_blogs"

        # 오래된 파일 삭제 (로거 전달) - 기존과 동일
        delete_old_files(parsed_blogs_folder, logger=main_logger)

        # 파서 인스턴스 생성 및 파싱 실행 (기존과 동일한 방식)
        parser = NaverBlogParser(max_workers=3, delay=1)
        results = parser.parse_multiple_blogs(urls)

        success_count = len(results[results['status'] == ParsingStatus.SUCCESS])
        main_logger.info(f"\n총 {len(urls)}개 중 {success_count}개 성공적으로 파싱됨")

    except Exception as e:
        main_logger.error(f"Main process error: {str(e)}", exc_info=True)
