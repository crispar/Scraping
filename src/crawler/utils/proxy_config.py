"""
Proxy Configuration Utility

프록시 설정을 환경 변수 또는 직접 설정을 통해 관리합니다.
"""

import os
from typing import Optional, Dict


class ProxyConfig:
    """프록시 설정을 관리하는 유틸리티 클래스"""

    _proxy_settings: Optional[Dict[str, str]] = None

    @classmethod
    def get_proxies(cls) -> Optional[Dict[str, str]]:
        """
        프록시 설정을 가져옵니다.

        환경 변수 우선순위:
        1. HTTP_PROXY / HTTPS_PROXY (표준)
        2. http_proxy / https_proxy (소문자)

        Returns:
            프록시 딕셔너리 또는 None
            예: {'http': 'http://proxy.example.com:8080',
                 'https': 'http://proxy.example.com:8080'}
        """
        # 직접 설정된 프록시가 있으면 우선 사용
        if cls._proxy_settings is not None:
            return cls._proxy_settings if cls._proxy_settings else None

        # 환경 변수에서 프록시 설정 읽기
        proxies = {}

        # HTTP 프록시
        http_proxy = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
        if http_proxy:
            proxies['http'] = http_proxy

        # HTTPS 프록시
        https_proxy = os.environ.get('HTTPS_PROXY') or os.environ.get('https_proxy')
        if https_proxy:
            proxies['https'] = https_proxy

        return proxies if proxies else None

    @classmethod
    def set_proxy(cls, http_proxy: Optional[str] = None, https_proxy: Optional[str] = None):
        """
        프록시를 직접 설정합니다.

        Args:
            http_proxy: HTTP 프록시 URL (예: 'http://proxy.example.com:8080')
            https_proxy: HTTPS 프록시 URL (예: 'http://proxy.example.com:8080')

        Examples:
            >>> ProxyConfig.set_proxy('http://proxy.company.com:8080')
            >>> ProxyConfig.set_proxy(
            ...     http_proxy='http://proxy.company.com:8080',
            ...     https_proxy='http://proxy.company.com:8080'
            ... )
        """
        if http_proxy or https_proxy:
            cls._proxy_settings = {}
            if http_proxy:
                cls._proxy_settings['http'] = http_proxy
            if https_proxy:
                cls._proxy_settings['https'] = https_proxy
        else:
            cls._proxy_settings = {}

    @classmethod
    def clear_proxy(cls):
        """프록시 설정을 제거합니다."""
        cls._proxy_settings = None

    @classmethod
    def is_proxy_enabled(cls) -> bool:
        """프록시가 설정되어 있는지 확인합니다."""
        proxies = cls.get_proxies()
        return proxies is not None and len(proxies) > 0

    @classmethod
    def get_proxy_info(cls) -> str:
        """현재 프록시 설정 정보를 문자열로 반환합니다."""
        proxies = cls.get_proxies()
        if not proxies:
            return "No proxy configured"

        info = []
        for protocol, url in proxies.items():
            info.append(f"{protocol.upper()}: {url}")
        return ", ".join(info)
