"""JSON-LD 을 직접 읽는 파서들이 흔한 변형 마크업에서 추출 전체를 실패시키지 않는지 검증.

이전 구현은 파서마다 복사된 루프에서 `data[0]`(빈 배열이면 IndexError)과
`json.loads(script.string)`(빈 script 면 TypeError)를 JSONDecodeError 만 잡은 채
호출해, ld+json 블록 하나만 이상해도 페이지 전체를 error 로 돌려줬다.
또 @graph 구조와 리스트형 @type 을 인식하지 못했다. 네트워크 없이 고정 HTML 로 검증한다.
"""

import pytest

from crawler.factory import ParserFactory

HTML = """
<html><head>
<title>Fallback Title</title>
<script type="application/ld+json">[]</script>
<script type="application/ld+json"></script>
<script type="application/ld+json">not json</script>
<script type="application/ld+json">
{"@context": "https://schema.org", "@graph": [
  {"@type": "WebPage", "name": "page"},
  {"@type": ["Article", "NewsArticle"], "headline": "Graph Headline",
   "datePublished": "2026-09-01T00:00:00Z", "author": {"@type": "Person", "name": "Kim"}}
]}
</script>
</head><body>
<h1>Fallback Title</h1>
<article><div class="entry-content">
<p>This is the first paragraph of the article body and it is long enough to be kept.</p>
<p>This is the second paragraph of the article body, also long enough to be kept.</p>
</div></article>
</body></html>
"""

JSON_LD_PARSERS = [
    'analyticsindiamag', 'arstechnica', 'economist', 'gizmodo',
    'marktechpost', 'samaltman', 'techafricanews', 'towardsdatascience',
]


class _Resp:
    status_code = 200
    text = HTML
    content = HTML.encode()
    encoding = 'utf-8'
    apparent_encoding = 'utf-8'

    def raise_for_status(self):
        pass


@pytest.mark.parametrize('name', JSON_LD_PARSERS)
def test_malformed_json_ld_blocks_do_not_abort_and_graph_is_read(name, monkeypatch):
    import importlib
    parser = ParserFactory.create_parser(name)
    if hasattr(parser, 'rate_limiter'):
        monkeypatch.setattr(parser.rate_limiter, 'wait', lambda *a, **k: None)
    module = importlib.import_module(type(parser).__module__)
    if hasattr(parser, 'scraper'):
        monkeypatch.setattr(parser.scraper, 'get', lambda *a, **k: _Resp())
    else:
        monkeypatch.setattr(module.requests, 'get', lambda *a, **k: _Resp())

    result = parser.parse_single('https://example.com/article')

    assert result['status'] == 'success', result.get('error')
    assert result['title'] == 'Graph Headline'
    assert result['author'] == 'Kim'
    assert result['date'].startswith('2026-09-01')

