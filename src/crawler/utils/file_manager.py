"""
파일 관리 유틸리티 모듈

파일 정리, 경로 생성 등의 기능을 제공합니다.
"""

import os
from datetime import datetime, timedelta
from typing import Optional
import logging
from crawler.utils.logger_config import setup_logger
from crawler.core.config import FileConfig


class FileManager:
    """파일 관리 유틸리티 클래스"""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        FileManager 초기화

        Args:
            logger: 로거 객체 (선택)
        """
        self.logger = logger or setup_logger('file_manager')
        self.config = FileConfig()

    def delete_old_files(self, directory: str, days: int = None) -> int:
        """
        지정된 날짜 이전의 파일 삭제

        Args:
            directory: 파일을 삭제할 디렉토리
            days: 기준 날짜 (일), None이면 설정 기본값 사용

        Returns:
            삭제된 파일 개수
        """
        if days is None:
            days = self.config.cleanup_days

        self.logger.info(f"Cleaning up files older than {days} days in directory: {directory}")

        if not os.path.exists(directory):
            self.logger.warning(f"디렉토리가 존재하지 않습니다: {directory}")
            return 0

        now = datetime.now()
        cutoff = now - timedelta(days=days)
        self.logger.debug(f"Cutoff date: {cutoff}")

        deleted_count = 0
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path):
                file_creation_time = datetime.fromtimestamp(os.path.getctime(file_path))
                self.logger.debug(f"File: {filename}, Created: {file_creation_time}")
                if file_creation_time < cutoff:
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                        self.logger.info(f"삭제된 파일: {file_path}")
                    except Exception as e:
                        self.logger.error(f"Error deleting file {file_path}: {str(e)}")

        self.logger.info(f"총 {deleted_count}개 파일이 삭제되었습니다.")
        return deleted_count

    def ensure_directory(self, directory: str) -> None:
        """
        디렉토리가 존재하지 않으면 생성

        Args:
            directory: 생성할 디렉토리 경로
        """
        os.makedirs(directory, exist_ok=True)
        self.logger.debug(f"Directory ensured: {directory}")

    def generate_timestamp(self, format_type: str = 'full') -> str:
        """
        타임스탬프 생성

        Args:
            format_type: 'full' 또는 'date'

        Returns:
            타임스탬프 문자열
        """
        if format_type == 'date':
            return datetime.now().strftime(self.config.date_only_format)
        else:
            return datetime.now().strftime(self.config.timestamp_format)

    def build_output_path(self, output_dir: str, prefix: str, extension: str,
                         suffix: str = '') -> str:
        """
        출력 파일 경로 생성

        Args:
            output_dir: 출력 디렉토리
            prefix: 파일명 접두사
            extension: 파일 확장자 (점 포함)
            suffix: 추가 접미사 (선택)

        Returns:
            완전한 파일 경로
        """
        timestamp = self.generate_timestamp()
        filename = f"{prefix}{suffix}_{timestamp}{extension}"
        return os.path.join(output_dir, filename)


# 하위 호환성을 위한 함수
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
    manager = FileManager(logger)
    return manager.delete_old_files(directory, days)
