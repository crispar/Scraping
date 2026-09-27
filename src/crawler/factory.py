"""
파서 팩토리 모듈

Factory Pattern을 사용하여 파서 인스턴스를 생성합니다.
"""

from typing import Dict, List, Tuple, Type
from urllib.parse import urlparse
from crawler.core.base_parser import BaseParser


class ParserFactory:
    """
    파서 팩토리 클래스

    요청된 타입에 따라 적절한 파서 인스턴스를 생성합니다.
    Registry Pattern을 함께 사용하여 확장 가능하도록 설계되었습니다.
    """

    # 등록된 파서 정보를 저장하는 레지스트리 (이름 -> (모듈 경로, 클래스 이름))
    _registry: Dict[str, tuple] = {}
    # 로드된 파서 클래스 캐시
    _loaded_parsers: Dict[str, Type[BaseParser]] = {}

    @classmethod
    def register_parser(cls, name: str, module_path: str, class_name: str) -> None:
        """
        파서 등록 (Lazy Loading 지원)

        Args:
            name: 파서 이름 (예: 'reddit', 'naver')
            module_path: 모듈 경로 (예: 'crawler.parsers.reddit_parser')
            class_name: 클래스 이름 (예: 'RedditParser')
        """
        cls._registry[name] = (module_path, class_name)

    @classmethod
    def create_parser(cls, parser_type: str, **kwargs) -> BaseParser:
        """
        파서 인스턴스 생성

        Args:
            parser_type: 파서 타입 ('reddit', 'naver' 등)
            **kwargs: 파서 생성자에 전달할 키워드 인자

        Returns:
            파서 인스턴스

        Raises:
            ValueError: 등록되지 않은 파서 타입인 경우
        """
        if parser_type not in cls._registry:
            available = ', '.join(cls._registry.keys())
            raise ValueError(
                f"Unknown parser type: '{parser_type}'. "
                f"Available parsers: {available}"
            )

        # 이미 로드되지 않았다면 로드
        if parser_type not in cls._loaded_parsers:
            module_path, class_name = cls._registry[parser_type]
            try:
                module = __import__(module_path, fromlist=[class_name])
                parser_class = getattr(module, class_name)
                cls._loaded_parsers[parser_type] = parser_class
            except (ImportError, AttributeError) as e:
                raise ImportError(f"Failed to load parser '{parser_type}': {e}")

        parser_class = cls._loaded_parsers[parser_type]
        return parser_class(**kwargs)

    @classmethod
    def get_available_parsers(cls) -> list:
        """
        사용 가능한 파서 목록 반환

        Returns:
            등록된 파서 이름 리스트
        """
        return list(cls._registry.keys())

    @staticmethod
    def detect_platform(url: str) -> str:
        """
        URL에서 플랫폼 자동 감지

        호스트명(과 필요한 경우 경로 접두사)으로만 매칭한다. URL 전체 부분문자열로
        비교하면 '?ref=reddit.com' 같은 쿼리나 'notopenai.com' 같은 다른 도메인이
        엉뚱한 파서로 라우팅된다.

        Args:
            url: 분석할 URL

        Returns:
            감지된 플랫폼 이름 (기본값: 'generic')
        """
        parsed = urlparse(url.strip())
        host = (parsed.hostname or '').lower()
        path = parsed.path or '/'
        if not host:
            return 'generic'

        for name, _module, _cls, domains in PLATFORMS:
            for rule in domains:
                domain, _, path_prefix = rule.partition('/')
                if host != domain and not host.endswith('.' + domain):
                    continue
                if path_prefix and not path.startswith('/' + path_prefix):
                    continue
                return name

        return 'generic'


# 플랫폼 레지스트리 — 파서 등록과 URL 감지 규칙의 단일 출처.
# (이름, 모듈, 클래스, 감지 도메인). 도메인은 서브도메인까지 매칭하며,
# 'host/path' 형태면 경로 접두사도 본다. 순서가 곧 감지 우선순위이므로
# 더 구체적인 규칙(naver_news)을 포괄 규칙(naver)보다 앞에 둔다.
PLATFORMS: List[Tuple[str, str, str, Tuple[str, ...]]] = [
    ('reddit', 'reddit_parser', 'RedditParser', ('reddit.com',)),
    ('naver_news', 'naver_news_parser', 'NaverNewsParser', ('n.news.naver.com', 'news.naver.com/main')),
    ('naver', 'naver_blog_parser', 'NaverBlogParser', ('naver.com',)),
    ('verge', 'verge_parser', 'VergeParser', ('theverge.com',)),
    ('fortune', 'fortune_parser', 'FortuneParser', ('fortune.com',)),
    ('nbc_news', 'nbc_news_parser', 'NBCNewsParser', ('nbcnews.com',)),
    ('cnbc', 'cnbc_parser', 'CNBCParser', ('cnbc.com',)),
    ('substack', 'substack_parser', 'SubstackParser', ('substack.com',)),
    ('wired', 'wired_parser', 'WiredParser', ('wired.com',)),
    ('androidpolice', 'androidpolice_parser', 'AndroidPoliceParser', ('androidpolice.com',)),
    ('scmp', 'scmp_parser', 'SCMPParser', ('scmp.com',)),
    ('gizmodo', 'gizmodo_parser', 'GizmodoParser', ('gizmodo.com',)),
    ('arstechnica', 'arstechnica_parser', 'ArsTechnicaParser', ('arstechnica.com',)),
    ('techafricanews', 'techafricanews_parser', 'TechAfricanNewsParser', ('techafricanews.com',)),
    ('samaltman', 'samaltman_parser', 'SamAltmanParser', ('blog.samaltman.com',)),
    ('techcrunch', 'techcrunch_parser', 'TechCrunchParser', ('techcrunch.com',)),
    ('marktechpost', 'marktechpost_parser', 'MarkTechPostParser', ('marktechpost.com',)),
    ('towardsdatascience', 'towardsdatascience_parser', 'TowardsDataScienceParser', ('towardsdatascience.com',)),
    ('analyticsindiamag', 'analyticsindiamag_parser', 'AnalyticsIndiaMagParser', ('analyticsindiamag.com',)),
    ('economist', 'economist_parser', 'EconomistParser', ('economist.com',)),
    ('gamespot', 'gamespot_parser', 'GameSpotParser', ('gamespot.com',)),
    ('dexerto', 'dexerto_parser', 'DexertoParser', ('dexerto.com',)),
    ('nltimes', 'nltimes_parser', 'NLTimesParser', ('nltimes.nl',)),
    ('thedrive', 'thedrive_parser', 'TheDriveParser', ('thedrive.com',)),
    ('engadget', 'engadget_parser', 'EngadgetParser', ('engadget.com',)),
    ('404media', 'fourzerofour_parser', 'FourZeroFourParser', ('404media.co',)),
    ('axios', 'axios_parser', 'AxiosParser', ('axios.com',)),
    ('zmescience', 'zmescience_parser', 'ZMEScienceParser', ('zmescience.com',)),
    ('tomshardware', 'tomshardware_parser', 'TomsHardwareParser', ('tomshardware.com',)),
    ('businessinsider', 'businessinsider_parser', 'BusinessInsiderParser', ('businessinsider.com',)),
    ('sammobile', 'sammobile_parser', 'SamMobileParser', ('sammobile.com',)),
    ('giveupinternet', 'giveupinternet_parser', 'GiveUpInternetParser', ('giveupinternet.com',)),
    ('pcgamer', 'pcgamer_parser', 'PCGamerParser', ('pcgamer.com',)),
    ('technically', 'technically_parser', 'TechnicallyParser', ('technical.ly',)),
    ('ninetofivegoogle', 'ninetofivegoogle_parser', 'NineToFiveGoogleParser', ('9to5google.com',)),
    ('restofworld', 'restofworld_parser', 'RestOfWorldParser', ('restofworld.org',)),
    ('upperclasscareer', 'upperclasscareer_parser', 'UpperclasscareerParser', ('upperclasscareer.com',)),
    ('sfgate', 'sfgate_parser', 'SFGateParser', ('sfgate.com',)),
    ('datacenterknowledge', 'datacenterknowledge_parser', 'DataCenterKnowledgeParser', ('datacenterknowledge.com',)),
    ('deadline', 'deadline_parser', 'DeadlineParser', ('deadline.com',)),
    ('google_research', 'google_research_parser', 'GoogleResearchParser', ('research.google',)),
    ('openai', 'openai_parser', 'OpenAIParser', ('openai.com',)),
    ('thehindu', 'thehindu_parser', 'TheHinduParser', ('thehindu.com',)),
    ('interviewquery', 'interviewquery_parser', 'InterviewQueryParser', ('interviewquery.com',)),
]

# 도메인 규칙이 없는 폴백 파서
GENERIC_PLATFORM = ('generic', 'generic_parser', 'GenericParser')


def initialize_parsers() -> None:
    """
    기본 파서들을 팩토리에 등록 (Lazy Loading)
    """
    for name, module, cls, _domains in PLATFORMS:
        ParserFactory.register_parser(name, f'crawler.parsers.{module}', cls)
    name, module, cls = GENERIC_PLATFORM
    ParserFactory.register_parser(name, f'crawler.parsers.{module}', cls)


# 모듈 로드 시 자동으로 파서 등록
initialize_parsers()
