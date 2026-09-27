"""http_client.fetch: 봇 차단(403)이면 브라우저 TLS 지문(curl_cffi)으로 한 번 더 시도한다.

openai·axios·engadget·gamespot·marktechpost 는 헤더가 아니라 TLS 지문으로 막는다
(2026-09-27 실측: 같은 헤더의 requests 는 403, curl_cffi impersonate='chrome' 은 200).
"""

import pytest

import crawler.utils.http_client as http_client
from crawler.factory import ParserFactory


class _Resp:
    def __init__(self, status, text='<html><title>ok</title></html>'):
        self.status_code = status
        self.text = text
        self.content = text.encode()
        self.encoding = 'utf-8'

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests
            raise requests.HTTPError(f'{self.status_code} Forbidden')


@pytest.fixture
def transports(monkeypatch):
    calls = {'plain': 0, 'impersonate': 0}

    def install(plain_status, impersonate_status=200):
        def plain(url, **kw):
            calls['plain'] += 1
            assert kw.get('timeout'), 'timeout required'
            return _Resp(plain_status)

        def impersonate(url, **kw):
            calls['impersonate'] += 1
            assert kw.get('timeout'), 'timeout required'
            return _Resp(impersonate_status, '<html><title>via cffi</title></html>')

        monkeypatch.setattr(http_client.requests, 'get', plain)
        monkeypatch.setattr(http_client, '_impersonated_get', impersonate)
        return calls
    return install


def test_blocked_request_is_retried_with_browser_fingerprint(transports):
    calls = transports(403)
    resp = http_client.fetch('https://blocked.example/a', timeout=10)
    assert resp.status_code == 200 and 'via cffi' in resp.text
    assert calls == {'plain': 1, 'impersonate': 1}


def test_ok_request_does_not_touch_fallback(transports):
    calls = transports(200)
    assert http_client.fetch('https://ok.example/a', timeout=10).status_code == 200
    assert calls['impersonate'] == 0


def test_non_block_errors_are_not_retried(transports):
    calls = transports(404)
    assert http_client.fetch('https://gone.example/a', timeout=10).status_code == 404
    assert calls['impersonate'] == 0


def test_fallback_can_be_disabled(transports, monkeypatch):
    monkeypatch.setenv('HTTP_IMPERSONATE', '0')
    calls = transports(403)
    assert http_client.fetch('https://blocked.example/a', timeout=10).status_code == 403
    assert calls['impersonate'] == 0


def test_session_primary_is_used_when_given(transports):
    """cloudscraper 세션을 쓰는 파서(axios·economist)도 같은 폴백을 탄다."""
    calls = transports(200)

    class Session:
        used = 0

        def get(self, url, **kw):
            Session.used += 1
            return _Resp(403)

    resp = http_client.fetch('https://blocked.example/a', timeout=10, session=Session())
    assert Session.used == 1 and calls['plain'] == 0 and calls['impersonate'] == 1
    assert resp.status_code == 200


@pytest.mark.parametrize('name', ['openai', 'engadget', 'gamespot', 'marktechpost', 'axios'])
def test_blocked_parsers_route_through_fallback(name, transports, monkeypatch):
    """TLS 지문으로 막히는 사이트의 파서가 실제로 공용 fetch 를 거치는지."""
    transports(403)
    parser = ParserFactory.create_parser(name)
    if hasattr(parser, 'rate_limiter'):
        monkeypatch.setattr(parser.rate_limiter, 'wait', lambda *a, **k: None)
    if hasattr(parser, 'scraper'):
        monkeypatch.setattr(parser.scraper, 'get', lambda *a, **k: _Resp(403))
    result = parser.parse_single(f'https://www.{name}.example/article')
    assert result['status'] == 'success', result.get('error')
    assert result['title'] == 'via cffi'
