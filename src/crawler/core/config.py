"""
설정 클래스 모듈

프로젝트의 모든 설정값을 중앙화하여 관리합니다.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RedditConfig:
    """Reddit 파서 설정"""
    max_workers: int = 3
    min_delay: float = 2.0
    max_delay: float = 4.0
    batch_size: int = 10
    max_retries: int = 3
    output_dir: str = 'parsed_reddit'
    max_comment_depth: int = 50  # 댓글 최대 깊이 제한


@dataclass
class NaverBlogConfig:
    """네이버 블로그 파서 설정"""
    max_workers: int = 3
    delay: float = 1.0
    output_dir: str = 'parsed_blogs'
    batch_size: int = 10  # 배치 크기 추가


@dataclass
class LogConfig:
    """로깅 설정"""
    log_dir: str = 'logs'
    date_format: str = '%Y-%m-%d %H:%M:%S'
    log_format: str = '[%(asctime)s] %(levelname)s [%(name)s.%(funcName)s:%(lineno)d] %(message)s'


@dataclass
class FileConfig:
    """파일 관련 설정"""
    timestamp_format: str = '%Y%m%d_%H%M%S'
    date_only_format: str = '%Y%m%d'
    encoding_csv: str = 'utf-8-sig'
    encoding_text: str = 'utf-8'
    cleanup_days: int = 1
