"""
공용 HTTP GET — 봇 차단 시 브라우저 TLS 지문으로 재시도

일부 사이트(openai·axios·engadget·gamespot·marktechpost 등, 2026-09-27 실측)는 헤더가 아니라
TLS/HTTP2 지문으로 봇을 가려 403 을 준다. 같은 요청을 curl_cffi 의 크롬 흉내(impersonate)로
보내면 통과한다. 그래서 1차 요청이 403 이면 한 번만 curl_cffi 로 재시도한다.

- Cloudflare JS 챌린지("Just a moment...")를 요구하는 사이트(nltimes, economist)는 이 방법으로도
  통과하지 못한다. 그런 곳은 실제 브라우저가 필요하다.
- curl_cffi 가 설치돼 있지 않거나 env HTTP_IMPERSONATE=0 이면 1차 응답을 그대로 돌려준다.
"""

import logging
import os
from typing import Any, Dict, Optional

import requests

from crawler.utils.proxy_config import ProxyConfig

logger = logging.getLogger('http_client')

# 이 상태 코드만 "봇 차단"으로 보고 재시도한다. 404·5xx 는 지문을 바꿔도 결과가 같다.
BLOCK_STATUSES = (403,)
IMPERSONATE_TARGET = 'chrome'


def _impersonation_enabled() -> bool:
    return os.environ.get('HTTP_IMPERSONATE', '1') not in ('0', 'false', 'False')


def _impersonated_get(url: str, timeout: float, proxies: Optional[Dict[str, str]]):
    """curl_cffi 로 크롬 TLS 지문 + 크롬 기본 헤더를 흉내 낸 GET.

    UA 등 헤더는 일부러 넘기지 않는다. 지문은 크롬인데 헤더가 다른 브라우저면 오히려 차단 신호가 된다.
    """
    from curl_cffi import requests as cffi_requests
    return cffi_requests.get(
        url, impersonate=IMPERSONATE_TARGET, timeout=timeout, proxies=proxies,
    )


def fetch(url: str, *, headers: Optional[Dict[str, str]] = None, timeout: float = 30,
          proxies: Optional[Dict[str, str]] = None, session: Any = None, **kwargs):
    """
    GET 요청. 1차 응답이 봇 차단(403)이면 브라우저 TLS 지문으로 한 번 재시도한다.

    Args:
        url: 요청 URL
        headers: 1차 요청 헤더
        timeout: 초 단위 타임아웃 (필수 — 없으면 응답 없는 서버에 워커가 영구히 묶인다)
        proxies: 프록시 dict (None 이면 ProxyConfig 기본값)
        session: 1차 요청에 쓸 세션(cloudscraper 등). None 이면 requests.get
        **kwargs: 1차 요청에 그대로 전달

    Returns:
        응답 객체 (requests.Response 또는 호환 객체). raise_for_status 는 호출부 책임.
    """
    if proxies is None:
        proxies = ProxyConfig.get_proxies()

    getter = session.get if session is not None else requests.get
    response = getter(url, headers=headers, timeout=timeout, proxies=proxies, **kwargs)
    if response.status_code not in BLOCK_STATUSES or not _impersonation_enabled():
        return response

    try:
        retried = _impersonated_get(url, timeout=timeout, proxies=proxies)
    except ImportError:
        logger.debug("curl_cffi 미설치 — 브라우저 지문 재시도 생략")
        return response
    except Exception as e:  # noqa: BLE001 - 재시도 실패는 1차 응답으로 보고
        logger.warning(f"Browser-fingerprint retry failed for {url}: {e}")
        return response

    logger.info(f"{response.status_code} → retried with {IMPERSONATE_TARGET} fingerprint: "
                f"{retried.status_code} ({url})")
    return retried if retried.status_code < 400 else response
