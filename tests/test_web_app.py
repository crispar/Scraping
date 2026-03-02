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
