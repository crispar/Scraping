"""
공통 파싱 유틸리티

DRY 원칙을 준수하기 위한 공통 파싱 함수들
"""

from typing import Any, Optional, Dict, Callable
from bs4 import BeautifulSoup, Tag


class ParsingHelper:
    """파싱 관련 공통 유틸리티"""

    @staticmethod
    def safe_extract(data: Optional[Dict], key: str, default: Any = '') -> Any:
        """
        딕셔너리에서 안전하게 값 추출

        Args:
            data: 딕셔너리 (None 가능)
            key: 키
            default: 기본값

        Returns:
            추출된 값 또는 기본값
        """
        if data is None:
            return default
        return data.get(key, default)

    @staticmethod
    def safe_find_text(soup: Optional[BeautifulSoup],
                       tag: str,
                       attrs: Optional[Dict] = None,
                       default: str = '',
                       strip: bool = True) -> str:
        """
        BeautifulSoup에서 안전하게 텍스트 추출

        Args:
            soup: BeautifulSoup 객체
            tag: 태그 이름
            attrs: 태그 속성 (선택)
            default: 기본값
            strip: 공백 제거 여부

        Returns:
            추출된 텍스트 또는 기본값
        """
        if soup is None:
            return default

        element = soup.find(tag, attrs) if attrs else soup.find(tag)
        if element is None:
            return default

        text = element.get_text(strip=strip) if hasattr(element, 'get_text') else default
        return text if text else default

    @staticmethod
    def safe_find_all_text(soup: Optional[BeautifulSoup],
                           tag: str,
                           attrs: Optional[Dict] = None,
                           separator: str = '\n',
                           strip: bool = True) -> str:
        """
        BeautifulSoup에서 여러 요소의 텍스트를 안전하게 추출

        Args:
            soup: BeautifulSoup 객체
            tag: 태그 이름
            attrs: 태그 속성 (선택)
            separator: 구분자
            strip: 공백 제거 여부

        Returns:
            결합된 텍스트
        """
        if soup is None:
            return ''

        elements = soup.find_all(tag, attrs) if attrs else soup.find_all(tag)
        texts = [elem.get_text(strip=strip) for elem in elements if hasattr(elem, 'get_text')]
        return separator.join(filter(None, texts))

    @staticmethod
    def safe_get_attr(element: Optional[Tag],
                      attr: str,
                      default: str = '') -> str:
        """
        BeautifulSoup 요소에서 안전하게 속성 추출

        Args:
            element: BeautifulSoup 요소
            attr: 속성 이름
            default: 기본값

        Returns:
            속성 값 또는 기본값
        """
        if element is None or not hasattr(element, 'get'):
            return default

        value = element.get(attr, default)
        return str(value) if value is not None else default

    @staticmethod
    def safe_int(value: Any, default: int = 0) -> int:
        """
        안전하게 정수로 변환

        Args:
            value: 변환할 값
            default: 기본값

        Returns:
            정수 또는 기본값
        """
        try:
            if value is None:
                return default
            if isinstance(value, str):
                # 쉼표 제거 (예: "1,234" -> 1234)
                value = value.replace(',', '').strip()
            return int(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def safe_float(value: Any, default: float = 0.0) -> float:
        """
        안전하게 실수로 변환

        Args:
            value: 변환할 값
            default: 기본값

        Returns:
            실수 또는 기본값
        """
        try:
            if value is None:
                return default
            if isinstance(value, str):
                value = value.replace(',', '').strip()
            return float(value)
        except (ValueError, TypeError):
            return default

    @staticmethod
    def clean_text(text: str,
                   strip: bool = True,
                   remove_newlines: bool = False,
                   collapse_spaces: bool = True) -> str:
        """
        텍스트 정리

        Args:
            text: 입력 텍스트
            strip: 앞뒤 공백 제거
            remove_newlines: 줄바꿈 제거
            collapse_spaces: 연속 공백 하나로 합치기

        Returns:
            정리된 텍스트
        """
        if not text:
            return ''

        result = text

        if strip:
            result = result.strip()

        if remove_newlines:
            result = result.replace('\n', ' ').replace('\r', '')

        if collapse_spaces:
            import re
            result = re.sub(r'\s+', ' ', result)

        return result

    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = '...') -> str:
        """
        텍스트 자르기

        Args:
            text: 입력 텍스트
            max_length: 최대 길이
            suffix: 생략 표시

        Returns:
            잘린 텍스트
        """
        if not text or len(text) <= max_length:
            return text

        return text[:max_length - len(suffix)] + suffix

    @staticmethod
    def apply_transform(value: Any,
                        transform: Optional[Callable[[Any], Any]] = None,
                        default: Any = None) -> Any:
        """
        값에 변환 함수 적용 (안전)

        Args:
            value: 입력 값
            transform: 변환 함수
            default: 기본값 (에러 시)

        Returns:
            변환된 값 또는 기본값
        """
        if transform is None:
            return value

        try:
            return transform(value)
        except Exception:
            return default if default is not None else value
