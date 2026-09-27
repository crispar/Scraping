"""JSON-LD 을 직접 읽는 파서들이 흔한 변형 마크업에서 추출 전체를 실패시키지 않는지 검증.

이전 구현은 파서마다 복사된 루프에서 `data[0]`(빈 배열이면 IndexError)과
`json.loads(script.string)`(빈 script 면 TypeError)를 JSONDecodeError 만 잡은 채
호출해, ld+json 블록 하나만 이상해도 페이지 전체를 error 로 돌려줬다.
노드 선택 규칙(최상위 노드만, @graph 무시)은 기존과 동일해야 한다 — @graph 를 읽게
바꿨다가 towardsdatascience 작성자가 'Unknown' 으로 퇴행한 적이 있다.
"""

import pytest

from crawler.factory import ParserFactory

BODY = """
<h1>Html Title</h1>
<article><div class="entry-content">
<p>This is the first paragraph of the article body and it is long enough to be kept.</p>
<p>This is the second paragraph of the article body, also long enough to be kept.</p>
</div></article>
</body></html>
"""

# 깨진 블록들 뒤에 정상 최상위 Article → 기존처럼 JSON-LD 값을 써야 한다
HTML_MALFORMED_THEN_ARTICLE = """
<html><head><title>Html Title</title>
<script type="application/ld+json">[]</script>
<script type="application/ld+json"></script>
<script type="application/ld+json">not json</script>
<script type="application/ld+json">
{"@context": "https://schema.org", "@type": "Article", "headline": "LD Headline",
 "datePublished": "2026-09-01T00:00:00Z", "author": {"@type": "Person", "name": "Kim"}}
</script>
</head><body>""" + BODY

# @graph 안에만 Article → 기존처럼 JSON-LD 를 쓰지 않고 HTML 추출로 폴백해야 한다
HTML_GRAPH_ONLY = """
<html><head><title>Html Title</title>
<script type="application/ld+json">
{"@context": "https://schema.org", "@graph": [
  {"@type": "Article", "headline": "Graph Headline",
   "author": [{"@id": "https://example.com/#/schema/person/1"}]}
]}
</script>
</head><body>""" + BODY

JSON_LD_PARSERS = [
    'analyticsindiamag', 'arstechnica', 'economist', 'gizmodo',
    'marktechpost', 'samaltman', 'techafricanews', 'towardsdatascience',
]


def _make_resp(html):
    class _Resp:
        status_code = 200
        text = html
        content = html.encode()
        encoding = 'utf-8'
        apparent_encoding = 'utf-8'

        def raise_for_status(self):
            pass
    return _Resp()


def _parse(name, html, monkeypatch):
    import importlib
    parser = ParserFactory.create_parser(name)
    if hasattr(parser, 'rate_limiter'):
        monkeypatch.setattr(parser.rate_limiter, 'wait', lambda *a, **k: None)
    module = importlib.import_module(type(parser).__module__)
    fetch = lambda *a, **k: _make_resp(html)
    if hasattr(parser, 'scraper'):
        monkeypatch.setattr(parser.scraper, 'get', fetch)
    if hasattr(module, 'http_client'):
        monkeypatch.setattr(module.http_client, 'fetch', fetch)
    if hasattr(module, 'requests'):
        monkeypatch.setattr(module.requests, 'get', fetch)
    return parser.parse_single('https://example.com/article')


@pytest.mark.parametrize('name', JSON_LD_PARSERS)
def test_malformed_json_ld_blocks_do_not_abort(name, monkeypatch):
    result = _parse(name, HTML_MALFORMED_THEN_ARTICLE, monkeypatch)
    assert result['status'] == 'success', result.get('error')
    assert result['title'] == 'LD Headline'
    assert result['author'] == 'Kim'
    assert result['date'].startswith('2026-09-01')


@pytest.mark.parametrize('name', JSON_LD_PARSERS)
def test_graph_only_page_keeps_html_fallback(name, monkeypatch):
    result = _parse(name, HTML_GRAPH_ONLY, monkeypatch)
    assert result['status'] == 'success', result.get('error')
    assert result['title'] != 'Graph Headline'
