"""URL validation utility."""

import ipaddress
import os
import socket
from urllib.parse import urlparse
from typing import Tuple, Optional


class URLValidator:
    """Shared URL validation logic for GUI and web app."""

    @staticmethod
    def validate(url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a URL.

        Returns:
            (is_valid, error_message_or_None)
        """
        if not url or not url.strip():
            return False, "Please enter a URL"

        url = url.strip()
        parsed = urlparse(url)

        if parsed.scheme not in ('http', 'https'):
            return False, "Please enter a valid URL starting with http:// or https://"

        if not parsed.netloc:
            return False, "Please enter a valid URL with a domain name"

        return True, None

    @staticmethod
    def check_public_host(url: str) -> Optional[str]:
        """
        URL 의 호스트가 사설·루프백·링크로컬 등 내부 주소로 해석되면 거부 사유를 반환.

        웹 API 는 사용자가 준 URL 을 서버가 대신 요청하므로, 막지 않으면 같은 망의
        VLM 서버·도커 호스트·클라우드 메타데이터를 외부에서 조회하는 통로(SSRF)가 된다.
        DNS 해석 실패는 여기서 판단하지 않는다(실제 요청이 실패로 보고함).
        리다이렉트로 내부 주소에 도달하는 경우까지 막지는 않는다.
        env ALLOW_PRIVATE_URLS=1 이면 검사를 끈다(사내망 페이지를 추출해야 할 때).

        Returns:
            거부 사유 문자열, 통과면 None
        """
        if os.environ.get('ALLOW_PRIVATE_URLS', '0') in ('1', 'true', 'True'):
            return None

        host = urlparse(url.strip()).hostname
        if not host:
            return None
        try:
            infos = socket.getaddrinfo(host, None)
        except (socket.gaierror, UnicodeError):
            return None

        for info in infos:
            address = ipaddress.ip_address(info[4][0].split('%', 1)[0])
            if not address.is_global:
                return f"내부 네트워크 주소는 추출할 수 없습니다: {host} ({address})"
        return None
