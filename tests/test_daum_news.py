"""Daum 뉴스(v.daum.net) 파서 — 네트워크 없이 실제 마크업 구조로 검증.

범용 파서로 처리되던 때는 <h1>(언론사 로고)을 제목으로, author/date 는 Unknown 으로 냈다.
Daum 은 날짜·언론사를 비표준 메타(og:regDate, og:article:author)에, 기자·날짜를 .info_view 에 둔다.
"""

import pytest

from crawler.factory import ParserFactory

HTML = """
<html><head>
<title>삼성전자, 3분기 영업익 110조 넘기나 | Daum 뉴스</title>
<meta property="og:title" content="삼성전자, 3분기 영업익 110조 넘기나…메모리 수익성 ‘사상 최고’">
<meta property="og:regDate" content="20260927095437">
<meta property="og:article:author" content="디지털타임스">
<meta property="og:url" content="https://v.daum.net/v/20260927095437316">
</head><body>
<h1><a href="#">디지털타임스</a></h1>
<div class="head_view">
  <h3 class="tit_view" data-translation="true">삼성전자, 3분기 영업익 110조 넘기나…메모리 수익성 ‘사상 최고’</h3>
  <div class="info_view">
    <span class="txt_info">이상현 기자</span>
    <span class="txt_info">입력 <span class="num_date">2026. 9. 27. 09:54</span></span>
  </div>
</div>
<div class="layer_summary"><p>자동요약 문장은 본문이 아니다.</p></div>
<div class="article_view"><section>
  <p dmcf-ptype="general">삼성전자가 반도체 호황에 힘입어 3분기에도 역대급 실적을 이어갈 전망이다.</p>
  <figure><img src="x.jpg"><figcaption>삼성전자 HBM4. 삼성전자 제공</figcaption></figure>
  <p dmcf-ptype="general">27일 업계에 따르면 삼성전자는 다음달 잠정실적을 발표할 예정이다.</p>
  <p></p>
  <p dmcf-ptype="general">이상현 기자 ishsy@dt.co.kr</p>
</section></div>
</body></html>
"""


class _Resp:
    status_code = 200
    text = HTML
    content = HTML.encode()
    encoding = 'utf-8'
    apparent_encoding = 'utf-8'

    def raise_for_status(self):
        pass


@pytest.fixture
def result(monkeypatch):
    import crawler.utils.http_client as http_client
    monkeypatch.setattr(http_client, 'fetch', lambda *a, **k: _Resp())
    parser = ParserFactory.create_parser('daum_news')
    monkeypatch.setattr(parser.rate_limiter, 'wait', lambda *a, **k: None)
    return parser, parser.parse_single('https://v.daum.net/v/20260927095437316')


@pytest.mark.parametrize('url', [
    'https://v.daum.net/v/20260927095437316',
    'https://news.v.daum.net/v/20260927095437316',
])
def test_daum_urls_route_to_daum_parser(url):
    assert ParserFactory.detect_platform(url) == 'daum_news'


def test_title_is_headline_not_press_logo(result):
    _, r = result
    assert r['status'] == 'success'
    assert r['title'] == '삼성전자, 3분기 영업익 110조 넘기나…메모리 수익성 ‘사상 최고’'


def test_author_is_reporter_and_press_is_kept(result):
    _, r = result
    assert r['author'] == '이상현'
    assert r['press'] == '디지털타임스'


def test_date_from_og_regdate(result):
    _, r = result
    assert r['date'] == '2026-09-27 09:54:37'


def test_content_is_article_body_only(result):
    _, r = result
    assert '역대급 실적' in r['content'] and '잠정실적' in r['content']
    assert '자동요약' not in r['content']
    assert r['content'].index('역대급') < r['content'].index('잠정실적')


def test_formatted_output_shows_press(result):
    parser, r = result
    text = parser.format_result(r)
    assert 'Author: 이상현' in text and 'Press: 디지털타임스' in text
    assert 'Date: 2026-09-27 09:54:37' in text


def test_fallbacks_when_meta_missing(monkeypatch):
    """og:regDate·기자 표기가 없으면 화면의 날짜·언론사로 폴백."""
    import crawler.utils.http_client as http_client
    html = (HTML.replace('<meta property="og:regDate" content="20260927095437">', '')
                .replace('<span class="txt_info">이상현 기자</span>', ''))

    class R(_Resp):
        text = html
    monkeypatch.setattr(http_client, 'fetch', lambda *a, **k: R())
    parser = ParserFactory.create_parser('daum_news')
    monkeypatch.setattr(parser.rate_limiter, 'wait', lambda *a, **k: None)
    r = parser.parse_single('https://v.daum.net/v/20260927095437316')
    assert r['date'] == '2026-09-27 09:54'
    assert r['author'] == '디지털타임스'
