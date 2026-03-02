"""
상수 정의 모듈

프로젝트에서 사용되는 모든 매직 넘버와 문자열 상수를 정의합니다.
"""


class HTTPStatus:
    """HTTP 상태 코드"""
    OK = 200
    TOO_MANY_REQUESTS = 429


class RedditConstants:
    """Reddit 관련 상수"""
    COMMENT_KIND = 't1'
    URL_PATTERN = r'https://www\.reddit\.com/r/[a-zA-Z0-9_]+/comments/[a-zA-Z0-9]+/[^/\s]+'
    JSON_SUFFIX = '.json'

    # User-Agent
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'


class NaverBlogConstants:
    """네이버 블로그 관련 상수"""
    BASE_URL = 'https://blog.naver.com'
    IFRAME_ID = 'mainFrame'

    # HTML 선택자
    PARAGRAPH_ID_PATTERN = r'^SE-'
    DATE_CLASS_PATTERN = r'date|writeDate|se_publishDate'
    MAIN_CONTAINER_CLASS_PATTERN = r'se-main-container'

    # User-Agent
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'


class OutputConstants:
    """출력 형식 관련 상수"""
    POST_SEPARATOR = "=" * 80
    POST_SEPARATOR_SHORT = "=" * 16
    COMMENT_SEPARATOR = "-" * 40

    # 파일명 접두사
    PREFIX_REDDIT = 'parsed_reddit'
    PREFIX_REDDIT_SIMPLE = 'simple_reddit'
    PREFIX_REDDIT_BATCH = 'parsed_reddit_batch'
    PREFIX_NAVER = 'parsed_blogs'

    # 파일 확장자
    EXT_CSV = '.csv'
    EXT_JSON = '.json'
    EXT_TXT = '.txt'


class ParsingStatus:
    """파싱 상태"""
    SUCCESS = 'success'
    ERROR_PREFIX = 'error: '
