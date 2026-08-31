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
    MAIN_CONTAINER_CLASS_PATTERN = r'se-main-container'

    # SmartEditor(SE) 컴포넌트 선택자 (본문을 문서 순서대로 순회하기 위함)
    COMPONENT_CLASS = 'se-component'          # 각 블록(텍스트/이미지/표 등)
    IMAGE_COMPONENT_CLASS = 'se-image'        # 이미지 계열(se-image, se-imageStrip, se-imageGroup)
    CAPTION_CLASS_PATTERN = r'se-caption|se-module-caption'
    IMG_LAZY_ATTR = 'data-lazy-src'           # 네이버 지연로딩 실제 src

    # 메타데이터 선택자 (PC=blog.naver.com/PostView, 모바일=m.blog.naver.com 둘 다 커버)
    # 순서가 곧 우선순위다. PC 페이지에는 본문 발행일과 무관한 사이드바 span.date 가
    # 함께 있어서, 실제 발행일인 .se_publishDate 를 반드시 먼저 봐야 한다.
    DATE_SELECTORS = ['.se_publishDate', '.blog_date', '.blog_date_time', '.date']
    AUTHOR_SELECTORS = ['.nick', '.blog_author', '.writer_nick', '.blog_nickname']
    TITLE_SELECTORS = ['.se-title-text', '.se_title', '.pcol1 .itemSubjectBoldfont']

    # '<제목> : 네이버 블로그' 꼬리표 제거용
    TITLE_SUFFIX_PATTERN = r'\s*[:|]\s*네이버\s*블로그\s*$'
    # 블로그 ID 추출 (닉네임을 못 찾았을 때 작성자 폴백)
    BLOG_ID_PATTERNS = [r'[?&]blogId=([^&#]+)', r'blog\.naver\.com/([^/?#]+)/\d+']

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
