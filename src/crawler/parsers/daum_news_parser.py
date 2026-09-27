"""
Daum 뉴스 파서 (v.daum.net / news.v.daum.net)

Daum 뉴스는 언론사 기사를 재게시하는 포털이라 표준 메타데이터가 비어 있다.
- 제목: <h1> 은 언론사 로고라서 .tit_view(→ og:title) 를 쓴다.
- 날짜: 비표준 og:regDate(YYYYMMDDHHMMSS) → 없으면 화면의 .num_date.
- 작성자: .info_view 의 기자 이름('기자' 접미사 제거) → 없으면 언론사(og:article:author).
- 본문: .article_view 의 p[dmcf-ptype="general"] (자동요약 레이어·사진 캡션 제외).
"""

import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup

from crawler.core.base_parser import BaseParser
from crawler.utils.rate_limiter import SimpleRateLimiter

# 기자 표기 뒤에 붙는 직함. naver_news_parser 와 같은 규칙.
_TITLE_SUFFIX = re.compile(r'\s*(기자|특파원|앵커|에디터)\s*$')
# .txt_info 중 날짜 표기("입력 2026. 9. 27. 09:54")는 기자 이름이 아니다
_DATE_LIKE = re.compile(r'\d{4}\.\s*\d{1,2}\.\s*\d{1,2}\.')


class DaumNewsParser(BaseParser):
    """Parser for Daum news articles."""

    def __init__(self, max_workers=None, delay=None, log_level=logging.INFO, format_preset=None):
        super().__init__(max_workers=max_workers or 1, log_level=log_level)
        self.rate_limiter = SimpleRateLimiter(delay=delay or 1.0)

    def _get_logger_name(self) -> str:
        return 'daum_news_parser'

    def parse_single(self, url: str) -> Dict[str, Any]:
        self.logger.info(f"Parsing Daum news: {url}")
        try:
            self.rate_limiter.wait()
            soup = self.fetch_html(url, headers={'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8'})
            press = self._meta(soup, 'og:article:author')
            return {
                'status': 'success',
                'url': self._meta(soup, 'og:url') or url,
                'title': self._extract_title(soup),
                'author': self._extract_reporter(soup) or press or 'Unknown',
                'press': press,
                'date': self._extract_date(soup) or 'Unknown',
                'content': self._extract_content(soup),
                'parser': 'daum_news',
                'timestamp': datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Error parsing {url}: {e}")
            return {'status': 'error', 'url': url, 'error': str(e), 'parser': 'daum_news'}

    def format_result(self, result: Dict[str, Any]) -> str:
        lines = self.build_header_lines(
            result, extra_lines=[f"Press: {result.get('press') or 'N/A'}"]
        )
        lines.append("\n" + "=" * 80 + "\n")
        lines.append("Content:\n")
        lines.append(result.get('content') or 'N/A')
        return "\n".join(lines)

    @staticmethod
    def _meta(soup: BeautifulSoup, prop: str) -> Optional[str]:
        tag = soup.find('meta', property=prop)
        value = (tag.get('content') or '').strip() if tag else ''
        return value or None

    def _extract_title(self, soup: BeautifulSoup) -> str:
        headline = soup.select_one('.tit_view')
        if headline and headline.get_text(strip=True):
            return headline.get_text(strip=True)
        return self._meta(soup, 'og:title') or 'Unknown'

    @staticmethod
    def _extract_reporter(soup: BeautifulSoup) -> Optional[str]:
        for span in soup.select('.info_view .txt_info'):
            text = span.get_text(' ', strip=True)
            if not text or _DATE_LIKE.search(text):
                continue
            name = _TITLE_SUFFIX.sub('', text).strip()
            if name:
                return name
        return None

    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        reg_date = self._meta(soup, 'og:regDate')
        if reg_date:
            try:
                return datetime.strptime(reg_date, '%Y%m%d%H%M%S').strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                self.logger.debug(f"Unexpected og:regDate format: {reg_date}")
        shown = soup.select_one('.info_view .num_date')
        if shown:
            match = re.search(r'(\d{4})\.\s*(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{1,2}):(\d{2})', shown.get_text())
            if match:
                y, mo, d, h, mi = (int(g) for g in match.groups())
                return f"{y:04d}-{mo:02d}-{d:02d} {h:02d}:{mi:02d}"
            return shown.get_text(strip=True)
        return None

    @staticmethod
    def _extract_content(soup: BeautifulSoup) -> str:
        body = soup.select_one('.article_view')
        if not body:
            return 'No content found'
        paragraphs = body.select('p[dmcf-ptype="general"]') or body.find_all('p')
        texts = [p.get_text(' ', strip=True) for p in paragraphs]
        return '\n\n'.join(t for t in texts if t) or 'No content found'
