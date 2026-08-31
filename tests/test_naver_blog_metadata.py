"""네이버 블로그 메타데이터(제목·URL·작성자·발행일) 추출 회귀 테스트

이전 구현은 (1) author 를 아예 뽑지 않았고, (2) 발행일을 span 태그로만 찾아
<p class="blog_date"> 를 쓰는 모바일(m.blog) 페이지에서 날짜를 놓쳤으며,
(3) PC 페이지에서는 사이드바의 span.date 를 먼저 잡아 엉뚱한 날짜를 넣었고,
(4) 포맷 출력에 원문 URL 이 없었다. 네트워크 없이 고정 HTML 로 검증한다.
"""

import pytest
from bs4 import BeautifulSoup

from crawler.factory import ParserFactory


MOBILE_HTML = """
<html><head>
  <title>Autonomous AI, 예기치 않은 수요 : 네이버 블로그</title>
  <meta property="og:url" content="https://blog.naver.com/doctordk/224394790055"/>
  <meta property="og:title" content="Autonomous AI, 예기치 않은 수요"/>
</head><body>
  <div class="blog_author"><span>의교창</span></div>
  <p class="blog_date">2026. 8. 30. 9:49</p>
  <div class="se-main-container"><div class="se-component"><p>본문</p></div></div>
</body></html>
"""

# PC 페이지에는 본문 발행일(.se_publishDate) 앞에 무관한 사이드바 날짜(span.date)가 있다.
PC_HTML = """
<html><head>
  <title>Autonomous AI, 예기치 않은 수요 : 네이버 블로그</title>
  <meta property="og:url" content="https://blog.naver.com/doctordk/224394790055"/>
</head><body>
  <div id="sidebar"><span class="date pcol2">2026. 3. 29.</span></div>
  <div class="blog2_container">
    <span class="nick">의교창</span>
    <div class="se-title-text"><p>Autonomous AI, 예기치 않은 수요</p></div>
    <span class="se_publishDate pcol2">2026. 8. 30. 9:49</span>
  </div>
</body></html>
"""


@pytest.fixture
def parser():
    return ParserFactory.create_parser('naver')


def _soup(html):
    return BeautifulSoup(html, 'html.parser')


class TestNaverBlogMetadata:

    def test_mobile_date_uses_blog_date_paragraph(self, parser):
        """모바일은 <p class="blog_date"> — span 만 찾던 예전 코드는 None 을 반환했다."""
        assert parser.extract_date(_soup(MOBILE_HTML)) == '2026. 8. 30. 9:49'

    def test_pc_date_prefers_publish_date_over_sidebar(self, parser):
        """PC 는 사이드바 span.date 가 아니라 .se_publishDate 를 써야 한다."""
        assert parser.extract_date(_soup(PC_HTML)) == '2026. 8. 30. 9:49'

    def test_author_from_mobile_and_pc_markup(self, parser):
        assert parser.extract_author(_soup(MOBILE_HTML), 'https://m.blog.naver.com/doctordk/224394790055') == '의교창'
        assert parser.extract_author(_soup(PC_HTML), 'https://blog.naver.com/doctordk/224394790055') == '의교창'

    def test_author_falls_back_to_blog_id(self, parser):
        """닉네임 마크업이 없으면 URL 의 blogId 라도 남긴다."""
        bare = _soup('<html><body><p>no nickname</p></body></html>')
        assert parser.extract_author(bare, 'https://m.blog.naver.com/doctordk/224394790055?enterPage=feed') == 'doctordk'
        assert parser.extract_author(
            bare, 'https://blog.naver.com/PostView.naver?blogId=doctordk&logNo=224394790055') == 'doctordk'

    def test_title_strips_naver_blog_suffix(self, parser):
        """<title> 폴백 시 ' : 네이버 블로그' 꼬리표를 떼어낸다."""
        only_title = _soup('<html><head><title>테스트 글 : 네이버 블로그</title></head><body></body></html>')
        assert parser.extract_title(only_title) == '테스트 글'
        assert parser.extract_title(_soup(PC_HTML)) == 'Autonomous AI, 예기치 않은 수요'

    def test_canonical_url_from_og_url(self, parser):
        """m.blog + 쿼리스트링으로 들어와도 정규 원문 주소를 돌려준다."""
        messy = 'https://m.blog.naver.com/doctordk/224394790055?enterPage=feed'
        assert parser.extract_canonical_url(_soup(MOBILE_HTML), messy) == \
            'https://blog.naver.com/doctordk/224394790055'
        assert parser.extract_canonical_url(_soup('<html></html>'), messy) == messy

    def test_format_result_includes_url_author_date(self, parser):
        """포맷 출력에 제목과 함께 원문 URL·작성자·발행일이 명기돼야 한다."""
        text = parser.format_result({
            'url': 'https://blog.naver.com/doctordk/224394790055',
            'title': 'Autonomous AI, 예기치 않은 수요',
            'author': '의교창',
            'date': '2026. 8. 30. 9:49',
            'content': '본문',
        })
        assert 'Title: Autonomous AI, 예기치 않은 수요' in text
        assert 'URL: https://blog.naver.com/doctordk/224394790055' in text
        assert 'Author: 의교창' in text
        assert 'Date: 2026. 8. 30. 9:49' in text
        # URL 은 제목 바로 아래여야 복사해도 출처가 붙어 나온다
        lines = text.split('\n')
        assert lines[1].startswith('URL: ')

    def test_format_result_shows_placeholders_for_missing_fields(self, parser):
        """값이 None 이어도 'None' 이 아니라 자리표시자가 나와야 한다."""
        text = parser.format_result({'url': None, 'title': None, 'author': None,
                                     'date': None, 'content': None})
        assert 'Author: Unknown' in text and 'Date: Unknown' in text
        assert 'None' not in text
