"""Test cases for the Flask web application"""

import json
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

    def test_extract_returns_proper_structure(self, client):
        response = client.post('/api/extract', json={
            'url': 'https://blog.samaltman.com/how-to-invest-in-startups'
        })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'success' in data
        assert 'platform' in data
        assert 'result' in data
        if data['success']:
            result = data['result']
            for key in ('title', 'content', 'author', 'url'):
                assert key in result


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

    def test_all_parsers_registered(self):
        available = ParserFactory.get_available_parsers()
        assert len(available) >= 40
        assert 'reddit' in available
        assert 'generic' in available
