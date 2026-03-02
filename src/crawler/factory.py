"""
파서 팩토리 모듈

Factory Pattern을 사용하여 파서 인스턴스를 생성합니다.
"""

from typing import Dict, Type, Any
import logging
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

        Args:
            url: 분석할 URL

        Returns:
            감지된 플랫폼 이름 (기본값: 'generic')
        """
        url_lower = url.lower()
        
        # 매핑 규칙: (검색어, 플랫폼 이름)
        patterns = [
            ('reddit.com', 'reddit'),
            ('n.news.naver.com', 'naver_news'),
            ('news.naver.com/main', 'naver_news'),
            ('naver.com', 'naver'),
            ('blog.naver', 'naver'),
            ('theverge.com', 'verge'),
            ('fortune.com', 'fortune'),
            ('nbcnews.com', 'nbc_news'),
            ('cnbc.com', 'cnbc'),
            ('substack.com', 'substack'),
            ('wired.com', 'wired'),
            ('androidpolice.com', 'androidpolice'),
            ('scmp.com', 'scmp'),
            ('gizmodo.com', 'gizmodo'),
            ('arstechnica.com', 'arstechnica'),
            ('techafricanews.com', 'techafricanews'),
            ('blog.samaltman.com', 'samaltman'),
            ('techcrunch.com', 'techcrunch'),
            ('marktechpost.com', 'marktechpost'),
            ('towardsdatascience.com', 'towardsdatascience'),
            ('analyticsindiamag.com', 'analyticsindiamag'),
            ('economist.com', 'economist'),
            ('gamespot.com', 'gamespot'),
            ('dexerto.com', 'dexerto'),
            ('nltimes.nl', 'nltimes'),
            ('thedrive.com', 'thedrive'),
            ('engadget.com', 'engadget'),
            ('404media.co', '404media'),
            ('axios.com', 'axios'),
            ('zmescience.com', 'zmescience'),
            ('tomshardware.com', 'tomshardware'),
            ('businessinsider.com', 'businessinsider'),
            ('sammobile.com', 'sammobile'),
            ('giveupinternet.com', 'giveupinternet'),
            ('pcgamer.com', 'pcgamer'),
            ('technical.ly', 'technically'),
            ('9to5google.com', 'ninetofivegoogle'),
            ('restofworld.org', 'restofworld'),
            ('upperclasscareer.com', 'upperclasscareer'),
            ('sfgate.com', 'sfgate'),
            ('datacenterknowledge.com', 'datacenterknowledge'),
            ('deadline.com', 'deadline'),
            ('research.google', 'google_research'),
            ('openai.com', 'openai'),
            ('thehindu.com', 'thehindu'),
            ('interviewquery.com', 'interviewquery')
        ]

        for pattern, platform in patterns:
            if pattern in url_lower:
                return platform
                
        return 'generic'


def initialize_parsers() -> None:
    """
    기본 파서들을 팩토리에 등록 (Lazy Loading)
    """
    parsers = {
        'reddit': ('crawler.parsers.reddit_parser', 'RedditParser'),
        'naver': ('crawler.parsers.naver_blog_parser', 'NaverBlogParser'),
        'naver_news': ('crawler.parsers.naver_news_parser', 'NaverNewsParser'),
        'verge': ('crawler.parsers.verge_parser', 'VergeParser'),
        'fortune': ('crawler.parsers.fortune_parser', 'FortuneParser'),
        'nbc_news': ('crawler.parsers.nbc_news_parser', 'NBCNewsParser'),
        'cnbc': ('crawler.parsers.cnbc_parser', 'CNBCParser'),
        'substack': ('crawler.parsers.substack_parser', 'SubstackParser'),
        'wired': ('crawler.parsers.wired_parser', 'WiredParser'),
        'androidpolice': ('crawler.parsers.androidpolice_parser', 'AndroidPoliceParser'),
        'scmp': ('crawler.parsers.scmp_parser', 'SCMPParser'),
        'gizmodo': ('crawler.parsers.gizmodo_parser', 'GizmodoParser'),
        'arstechnica': ('crawler.parsers.arstechnica_parser', 'ArsTechnicaParser'),
        'techafricanews': ('crawler.parsers.techafricanews_parser', 'TechAfricanNewsParser'),
        'samaltman': ('crawler.parsers.samaltman_parser', 'SamAltmanParser'),
        'techcrunch': ('crawler.parsers.techcrunch_parser', 'TechCrunchParser'),
        'marktechpost': ('crawler.parsers.marktechpost_parser', 'MarkTechPostParser'),
        'towardsdatascience': ('crawler.parsers.towardsdatascience_parser', 'TowardsDataScienceParser'),
        'analyticsindiamag': ('crawler.parsers.analyticsindiamag_parser', 'AnalyticsIndiaMagParser'),
        'economist': ('crawler.parsers.economist_parser', 'EconomistParser'),
        'gamespot': ('crawler.parsers.gamespot_parser', 'GameSpotParser'),
        'dexerto': ('crawler.parsers.dexerto_parser', 'DexertoParser'),
        'nltimes': ('crawler.parsers.nltimes_parser', 'NLTimesParser'),
        'thedrive': ('crawler.parsers.thedrive_parser', 'TheDriveParser'),
        'engadget': ('crawler.parsers.engadget_parser', 'EngadgetParser'),
        '404media': ('crawler.parsers.fourzerofour_parser', 'FourZeroFourParser'),
        'axios': ('crawler.parsers.axios_parser', 'AxiosParser'),
        'zmescience': ('crawler.parsers.zmescience_parser', 'ZMEScienceParser'),
        'tomshardware': ('crawler.parsers.tomshardware_parser', 'TomsHardwareParser'),
        'businessinsider': ('crawler.parsers.businessinsider_parser', 'BusinessInsiderParser'),
        'sammobile': ('crawler.parsers.sammobile_parser', 'SamMobileParser'),
        'giveupinternet': ('crawler.parsers.giveupinternet_parser', 'GiveUpInternetParser'),
        'pcgamer': ('crawler.parsers.pcgamer_parser', 'PCGamerParser'),
        'technically': ('crawler.parsers.technically_parser', 'TechnicallyParser'),
        'ninetofivegoogle': ('crawler.parsers.ninetofivegoogle_parser', 'NineToFiveGoogleParser'),
        'restofworld': ('crawler.parsers.restofworld_parser', 'RestOfWorldParser'),
        'upperclasscareer': ('crawler.parsers.upperclasscareer_parser', 'UpperclasscareerParser'),
        'sfgate': ('crawler.parsers.sfgate_parser', 'SFGateParser'),
        'datacenterknowledge': ('crawler.parsers.datacenterknowledge_parser', 'DataCenterKnowledgeParser'),
        'deadline': ('crawler.parsers.deadline_parser', 'DeadlineParser'),
        'google_research': ('crawler.parsers.google_research_parser', 'GoogleResearchParser'),
        'openai': ('crawler.parsers.openai_parser', 'OpenAIParser'),
        'thehindu': ('crawler.parsers.thehindu_parser', 'TheHinduParser'),
        'interviewquery': ('crawler.parsers.interviewquery_parser', 'InterviewQueryParser'),
        'generic': ('crawler.parsers.generic_parser', 'GenericParser'),
    }

    for name, (module, cls) in parsers.items():
        ParserFactory.register_parser(name, module, cls)


# 모듈 로드 시 자동으로 파서 등록
initialize_parsers()
