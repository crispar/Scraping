"""
Reddit 파서 (리팩토링 버전)

OOAD 원칙을 준수하며 기존 동작을 100% 유지합니다.
"""

import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import time
import threading
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urlparse
import os
import json
import random
import logging
from typing import Dict, List, Any, Optional

from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import RateLimiter
from crawler.utils.url_extractor import URLExtractor
from crawler.utils.file_manager import FileManager
from crawler.strategies.output_strategy import OutputStrategyFactory
from crawler.core.config import RedditConfig, FileConfig
from crawler.constants import RedditConstants, HTTPStatus, ParsingStatus, OutputConstants


class RedditParser(BaseParser):
    """
    Reddit 파서 클래스 (리팩토링)

    BaseParser를 상속하여 Reddit 특화 파싱 기능을 구현합니다.
    """

    def __init__(self, max_workers: int = None, min_delay: float = None,
                 max_delay: float = None, log_level: int = logging.INFO,
                 format_preset: str = None):
        """
        Reddit 파서 초기화

        Args:
            max_workers: 동시에 처리할 최대 스레드 수 (None이면 설정 기본값)
            min_delay: 요청 간 최소 딜레이 (초) (None이면 설정 기본값)
            max_delay: 요청 간 최대 딜레이 (초) (None이면 설정 기본값)
            log_level: 로깅 레벨
            format_preset: 출력 포맷 프리셋 (무시됨, 호환성 유지용)
        """
        # 설정 로드
        self.config = RedditConfig()
        if max_workers is not None:
            self.config.max_workers = max_workers
        if min_delay is not None:
            self.config.min_delay = min_delay
        if max_delay is not None:
            self.config.max_delay = max_delay

        # 베이스 클래스 초기화
        super().__init__(max_workers=self.config.max_workers, log_level=log_level)

        # Rate limiter 초기화
        self.rate_limiter = RateLimiter(
            min_delay=self.config.min_delay,
            max_delay=self.config.max_delay,
            logger=self.logger
        )

        # HTTP 헤더 설정
        self.headers = {
            'User-Agent': RedditConstants.USER_AGENT
        }

        # OAuth 설정 (env에 키가 있으면 oauth.reddit.com 사용, 없으면 기존 공개 .json 방식)
        self._client_id = os.environ.get('REDDIT_CLIENT_ID', '').strip()
        self._client_secret = os.environ.get('REDDIT_CLIENT_SECRET', '').strip()
        self._oauth_user_agent = os.environ.get(
            'REDDIT_USER_AGENT', 'linux:content-extractor:v2.0 (personal use)'
        )
        self._oauth_token: Optional[str] = None
        self._token_expiry: float = 0.0
        self._token_lock = threading.Lock()
        if self._client_id and self._client_secret:
            self.logger.info("Reddit OAuth credentials found, using oauth.reddit.com API")
        else:
            self.logger.warning(
                "No Reddit OAuth credentials (REDDIT_CLIENT_ID/REDDIT_CLIENT_SECRET), "
                "falling back to public .json endpoint (may be blocked with 403)"
            )

        # 파일 매니저 초기화
        self.file_manager = FileManager(self.logger)

        # 출력 전략 초기화
        self.output_strategies = OutputStrategyFactory.create_reddit_strategies(self.logger)

        self.logger.info(
            f"RedditParser initialized with max_workers={self.config.max_workers}, "
            f"min_delay={self.config.min_delay}s, max_delay={self.config.max_delay}s"
        )

    def _get_logger_name(self) -> str:
        """로거 이름 반환"""
        return 'reddit_parser'

    def _get_oauth_token(self) -> Optional[str]:
        """
        OAuth 액세스 토큰 반환 (캐시 사용, 만료 5분 전 갱신)

        Returns:
            액세스 토큰 문자열, 실패 또는 키 미설정 시 None
        """
        if not (self._client_id and self._client_secret):
            return None

        with self._token_lock:
            if self._oauth_token and time.time() < self._token_expiry - 300:
                return self._oauth_token

            self.logger.info("Requesting new Reddit OAuth token")
            response = requests.post(
                'https://www.reddit.com/api/v1/access_token',
                auth=(self._client_id, self._client_secret),
                data={'grant_type': 'client_credentials'},
                headers={'User-Agent': self._oauth_user_agent},
                timeout=15
            )
            if response.status_code != HTTPStatus.OK:
                self.logger.error(
                    f"Failed to get OAuth token: {response.status_code} {response.text[:200]}"
                )
                return None

            data = response.json()
            self._oauth_token = data.get('access_token')
            self._token_expiry = time.time() + data.get('expires_in', 3600)
            self.logger.info(f"OAuth token acquired (expires in {data.get('expires_in')}s)")
            return self._oauth_token

    def _fetch_post_json(self, url: str) -> requests.Response:
        """
        포스트 JSON 데이터 요청 (OAuth 우선, 미설정 시 공개 .json 폴백)

        Args:
            url: Reddit 포스트 URL

        Returns:
            requests.Response 객체
        """
        token = self._get_oauth_token()
        if token:
            # oauth.reddit.com으로 호스트 교체 후 인증 요청
            path = urlparse(url).path.rstrip('/')
            oauth_url = f"https://oauth.reddit.com{path}{RedditConstants.JSON_SUFFIX}"
            self.logger.debug(f"Requesting via OAuth API: {oauth_url}")
            return requests.get(
                oauth_url,
                headers={
                    'Authorization': f'bearer {token}',
                    'User-Agent': self._oauth_user_agent
                },
                params={'raw_json': 1},
                timeout=30
            )

        # 폴백: 기존 공개 .json 엔드포인트
        self.logger.debug(f"Requesting JSON data from {url}")
        return requests.get(f"{url}{RedditConstants.JSON_SUFFIX}", headers=self.headers, timeout=30)

    @staticmethod
    def _atom_text(entry: ET.Element, tag: str, ns: Dict[str, str]) -> str:
        """Atom 엔트리에서 태그 텍스트 추출"""
        el = entry.find(f'atom:{tag}', ns)
        return el.text if el is not None and el.text else ''

    @staticmethod
    def _html_to_text(html_str: str) -> str:
        """HTML 콘텐츠를 일반 텍스트로 변환 (본문 div.md 우선)"""
        soup = BeautifulSoup(html_str or '', 'html.parser')
        md = soup.find('div', class_='md')
        target = md if md else soup
        return target.get_text(separator='\n', strip=True)

    def _parse_via_rss(self, url: str) -> Dict[str, Any]:
        """
        RSS(Atom) 피드 폴백 파싱

        .json이 403으로 차단된 경우 사용. 첫 엔트리=포스트, 나머지=댓글.
        제한: 점수/추천비율 없음, 댓글 깊이·대댓글 구조 없음 (평면 목록).

        Args:
            url: Reddit 포스트 URL

        Returns:
            파싱된 포스트 데이터 (기존 결과 구조와 동일한 키)
        """
        rss_url = f"{url.rstrip('/')}/.rss"
        self.logger.info(f"Falling back to RSS feed: {rss_url}")
        response = requests.get(rss_url, headers=self.headers, timeout=30)
        if response.status_code != HTTPStatus.OK:
            raise Exception(f"RSS fallback failed: {response.status_code}")

        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        root = ET.fromstring(response.content)
        entries = root.findall('atom:entry', ns)
        if not entries:
            raise Exception("RSS fallback: no entries in feed")

        post = entries[0]

        def _author(entry: ET.Element) -> str:
            el = entry.find('atom:author/atom:name', ns)
            name = el.text if el is not None and el.text else ''
            return name[3:] if name.startswith('/u/') else name

        post_id = self._atom_text(post, 'id', ns)
        if post_id.startswith('t3_'):
            post_id = post_id[3:]

        post_html = self._atom_text(post, 'content', ns)
        content = self._html_to_text(post_html)

        # 링크 추출: 포스트 콘텐츠 내 외부 링크 (reddit 내부 링크 제외)
        links = []
        post_soup = BeautifulSoup(post_html, 'html.parser')
        for a in post_soup.find_all('a', href=True):
            href = a['href']
            if 'reddit.com' not in href and 'redd.it' not in href and href not in links:
                links.append(href)

        comments = []
        for entry in entries[1:]:
            comment_id = self._atom_text(entry, 'id', ns)
            if comment_id.startswith('t1_'):
                comment_id = comment_id[3:]
            comments.append({
                'comment_id': comment_id,
                'parent_id': None,
                'depth': 0,
                'author': _author(entry),
                'content': self._html_to_text(self._atom_text(entry, 'content', ns)),
                'timestamp': self._atom_text(entry, 'updated', ns),
                'score': None,
                'status': ParsingStatus.SUCCESS
            })

        result = {
            'url': url,
            'post_id': post_id,
            'title': self._atom_text(post, 'title', ns),
            'author': _author(post),
            'created_utc': self._atom_text(post, 'published', ns) or None,
            'content': content,
            'score': None,
            'upvote_ratio': None,
            'links': links,
            'comments': comments,
            'status': ParsingStatus.SUCCESS
        }

        self.logger.info(
            f"Successfully parsed post via RSS fallback: {url} "
            f"({len(comments)} comments, no scores/nesting)"
        )
        return result

    def format_result(self, result: Dict[str, Any]) -> str:
        """
        Reddit 파싱 결과를 포맷팅

        Args:
            result: 파싱 결과 딕셔너리

        Returns:
            포맷팅된 문자열
        """
        lines = self.build_header_lines(
            result,
            date=result.get('created_utc'),
            extra_lines=[
                f"Score: {result.get('score', 0)} | "
                f"Comments: {len(result.get('comments', []))}"
            ],
        )
        lines.append("\n" + "=" * 80 + "\n")
        lines.append("Content:\n")
        content = result.get('content', 'N/A')
        lines.append(content if content else "[No content]")

        # Comments
        comments = result.get('comments', [])
        if comments:
            lines.append("\n\n" + "=" * 80)
            lines.append(f"\nComments ({len(comments)}):\n")
            lines.append("=" * 80 + "\n")
            for i, comment in enumerate(comments, 1):
                indent = "  " * comment.get('depth', 0)
                lines.append(f"{indent}[{i}] {comment.get('author', 'Unknown')}")
                lines.append(f"{indent}    Score: {comment.get('score', 0)} | Depth: {comment.get('depth', 0)}")
                content = comment.get('content', '')
                if content:
                    lines.append(f"{indent}    {content}")
                lines.append("")
        
        return "\n".join(lines)

    def parse_single(self, url: str, max_retries: int = None) -> Dict[str, Any]:
        """
        단일 Reddit 포스트와 댓글들 파싱

        Args:
            url: Reddit 포스트 URL
            max_retries: 최대 재시도 횟수 (None이면 설정 기본값)

        Returns:
            파싱된 포스트 데이터
        """
        if max_retries is None:
            max_retries = self.config.max_retries

        return self.parse_single_post(url, max_retries)

    def parse_single_post(self, url: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        단일 Reddit 포스트와 댓글들 파싱 (기존 메서드명 유지)

        Args:
            url: Reddit 포스트 URL
            max_retries: 최대 재시도 횟수

        Returns:
            파싱된 포스트 데이터
        """
        self.logger.info(f"Parsing Reddit post: {url}")
        retry_count = 0

        while retry_count < max_retries:
            try:
                # rate limiting 대기
                self.rate_limiter.wait()

                # 첫 번째 요청: 포스트 데이터 (OAuth 우선, 폴백 시 공개 .json)
                response = self._fetch_post_json(url)

                if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                    retry_count += 1
                    wait_time = self.rate_limiter.backoff(retry_count)
                    self.logger.warning(
                        f"Rate limit hit (429), retry {retry_count}/{max_retries}, "
                        f"waiting for {wait_time}s..."
                    )
                    continue

                if response.status_code != HTTPStatus.OK:
                    # 토큰 만료/무효 가능성 → 캐시 비워서 재시도 시 새로 발급
                    if response.status_code in (401, 403) and self._oauth_token:
                        with self._token_lock:
                            self._oauth_token = None
                    # OAuth 키가 없고 공개 .json이 차단(403)된 경우 RSS 폴백
                    elif response.status_code == 403 and not (self._client_id and self._client_secret):
                        self.logger.warning("Public .json blocked (403), trying RSS fallback")
                        return self._parse_via_rss(url)
                    raise Exception(f"Failed to fetch data: {response.status_code}")

                data = response.json()
                if not data or len(data) < 2:
                    raise Exception("Invalid JSON response")

                # 포스트 데이터는 첫 번째 배열의 첫 번째 항목
                post_data = data[0]['data']['children'][0]['data']

                # 댓글 데이터는 두 번째 배열
                comments_data = data[1]['data']['children']

                # 포스트 내용 파싱
                content = post_data.get('selftext', '')
                title = post_data.get('title', '')
                author = post_data.get('author', '')
                created_utc = post_data.get('created_utc', '')
                score = post_data.get('score', 0)
                upvote_ratio = post_data.get('upvote_ratio', 0)

                self.logger.debug(f"Post title: {title}, author: {author}, score: {score}")

                # 링크 추출
                links = []
                if post_data.get('url'):
                    links.append(post_data['url'])

                # url 패턴 찾기
                url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
                additional_links = re.findall(url_pattern, content)
                links.extend(additional_links)

                self.logger.debug(f"Found {len(links)} links in post")

                # 댓글 파싱
                comments = []
                self._parse_comments_recursive(comments_data, comments)

                self.logger.debug(f"Parsed {len(comments)} comments")

                result = {
                    'url': url,
                    'post_id': post_data.get('id'),
                    'title': title,
                    'author': author,
                    'created_utc': datetime.fromtimestamp(created_utc).isoformat() if created_utc else None,
                    'content': content,
                    'score': score,
                    'upvote_ratio': upvote_ratio,
                    'links': links,
                    'comments': comments,
                    'status': ParsingStatus.SUCCESS
                }

                self.logger.info(f"Successfully parsed post: {url}")
                return result

            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = self.rate_limiter.backoff(retry_count)
                    self.logger.warning(
                        f"Error parsing {url} (attempt {retry_count}/{max_retries}): {str(e)}"
                    )
                    self.logger.warning(f"Retrying in {wait_time}s...")
                else:
                    self.logger.error(f"Failed to parse {url} after {max_retries} attempts: {str(e)}")
                    return {
                        'url': url,
                        'post_id': None,
                        'title': None,
                        'author': None,
                        'created_utc': None,
                        'content': None,
                        'score': None,
                        'upvote_ratio': None,
                        'links': None,
                        'comments': [],
                        'status': f'{ParsingStatus.ERROR_PREFIX}{str(e)}'
                    }

    def _parse_comments_recursive(self, comments_data: List, result: List,
                                  depth: int = 0, parent_id: Optional[str] = None) -> None:
        """
        댓글을 재귀적으로 파싱하여 중첩 구조를 보존

        Args:
            comments_data: 파싱할 댓글 데이터
            result: 결과를 저장할 리스트
            depth: 현재 댓글의 깊이
            parent_id: 부모 댓글의 ID
        """
        for comment in comments_data:
            if comment['kind'] == RedditConstants.COMMENT_KIND:  # 일반 댓글인 경우
                comment_data = comment['data']

                comment_obj = {
                    'comment_id': comment_data.get('id'),
                    'parent_id': parent_id,
                    'depth': depth,
                    'author': comment_data.get('author'),
                    'content': comment_data.get('body'),
                    'timestamp': datetime.fromtimestamp(comment_data.get('created_utc', 0)).isoformat(),
                    'score': comment_data.get('score'),
                    'status': ParsingStatus.SUCCESS
                }

                result.append(comment_obj)

                # 대댓글이 있는 경우 재귀적으로 처리 (깊이 제한)
                if depth < self.config.max_comment_depth:
                    if (comment_data.get('replies') and
                        isinstance(comment_data['replies'], dict) and
                        comment_data['replies'].get('data') and
                        comment_data['replies']['data'].get('children')):
                        self._parse_comments_recursive(
                            comment_data['replies']['data']['children'],
                            result,
                            depth + 1,
                            comment_data.get('id')
                        )
                elif depth == self.config.max_comment_depth:
                    self.logger.warning(
                        f"Max comment depth {self.config.max_comment_depth} reached. "
                        f"Skipping deeper nested comments."
                    )

    def parse_from_file(self, file_path: str, output_dir: str = None) -> Optional[pd.DataFrame]:
        """
        파일에서 URL을 추출하고 파싱 실행

        Args:
            file_path: 입력 파일 경로
            output_dir: 결과 저장 디렉토리 (None이면 설정 기본값)

        Returns:
            파싱 결과 DataFrame
        """
        if output_dir is None:
            output_dir = self.config.output_dir

        self.logger.info(f"Parsing Reddit posts from file: {file_path}")

        # URL 추출
        urls = URLExtractor.extract_reddit_urls_from_file(file_path, logger=self.logger)

        if not urls:
            self.logger.warning("파싱할 URL이 없습니다.")
            return None

        # 파싱 실행
        self.logger.info("\n파싱 시작...")
        return self.parse_multiple_posts(urls, output_dir)

    def parse_multiple(self, urls: List[str], output_dir: str) -> pd.DataFrame:
        """
        여러 Reddit 포스트 파싱 (BaseParser 인터페이스 구현)

        Args:
            urls: Reddit 포스트 URL 리스트
            output_dir: 결과 저장 디렉토리

        Returns:
            파싱 결과 DataFrame
        """
        return self.parse_multiple_posts(urls, output_dir)

    def parse_multiple_posts(self, urls: List[str], output_dir: str = None,
                            batch_size: int = None) -> pd.DataFrame:
        """
        여러 Reddit 포스트 파싱 (기존 메서드명 유지, 배치 처리 포함)

        Args:
            urls: Reddit 포스트 URL 리스트
            output_dir: 결과 저장 디렉토리
            batch_size: 한 번에 처리할 URL 수 (None이면 설정 기본값)

        Returns:
            파싱 결과 DataFrame
        """
        if output_dir is None:
            output_dir = self.config.output_dir
        if batch_size is None:
            batch_size = self.config.batch_size

        self.logger.info(f"Starting to parse {len(urls)} Reddit posts with batch size {batch_size}")
        self.file_manager.ensure_directory(output_dir)

        all_results = []
        total_success = 0

        # 배치 처리를 위한 URL 분할
        for i in range(0, len(urls), batch_size):
            batch_urls = urls[i:i+batch_size]
            self.logger.info(
                f"Processing batch {i//batch_size + 1}/{(len(urls)+batch_size-1)//batch_size}: "
                f"{len(batch_urls)} URLs"
            )

            # 병렬 처리로 성능 향상
            batch_results = []
            with ThreadPoolExecutor(max_workers=self.config.max_workers) as executor:
                # 병렬 실행
                future_to_url = {
                    executor.submit(self.parse_single_post, url, self.config.max_retries): url
                    for url in batch_urls
                }

                # 완료된 작업부터 처리
                for idx, future in enumerate(future_to_url, 1):
                    url = future_to_url[future]
                    try:
                        result = future.result()
                        batch_results.append(result)

                        # 진행 상황 출력
                        self.logger.info(f"처리 완료: {i+idx}/{len(urls)} - {url}")
                        self.logger.info(f"상태: {result['status']}")
                        if result['status'] == ParsingStatus.SUCCESS:
                            self.logger.info(f"제목: {result['title']}")
                            self.logger.info(f"댓글 수: {len(result['comments'])}")
                            total_success += 1
                        self.logger.info("-" * 50)

                    except Exception as e:
                        self.logger.error(f"Error processing {url}: {str(e)}")
                        batch_results.append(self.create_error_result(url, e))

            # 배치 간 대기 (rate limiting)
            if i + batch_size < len(urls):
                wait_time = random.uniform(self.config.min_delay, self.config.max_delay)
                self.logger.info(f"다음 배치까지 {wait_time:.1f}초 대기...")
                time.sleep(wait_time)

            all_results.extend(batch_results)

            # 메모리 관리를 위해 현재 배치 결과 저장
            if i + batch_size < len(urls):
                self.logger.info(f"Saving intermediate results after processing {i+len(batch_urls)}/{len(urls)} URLs")
                batch_df = pd.DataFrame(batch_results)

                # 배치 파일 경로 생성
                batch_path = self.file_manager.build_output_path(
                    output_dir,
                    OutputConstants.PREFIX_REDDIT_BATCH,
                    OutputConstants.EXT_CSV,
                    suffix=f"_{i//batch_size + 1}"
                )

                # CSV 전략으로 저장
                self.output_strategies['csv'].save(batch_df, batch_path)
                self.logger.info(f"Saved batch results to: {batch_path}")

        # 모든 결과를 DataFrame으로 변환
        df = pd.DataFrame(all_results)

        # 결과 저장
        self.save_results(df, output_dir)

        self.logger.info(f"총 파싱 결과: 성공 {total_success}개 / 전체 {len(urls)}개")

        return df

    def save_results(self, results: Any, output_dir: str) -> None:
        """
        파싱 결과를 다양한 형식으로 저장

        Args:
            results: 파싱 결과 (DataFrame 또는 리스트)
            output_dir: 저장 디렉토리
        """
        try:
            # 오래된 파일 자동 정리 (1일 이상)
            deleted_count = self.file_manager.delete_old_files(output_dir, days=1)
            if deleted_count > 0:
                self.logger.info(f"Cleaned up {deleted_count} old files from {output_dir}")

            self.logger.info("Saving final results")

            # DataFrame으로 변환
            if isinstance(results, list):
                df = pd.DataFrame(results)
            else:
                df = results

            # 파일 경로 생성
            csv_path = self.file_manager.build_output_path(
                output_dir, OutputConstants.PREFIX_REDDIT, OutputConstants.EXT_CSV
            )
            json_path = self.file_manager.build_output_path(
                output_dir, OutputConstants.PREFIX_REDDIT, OutputConstants.EXT_JSON
            )
            txt_path = self.file_manager.build_output_path(
                output_dir, OutputConstants.PREFIX_REDDIT, OutputConstants.EXT_TXT
            )
            simple_path = self.file_manager.build_output_path(
                output_dir, OutputConstants.PREFIX_REDDIT_SIMPLE, OutputConstants.EXT_TXT
            )

            # 각 전략으로 저장
            self.output_strategies['csv'].save(df, csv_path)
            self.output_strategies['json'].save(df, json_path)
            self.output_strategies['txt'].save(df, txt_path)
            self.output_strategies['simple'].save(df, simple_path)

            self.logger.info(f"\n파싱 완료! 결과가 다음 파일들에 저장되었습니다:")
            self.logger.info(f"CSV 파일: {csv_path}")
            self.logger.info(f"텍스트 파일: {txt_path}")
            self.logger.info(f"JSON 파일: {json_path}")
            self.logger.info(f"간단한 형식: {simple_path}")

        except Exception as e:
            self.logger.error(f"Error saving results: {str(e)}")
            raise

    def save_simple_format(self, results: Any, output_path: str) -> None:
        """
        결과를 제목, URL, 본문, 댓글 순으로 저장 (하위 호환성 메서드)

        Args:
            results: 파싱 결과 데이터 (리스트 또는 DataFrame)
            output_path: 저장할 파일 경로
        """
        self.output_strategies['simple'].save(results, output_path)

    # 하위 호환성을 위한 정적 메서드 유지
    @staticmethod
    def extract_reddit_urls(text: str) -> List[str]:
        """
        텍스트에서 Reddit URL을 추출하여 리스트로 반환 (하위 호환성)

        Args:
            text: Reddit URL이 포함된 텍스트

        Returns:
            Reddit URL 리스트
        """
        return URLExtractor.extract_reddit_urls(text)

    @staticmethod
    def extract_urls_from_file(file_path: str, logger: Optional[logging.Logger] = None) -> List[str]:
        """
        파일에서 Reddit URL 추출 (하위 호환성)

        Args:
            file_path: 입력 파일 경로
            logger: 로거 객체 (선택)

        Returns:
            Reddit URL 리스트
        """
        return URLExtractor.extract_reddit_urls_from_file(file_path, logger)


# 사용 예시 (기존과 동일하게 동작)
if __name__ == "__main__":
    from crawler.utils.logger_config import setup_logger

    # 메인 로거 설정
    main_logger = setup_logger('reddit_main')

    try:
        # 입력 파일 경로 설정
        input_file = 'input.txt'  # URL이 포함된 텍스트 파일

        main_logger.info("Starting Reddit parsing process")

        # 파서 인스턴스 생성 (기존과 동일한 방식)
        parser = RedditParser(max_workers=3, min_delay=2, max_delay=4)

        # 파일에서 URL 추출 및 파싱 실행
        results = parser.parse_from_file(input_file)

        if results is not None:
            success_count = len(results[results['status'] == ParsingStatus.SUCCESS])
            main_logger.info(f"\n총 파싱 결과: 성공 {success_count}개 / 전체 {len(results)}개")

    except Exception as e:
        main_logger.error(f"Main process error: {str(e)}", exc_info=True)
