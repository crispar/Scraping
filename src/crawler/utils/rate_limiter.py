"""
Rate Limiter 모듈

Thread-safe한 rate limiting 기능을 제공합니다.
"""

import time
import random
import threading
import logging
from typing import Optional


class RateLimiter:
    """
    Thread-safe rate limiter

    여러 스레드에서 동시에 사용해도 안전하게 rate limiting을 수행합니다.
    """

    def __init__(self, min_delay: float = 1.0, max_delay: float = 2.0, logger: Optional[logging.Logger] = None):
        """
        RateLimiter 초기화

        Args:
            min_delay: 최소 지연 시간 (초)
            max_delay: 최대 지연 시간 (초)
            logger: 로거 객체 (선택)
        """
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.logger = logger
        self._lock = threading.Lock()
        self._last_request_time = 0

    def wait(self) -> None:
        """
        Rate limiting을 위한 대기

        Thread-safe하게 마지막 요청 시간을 추적하고 필요시 대기합니다.
        """
        with self._lock:
            current_time = time.time()
            elapsed = current_time - self._last_request_time

            if elapsed < self.min_delay:
                # 무작위 지연 시간 추가 (min_delay-max_delay초)
                wait_time = self.min_delay - elapsed + random.uniform(0, self.max_delay - self.min_delay)
                if self.logger:
                    self.logger.debug(f"Rate limiting: waiting for {wait_time:.2f}s")
                time.sleep(wait_time)

            self._last_request_time = time.time()

    def backoff(self, retry_count: int) -> float:
        """
        지수적 백오프 계산 및 대기

        Args:
            retry_count: 현재 재시도 횟수

        Returns:
            대기한 시간 (초)
        """
        wait_time = self.max_delay * (2 ** retry_count)
        if self.logger:
            self.logger.warning(f"Exponential backoff: waiting for {wait_time:.2f}s")
        time.sleep(wait_time)
        return wait_time


class SimpleRateLimiter:
    """
    간단한 rate limiter (단일 스레드용)

    네이버 블로그 파서처럼 고정 지연만 필요한 경우 사용합니다.
    """

    def __init__(self, delay: float = 1.0, logger: Optional[logging.Logger] = None):
        """
        SimpleRateLimiter 초기화

        Args:
            delay: 고정 지연 시간 (초)
            logger: 로거 객체 (선택)
        """
        self.delay = delay
        self.logger = logger

    def wait(self) -> None:
        """
        고정 시간 대기
        """
        if self.logger:
            self.logger.debug(f"Waiting for {self.delay}s")
        time.sleep(self.delay)
