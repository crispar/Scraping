"""Test cases for the Flask web application"""

import json
import time
import pytest
from web_app import create_app
from crawler.factory import ParserFactory
from crawler.services.crawler_service import CrawlerService, ExtractionResult
from crawler.utils.url_validator import URLValidator


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestWebAppBasic:

    def test_index_page_loads(self, client):
        response = client.get('/')
        assert response.status_code == 200
        assert b'Content Extractor' in response.data

    def test_health_check(self, client):
        response = client.get('/api/health')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'healthy'

    def test_get_available_parsers(self, client):
        response = client.get('/api/parsers')
        assert response.status_code == 200
        data = json.loads(response.data)
        parsers = data['parsers']
        assert 'reddit' in parsers
        assert 'generic' in parsers
        # Should match the actual factory count
        assert len(parsers) == len(ParserFactory.get_available_parsers())


class TestPlatformDetection:

    def test_detect_reddit(self, client):
        response = client.post('/api/detect', json={'url': 'https://www.reddit.com/r/test/comments/abc123/test_post/'})
        assert response.status_code == 200
        assert json.loads(response.data)['platform'] == 'reddit'

    def test_detect_naver(self, client):
        response = client.post('/api/detect', json={'url': 'https://blog.naver.com/user/123456'})
        assert response.status_code == 200
        assert json.loads(response.data)['platform'] == 'naver'

    def test_detect_techcrunch(self, client):
        response = client.post('/api/detect', json={'url': 'https://techcrunch.com/2025/01/01/test-article/'})
        assert response.status_code == 200
        assert json.loads(response.data)['platform'] == 'techcrunch'

    def test_detect_generic_for_unknown_domain(self, client):
        response = client.post('/api/detect', json={'url': 'https://unknown-site.com/article'})
        assert response.status_code == 200
        assert json.loads(response.data)['platform'] == 'generic'

    def test_detect_missing_url(self, client):
        response = client.post('/api/detect', json={})
        assert response.status_code == 400

    def test_detect_invalid_url(self, client):
        response = client.post('/api/detect', json={'url': 'not-a-url'})
        assert response.status_code == 400


class TestExtraction:

    def test_extract_missing_url(self, client):
        response = client.post('/api/extract', json={})
        assert response.status_code == 400

    def test_extract_invalid_url(self, client):
        response = client.post('/api/extract', json={'url': 'not-a-url'})
        assert response.status_code == 400

    @pytest.fixture
    def stub_service(self, monkeypatch):
        """추출기를 고정 결과로 대체 — 네트워크 없이 API 계약만 검증한다."""
        def fake_extract(self, url):
            return ExtractionResult(
                success=True,
                message="Extraction completed successfully!",
                formatted_text="Title: T\nURL: " + url + "\nContent:\nbody",
                raw_result={
                    'url': url, 'title': 'T', 'author': 'A', 'date': 'D',
                    'content': 'body', 'status': 'success',
                },
                platform='generic',
            )
        monkeypatch.setattr(CrawlerService, 'extract_content', fake_extract)

    @staticmethod
    def _assert_result_structure(data):
        assert 'success' in data
        assert 'platform' in data
        assert 'result' in data
        if data['success']:
            result = data['result']
            for key in ('title', 'content', 'author', 'date', 'url'):
                assert key in result

    @staticmethod
    def _poll(client, job_id, attempts=50):
        """비동기 작업이 끝날 때까지 폴링 (백그라운드 스레드 완료 대기)."""
        for _ in range(attempts):
            response = client.get(f'/api/extract/result/{job_id}')
            assert response.status_code == 200
            data = json.loads(response.data)
            if data['status'] != 'pending':
                return data
            time.sleep(0.05)
        pytest.fail(f"job {job_id} did not finish in time")

    def test_extract_sync_returns_proper_structure(self, client, stub_service):
        """sync=true 하위호환 경로는 예전처럼 200 + 결과를 바로 돌려준다."""
        response = client.post('/api/extract', json={
            'url': 'https://example.com/post', 'sync': True,
        })
        assert response.status_code == 200
        self._assert_result_structure(json.loads(response.data))

    def test_extract_async_returns_job_then_result(self, client, stub_service):
        """기본 경로는 202 + job_id 를 주고, 폴링으로 같은 구조의 결과를 받는다."""
        response = client.post('/api/extract', json={'url': 'https://example.com/post'})
        assert response.status_code == 202
        job = json.loads(response.data)
        assert job['status'] == 'pending'
        assert job['job_id']

        data = self._poll(client, job['job_id'])
        assert data['status'] == 'done'
        self._assert_result_structure(data)
        assert data['result']['url'] == 'https://example.com/post'

    def test_extract_async_reports_failure(self, client, monkeypatch):
        """추출 중 예외가 나면 job 이 error 상태로 마감돼야 한다 (무한 pending 금지)."""
        def boom(self, url):
            raise RuntimeError('extractor exploded')
        monkeypatch.setattr(CrawlerService, 'extract_content', boom)

        response = client.post('/api/extract', json={'url': 'https://example.com/post'})
        assert response.status_code == 202
        data = self._poll(client, json.loads(response.data)['job_id'])
        assert data['status'] == 'error'
        assert 'extractor exploded' in data['message']

    def test_extract_result_unknown_job(self, client):
        response = client.get('/api/extract/result/does-not-exist')
        assert response.status_code == 404
        assert json.loads(response.data)['status'] == 'not_found'


class TestURLValidator:
    """Unit tests for the shared URLValidator"""

    def test_valid_https_url(self):
        is_valid, error = URLValidator.validate('https://example.com/page')
        assert is_valid is True
        assert error is None

    def test_valid_http_url(self):
        is_valid, error = URLValidator.validate('http://example.com')
        assert is_valid is True
        assert error is None

    def test_empty_string(self):
        is_valid, error = URLValidator.validate('')
        assert is_valid is False
        assert error is not None

    def test_none_value(self):
        is_valid, error = URLValidator.validate(None)
        assert is_valid is False

    def test_no_scheme(self):
        is_valid, error = URLValidator.validate('example.com/page')
        assert is_valid is False

    def test_ftp_scheme_rejected(self):
        is_valid, error = URLValidator.validate('ftp://example.com/file')
        assert is_valid is False

    def test_whitespace_trimmed(self):
        is_valid, error = URLValidator.validate('  https://example.com  ')
        assert is_valid is True


class TestExtractionResult:
    """Test ExtractionResult dataclass"""

    def test_extraction_result_fields(self):
        result = ExtractionResult(
            success=True,
            message="OK",
            formatted_text="content",
            raw_result={'url': 'http://test.com', 'status': 'success'},
            platform='generic',
        )
        assert result.success is True
        assert result.platform == 'generic'
        assert result.raw_result['status'] == 'success'

    @pytest.mark.network
    def test_service_returns_extraction_result(self):
        service = CrawlerService()
        result = service.extract_content('https://blog.samaltman.com/how-to-invest-in-startups')
        assert isinstance(result, ExtractionResult)
        assert isinstance(result.success, bool)
        assert isinstance(result.raw_result, dict)
        assert result.platform == 'samaltman'


class TestFrontendBugFixes:
    """Verify fixes for flickering and URL persistence bugs in index.html"""

    def test_index_page_contains_goBack_with_resetState(self, client):
        """goBack() must call resetState() to clear previous URL and results"""
        response = client.get('/')
        html = response.data.decode('utf-8')
        assert 'function resetState()' in html, "resetState() function must exist"
        assert 'function goBack()' in html, "goBack() function must exist"
        # goBack must call resetState
        goback_start = html.find('function goBack()')
        goback_body = html[goback_start:html.find('\n    }', goback_start) + 6]
        assert 'resetState()' in goback_body, "goBack() must call resetState()"

    def test_resetState_clears_url_input(self, client):
        """resetState() must clear the URL input field"""
        response = client.get('/')
        html = response.data.decode('utf-8')
        reset_start = html.find('function resetState()')
        reset_end = html.find('\n    }', reset_start) + 6
        reset_body = html[reset_start:reset_end]
        assert "urlInput.value = ''" in reset_body, "resetState must clear urlInput"

    def test_resetState_clears_platform_tag(self, client):
        """resetState() must hide the platform detection tag"""
        response = client.get('/')
        html = response.data.decode('utf-8')
        reset_start = html.find('function resetState()')
        reset_end = html.find('\n    }', reset_start) + 6
        reset_body = html[reset_start:reset_end]
        assert "platformTag.style.display = 'none'" in reset_body

    def test_resetState_clears_result_data(self, client):
        """resetState() must clear all result fields"""
        response = client.get('/')
        html = response.data.decode('utf-8')
        reset_start = html.find('function resetState()')
        reset_end = html.find('\n    }', reset_start) + 6
        reset_body = html[reset_start:reset_end]
        assert "resultText.value = ''" in reset_body
        assert "resultJson.textContent = 'No data yet.'" in reset_body

    def test_resetState_clears_info_fields(self, client):
        """resetState() must reset all info grid fields"""
        response = client.get('/')
        html = response.data.decode('utf-8')
        for field in ['info-title', 'info-author', 'info-date',
                      'info-parser', 'info-status', 'info-url']:
            assert f"getElementById('{field}').textContent = '-'" in html, \
                f"resetState must reset {field}"

    def test_hero_animation_only_on_initial_load(self, client):
        """hero__content animation must only play on initial load, not on goBack()"""
        response = client.get('/')
        html = response.data.decode('utf-8')
        # Initial HTML has the animation class
        assert 'hero__content hero__content--initial' in html, \
            "hero__content must have --initial class for first load animation"
        # goBack removes the animation class to prevent flicker
        assert "classList.remove('hero__content--initial')" in html, \
            "goBack must remove animation class to prevent re-triggering"
        # Static .hero__content should NOT have animation
        assert '.hero__content {' in html
        # The animation should only be on the --initial modifier
        assert '.hero__content--initial' in html

    def test_hero_content_no_static_animation(self, client):
        """The base .hero__content class must not have animation property"""
        response = client.get('/')
        html = response.data.decode('utf-8')
        # Find .hero__content CSS block (not --initial)
        hero_css_start = html.find('.hero__content {')
        hero_css_end = html.find('}', hero_css_start) + 1
        hero_css = html[hero_css_start:hero_css_end]
        assert 'animation' not in hero_css, \
            "Base .hero__content must not have animation (causes flicker on goBack)"

    def test_error_retry_uses_separate_function(self, client):
        """Error retry button must use retryFromError(), not goBack()"""
        response = client.get('/')
        html = response.data.decode('utf-8')
        assert 'function retryFromError()' in html, \
            "retryFromError() function must exist"
        assert 'onclick="retryFromError()"' in html, \
            "Error retry button must call retryFromError()"

    def test_error_retry_preserves_url(self, client):
        """retryFromError() must NOT clear the URL (user wants to retry same URL)"""
        response = client.get('/')
        html = response.data.decode('utf-8')
        retry_start = html.find('function retryFromError()')
        retry_end = html.find('\n    }', retry_start) + 6
        retry_body = html[retry_start:retry_end]
        assert 'resetState' not in retry_body, \
            "retryFromError must NOT call resetState (preserves URL for retry)"


class TestServiceIntegrity:
    """Verify CrawlerService behavior matches ParserFactory"""

    def test_detect_platform_matches_factory(self):
        service = CrawlerService()
        test_cases = [
            ('https://www.reddit.com/r/test', 'reddit'),
            ('https://techcrunch.com/article', 'techcrunch'),
            ('https://blog.naver.com/user/123', 'naver'),
            ('https://unknown.com/page', 'generic'),
        ]
        for url, expected in test_cases:
            assert service.detect_platform(url) == expected
            assert ParserFactory.detect_platform(url) == expected

    def test_detect_platform_matches_host_not_substring(self):
        """도메인 이름이 쿼리·경로·다른 도메인의 일부로만 등장하면 매칭하면 안 된다."""
        cases = [
            ('https://example.com/share?ref=reddit.com', 'generic'),
            ('https://example.com/blog.naver/123', 'generic'),
            ('https://notopenai.com/post', 'generic'),
            ('https://reddit.com.evil.example/r/x', 'generic'),
            # 정상 케이스: 서브도메인·대소문자·포트
            ('https://old.reddit.com/r/test', 'reddit'),
            ('https://M.BLOG.NAVER.COM/user/1', 'naver'),
            ('https://n.news.naver.com/article/001/0001', 'naver_news'),
            ('https://news.naver.com/main/read.naver?oid=1', 'naver_news'),
            ('https://www.theverge.com:443/a', 'verge'),
            ('https://research.google/blog/x', 'google_research'),
            ('https://www.404media.co/x', '404media'),
        ]
        for url, expected in cases:
            assert ParserFactory.detect_platform(url) == expected, url

    def test_every_detectable_platform_is_registered(self):
        """감지 규칙이 가리키는 플랫폼은 모두 파서로 생성 가능해야 한다."""
        from crawler.factory import PLATFORMS
        available = set(ParserFactory.get_available_parsers())
        for name, _module, _cls, _domains in PLATFORMS:
            assert name in available

    def test_all_parsers_registered(self):
        available = ParserFactory.get_available_parsers()
        assert len(available) >= 40
        assert 'reddit' in available
        assert 'generic' in available


class TestInternalAddressGuard:
    """웹 API 가 서버 내부망(도커 호스트·VLM·메타데이터 등)을 대신 조회해주면 안 된다."""

    @pytest.mark.parametrize('url', [
        'http://localhost:5000/api/health',
        'http://127.0.0.1:8081/health',
        'http://169.254.169.254/latest/meta-data/',
        'http://10.0.0.5/',
        'http://192.168.0.10/admin',
        'http://[::1]/',
        'http://0.0.0.0/',
    ])
    def test_extract_rejects_internal_addresses(self, client, url):
        response = client.post('/api/extract', json={'url': url, 'sync': True})
        assert response.status_code == 400
        assert '내부' in json.loads(response.data)['error']

    def test_validator_allows_public_ip(self):
        assert URLValidator.check_public_host('http://93.184.216.34/') is None

    def test_guard_can_be_disabled_by_env(self, monkeypatch):
        monkeypatch.setenv('ALLOW_PRIVATE_URLS', '1')
        assert URLValidator.check_public_host('http://127.0.0.1/') is None

    def test_unresolvable_host_is_left_to_the_fetch(self):
        # DNS 실패는 가드가 판단할 대상이 아니다 — 실제 요청이 실패로 보고한다.
        assert URLValidator.check_public_host('http://no-such-host.invalid/') is None


class TestJobQueueLimits:
    """추출 요청마다 스레드를 무제한 생성하지 않고 대기열 상한을 둔다."""

    def test_rejects_when_queue_is_full(self, monkeypatch):
        import threading
        import web_app
        release = threading.Event()

        def slow(self, url):
            release.wait(5)
            return ExtractionResult(True, 'ok', 'x', {'url': url, 'status': 'success', 'content': 'x'}, 'generic')

        monkeypatch.setattr(CrawlerService, 'extract_content', slow)
        monkeypatch.setenv('EXTRACT_WORKERS', '1')
        monkeypatch.setenv('EXTRACT_MAX_PENDING', '2')
        app = web_app.create_app()
        client = app.test_client()
        try:
            codes = [
                client.post('/api/extract', json={'url': f'https://example.com/{i}'}).status_code
                for i in range(3)
            ]
            assert codes == [202, 202, 429]
        finally:
            release.set()


class TestEmptyContentIsNotSuccess:
    """파서가 status=success 를 줘도 본문이 비었으면 사용자에게 성공으로 보이면 안 된다."""

    @staticmethod
    def _service_with(monkeypatch, raw):
        class FakeParser:
            def parse_single(self, url):
                return dict(raw, url=url)

            def format_result(self, result):
                return 'formatted'

        monkeypatch.setattr(ParserFactory, 'create_parser', staticmethod(lambda *_a, **_k: FakeParser()))
        return CrawlerService()

    @pytest.mark.parametrize('content', ['', '   ', None, 'No content found'])
    def test_empty_body_is_failure(self, monkeypatch, content):
        service = self._service_with(monkeypatch, {'status': 'success', 'title': 'T', 'content': content})
        result = service.extract_content('https://example.com/a')
        assert result.success is False
        assert '본문' in result.message
        assert result.formatted_text == 'formatted'

    def test_body_present_is_success(self, monkeypatch):
        service = self._service_with(monkeypatch, {'status': 'success', 'content': 'hello'})
        assert service.extract_content('https://example.com/a').success is True

    def test_link_post_with_comments_is_success(self, monkeypatch):
        # 레딧 링크/이미지 게시물: 본문은 비어도 댓글이 추출 결과다.
        service = self._service_with(
            monkeypatch, {'status': 'success', 'content': '', 'comments': [{'content': 'c'}]})
        assert service.extract_content('https://www.reddit.com/r/x').success is True
