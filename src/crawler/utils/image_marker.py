"""본문 삽입 이미지의 인라인 텍스트 마커 유틸리티

추출된 본문(content 문자열)은 그대로 클립보드 복사·CSV/TXT 저장·API 응답에 흐른다.
본문 이미지(기사 캡처·차트·표)는 텍스트만 뽑던 기존 파이프라인에서 누락됐는데,
이 모듈은 이미지의 URL과(가능하면) VLM 해석 결과를 본문 흐름의 제자리에 끼워 넣는
단일 라인/블록 마커를 만든다.
"""

import re
from typing import Optional


# 마커 포맷 프리셋
MARKER_FORMAT_PLAIN = 'plain'        # [이미지: 캡션] url  (+ VLM 설명 블록)
MARKER_FORMAT_MARKDOWN = 'markdown'  # ![캡션](url)        (+ VLM 설명 블록)
DEFAULT_MARKER_FORMAT = MARKER_FORMAT_PLAIN


def resolve_image_src(img_tag, base_url: str = '') -> Optional[str]:
    """<img> 에서 실제 이미지 URL 추출.

    - 네이버 지연로딩: data-lazy-src > data-src > src 순.
    - base64 data URI 는 제외(본문에 수 KB 덤프 방지).
    - 프로토콜 상대(//) / 루트 상대(/) 경로 정규화.
    """
    if img_tag is None:
        return None
    url = (img_tag.get('data-lazy-src')
           or img_tag.get('data-src')
           or img_tag.get('src')
           or '')
    url = url.strip()
    if not url or url.startswith('data:'):
        return None
    if url.startswith('//'):
        url = 'https:' + url
    elif url.startswith('/') and base_url:
        url = base_url.rstrip('/') + url
    return url


def build_image_marker(url: str,
                       caption: str = '',
                       description: str = '',
                       marker_format: str = DEFAULT_MARKER_FORMAT) -> str:
    """이미지 한 장에 대한 인라인 마커 문자열 생성.

    Args:
        url: 이미지 URL
        caption: 이미지 캡션(se-caption 또는 alt)
        description: VLM 이 해석한 이미지 내용(있으면 블록으로 덧붙임)
        marker_format: 'plain' | 'markdown'
    """
    caption = (caption or '').strip()
    if marker_format == MARKER_FORMAT_MARKDOWN:
        head = f'![{caption}]({url})'
    else:
        head = f'[이미지: {caption}] {url}' if caption else f'[이미지] {url}'

    description = (description or '').strip()
    if description:
        # 이미지 내용을 들여쓰기 블록으로 첨부 → 붙여넣기 시 본문과 구분되면서 함께 읽힘
        body = '\n'.join('  ' + line for line in description.splitlines())
        return f'{head}\n  ↳ (이미지 내용)\n{body}'
    return head


def extract_image_caption(component, caption_pattern: str) -> str:
    """SE 이미지 컴포넌트에서 캡션 텍스트 추출(없으면 img alt)."""
    cap = component.find(class_=re.compile(caption_pattern))
    if cap:
        text = cap.get_text(strip=True)
        if text:
            return text
    img = component.find('img')
    if img and img.get('alt'):
        return img.get('alt').strip()
    return ''
