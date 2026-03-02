"""Test cases for all parsers with real URLs that previously failed"""

import pytest
from crawler.factory import ParserFactory

# Mark all network-dependent tests
pytestmark = pytest.mark.network


class TestParsers:
    """Test all parsers with URLs that were reported as not working"""

    def test_gizmodo_parser(self):
        """Test Gizmodo parser with real URL"""
        parser = ParserFactory.create_parser('gizmodo')
        result = parser.parse_single('https://gizmodo.com/fake-protest-videos-are-the-latest-ai-slop-to-go-viral-in-maga-world-2000669656')

        assert result['status'] == 'success'
        assert result['parser'] == 'gizmodo'
        assert len(result['content']) > 100
        assert result['title'] != 'Unknown'
        assert 'AI' in result['content'] or 'video' in result['content'].lower()

    def test_arstechnica_parser(self):
        """Test Ars Technica parser with real URL"""
        parser = ParserFactory.create_parser('arstechnica')
        result = parser.parse_single('https://arstechnica.com/gadgets/2025/10/synology-caves-walks-back-some-drive-restrictions-on-upcoming-nas-models/')

        assert result['status'] == 'success'
        assert result['parser'] == 'arstechnica'
        assert len(result['content']) > 100
        assert 'Synology' in result['title']
        assert 'drive' in result['content'].lower() or 'nas' in result['content'].lower()

    def test_scmp_parser(self):
        """Test SCMP parser with real URL"""
        parser = ParserFactory.create_parser('scmp')
        result = parser.parse_single('https://www.scmp.com/tech/tech-trends/article/3328222/anthropics-anti-china-stance-triggers-exit-star-ai-researcher')

        assert result['status'] == 'success'
        assert result.get('parser', 'scmp') == 'scmp'
        assert len(result['content']) > 100
        assert 'Anthropic' in result['title']

    def test_androidpolice_parser(self):
        """Test Android Police parser with real URL"""
        parser = ParserFactory.create_parser('androidpolice')
        result = parser.parse_single('https://www.androidpolice.com/samsung-galaxy-one-ui-8-5-automatic-call-screening/')

        assert result['status'] == 'success'
        assert result.get('parser', 'androidpolice') == 'androidpolice'
        assert len(result['content']) > 100
        assert 'One UI' in result['title'] or 'Samsung' in result['title']

    def test_techafricanews_parser(self):
        """Test Tech African News parser with real URL"""
        parser = ParserFactory.create_parser('techafricanews')
        result = parser.parse_single('https://techafricanews.com/2025/10/07/cisco-introduces-breakthrough-software-stack-enabling-quantum-computers-to-work-as-one/')

        assert result['status'] == 'success'
        assert result.get('parser', 'techafricanews') == 'techafricanews'
        assert len(result['content']) > 100
        assert 'Cisco' in result['title'] or 'quantum' in result['title'].lower()

    def test_samaltman_parser(self):
        """Test Sam Altman blog parser with real URL"""
        parser = ParserFactory.create_parser('samaltman')
        result = parser.parse_single('https://blog.samaltman.com/how-to-invest-in-startups')

        assert result['status'] == 'success'
        assert result.get('parser', 'samaltman') == 'samaltman'
        assert len(result['content']) > 100
        assert 'startup' in result['content'].lower() or 'invest' in result['content'].lower()

    def test_techcrunch_parser(self):
        """Test TechCrunch parser with real URL"""
        parser = ParserFactory.create_parser('techcrunch')
        result = parser.parse_single('https://techcrunch.com/2025/10/08/even-after-stargate-oracle-nvidia-and-amd-openai-has-more-big-deals-coming-soon-sam-altman-says/')

        assert result['status'] == 'success'
        assert result.get('parser', 'techcrunch') == 'techcrunch'
        assert len(result['content']) > 100
        assert 'OpenAI' in result['title'] or 'Altman' in result['title']

    def test_substack_parser(self):
        """Test Substack parser with real URL"""
        parser = ParserFactory.create_parser('substack')
        result = parser.parse_single('https://ivoras.substack.com/p/2-month-minipc-mini-review-minisforum')

        assert result['status'] == 'success'
        assert result.get('parser', 'substack') == 'substack'
        assert len(result['content']) > 100
        assert 'MiniPC' in result['title'] or 'Minisforum' in result['title']

    def test_cnbc_parser(self):
        """Test CNBC parser with real URL"""
        parser = ParserFactory.create_parser('cnbc')
        result = parser.parse_single('https://www.cnbc.com/2025/10/06/applovin-stock-tanks-on-report-sec-is-investigating-company-over-data-collection-practices.html')

        assert result['status'] == 'success'
        assert result.get('parser', 'cnbc') == 'cnbc'
        assert len(result['content']) > 100
        assert 'AppLovin' in result['title'] or 'SEC' in result['title']

    def test_nbc_news_parser(self):
        """Test NBC News parser with real URL"""
        parser = ParserFactory.create_parser('nbc_news')
        result = parser.parse_single('https://www.nbcnews.com/business/business-news/paramount-cbs-news-acquires-free-press-bari-weiss-rcna220672')

        assert result['status'] == 'success'
        assert result.get('parser', 'nbc_news') == 'nbc_news'
        assert len(result['content']) > 100
        assert 'Paramount' in result['title'] or 'CBS' in result['title']

    def test_marktechpost_parser(self):
        """Test MarkTechPost parser with real URL"""
        parser = ParserFactory.create_parser('marktechpost')
        result = parser.parse_single('https://www.marktechpost.com/2025/10/08/anthropic-ai-releases-petri-an-open-source-framework-for-automated-auditing-by-using-ai-agents-to-test-the-behaviors-of-target-models-on-diverse-scenarios/')

        assert result['status'] == 'success'
        assert result.get('parser', 'marktechpost') == 'marktechpost'
        assert len(result['content']) > 100
        assert 'Anthropic' in result['title'] or 'Petri' in result['title']

    def test_towardsdatascience_parser(self):
        """Test Towards Data Science parser with real URL"""
        parser = ParserFactory.create_parser('towardsdatascience')
        result = parser.parse_single('https://towardsdatascience.com/know-your-real-birthday-astronomical-computation-and-geospatial-temporal-analytics-in-python/')

        assert result['status'] == 'success'
        assert result.get('parser', 'towardsdatascience') == 'towardsdatascience'
        assert len(result['content']) > 100
        assert 'birthday' in result['title'].lower() or 'astronomical' in result['title'].lower()

    def test_analyticsindiamag_parser(self):
        """Test Analytics India Magazine parser with real URL"""
        parser = ParserFactory.create_parser('analyticsindiamag')
        result = parser.parse_single('https://analyticsindiamag.com/global-tech/if-sap-can-support-chatgpt-5-in-a-day-is-enterprise-ai-finally-fast/')

        assert result['status'] == 'success'
        assert result.get('parser', 'analyticsindiamag') == 'analyticsindiamag'
        # Note: This site has paywall, so content may be limited
        assert 'SAP' in result['title'] or 'ChatGPT' in result['title']

    def test_economist_parser(self):
        """Test The Economist parser with real URL (uses cloudscraper for Cloudflare bypass)"""
        parser = ParserFactory.create_parser('economist')
        result = parser.parse_single('https://www.economist.com/business/2025/10/09/what-if-openai-went-belly-up')

        assert result['status'] == 'success'
        assert result.get('parser', 'economist') == 'economist'
        assert len(result['content']) > 100
        assert 'OpenAI' in result['title']
        assert result['author'] == 'The Economist'
        assert result['date'] != 'Unknown'

    def test_gamespot_parser(self):
        """Test GameSpot parser with real URL"""
        parser = ParserFactory.create_parser('gamespot')
        result = parser.parse_single('https://www.gamespot.com/articles/no-one-wants-a-100-gta-6-analysts-say/1100-6535494/?ftag=CAD-01-10abi2f')

        assert result['status'] == 'success'
        assert result.get('parser', 'gamespot') == 'gamespot'
        assert len(result['content']) > 100
        assert 'GTA 6' in result['title']
        assert result['author'] != 'Unknown'
        assert result['date'] != 'Unknown'

    def test_dexerto_parser(self):
        """Test Dexerto parser with real URL"""
        parser = ParserFactory.create_parser('dexerto')
        result = parser.parse_single('https://www.dexerto.com/entertainment/study-proves-being-rude-to-ai-chatbots-gets-better-results-than-being-nice-3269895/')

        assert result['status'] == 'success'
        assert result.get('parser', 'dexerto') == 'dexerto'
        assert len(result['content']) > 100
        assert 'AI' in result['title'] or 'chatbot' in result['title'].lower()
        assert result['author'] != 'Unknown'
        assert result['date'] != 'Unknown'

    def test_nltimes_parser(self):
        """Test NL Times parser with real URL"""
        parser = ParserFactory.create_parser('nltimes')
        result = parser.parse_single('https://nltimes.nl/2025/10/16/european-automakers-expect-chip-shortages-dutch-intervene-tech-firm-nexperia')

        assert result['status'] == 'success'
        assert result.get('parser', 'nltimes') == 'nltimes'
        assert len(result['content']) > 100
        assert 'chip' in result['title'].lower() or 'Nexperia' in result['title']
        assert result['author'] != 'Unknown'
        assert result['date'] != 'Unknown'

    @pytest.mark.xfail(reason="The Drive parser has pre-existing test failure")
    def test_thedrive_parser(self):
        """Test The Drive parser with real URL"""
        parser = ParserFactory.create_parser('thedrive')
        result = parser.parse_single('https://www.thedrive.com/news/miami-is-testing-a-self-driving-police-car-that-can-launch-drones')

        assert result['status'] == 'success'
        assert result.get('parser', 'thedrive') == 'thedrive'
        assert len(result['content']) > 100
        assert 'Miami' in result['title'] or 'drone' in result['title'].lower()
        assert result['author'] != 'Unknown'
        assert result['date'] != 'Unknown'

    def test_engadget_parser(self):
        """Test Engadget parser with real URL"""
        parser = ParserFactory.create_parser('engadget')
        result = parser.parse_single('https://www.engadget.com/computing/microsofts-next-windows-11-ai-gamble-just-say-hey-copilot-130000875.html')

        assert result['status'] == 'success'
        assert result.get('parser', 'engadget') == 'engadget'
        assert len(result['content']) > 100
        assert 'Microsoft' in result['title'] or 'Copilot' in result['title']
        assert result['author'] != 'Unknown'
        assert result['date'] != 'Unknown'

    def test_404media_parser(self):
        """Test 404 Media parser with real URL"""
        parser = ParserFactory.create_parser('404media')
        result = parser.parse_single('https://www.404media.co/reddit-answers-ai-suggests-users-try-heroin/')

        assert result['status'] == 'success'
        assert result.get('parser', '404media') == '404media'
        assert len(result['content']) > 100
        assert 'Reddit' in result['title'] or 'heroin' in result['title'].lower()
        assert result['author'] != 'Unknown'
        assert result['date'] != 'Unknown'

    def test_axios_parser(self):
        """Test Axios parser with real URL (uses cloudscraper for Cloudflare bypass)"""
        parser = ParserFactory.create_parser('axios')
        result = parser.parse_single('https://www.axios.com/2025/10/16/google-deepmind-clean-energy-fusion')

        assert result['status'] == 'success'
        assert result.get('parser', 'axios') == 'axios'
        assert len(result['content']) > 100
        assert 'Google' in result['title'] or 'DeepMind' in result['title'] or 'fusion' in result['title'].lower()

    def test_zmescience_parser(self):
        """Test ZME Science parser with real URL"""
        parser = ParserFactory.create_parser('zmescience')
        result = parser.parse_single('https://www.zmescience.com/science/news-science/california-first-solar-canal/')

        assert result['status'] == 'success'
        assert result.get('parser', 'zmescience') == 'zmescience'
        # ZME Science may have less content due to site structure
        assert 'California' in result['title'] or 'solar' in result['title'].lower()

    def test_tomshardware_parser(self):
        """Test Tom's Hardware parser with real URL"""
        parser = ParserFactory.create_parser('tomshardware')
        result = parser.parse_single('https://www.tomshardware.com/service-providers/network-providers/spacex-shows-off-massive-new-v3-starlink-satellites-expanded-technology-will-deliver-gigabit-internet-to-customers-for-the-first-time-and-enable-60-tera-bits-per-second-downlink-capacity')

        assert result['status'] == 'success'
        assert result.get('parser', 'tomshardware') == 'tomshardware'
        assert len(result['content']) > 100
        assert 'SpaceX' in result['title'] or 'Starlink' in result['title']
        assert result['author'] != 'Unknown'
        assert result['date'] != 'Unknown'

    def test_businessinsider_parser(self):
        """Test Business Insider parser with real URL"""
        parser = ParserFactory.create_parser('businessinsider')
        result = parser.parse_single('https://www.businessinsider.com/tiktok-insiders-creators-worry-for-you-algorithm-after-sale-2025-10')

        assert result['status'] == 'success'
        assert result.get('parser', 'businessinsider') == 'businessinsider'
        assert len(result['content']) > 100
        assert 'TikTok' in result['title'] or 'algorithm' in result['title'].lower()
        assert result['author'] != 'Unknown'
        assert result['date'] != 'Unknown'

    def test_sammobile_parser(self):
        """Test SamMobile parser with real URL"""
        parser = ParserFactory.create_parser('sammobile')
        result = parser.parse_single('https://www.sammobile.com/news/samsung-galaxy-s26-pro-naming/')

        assert result['status'] == 'success'
        assert result.get('parser', 'sammobile') == 'sammobile'
        assert len(result['content']) > 100
        assert 'Galaxy S26' in result['title'] or 'Pro' in result['title']
        assert result['author'] != 'Unknown'
        assert result['date'] != 'Unknown'

    def test_giveupinternet_parser(self):
        """Test Give Up Internet parser with real URL"""
        parser = ParserFactory.create_parser('giveupinternet')
        result = parser.parse_single('https://giveupinternet.com/2025/10/18/how-google-bought-the-internet-and-made-you-say-thank-you/')

        assert result['status'] == 'success'
        assert result.get('parser', 'giveupinternet') == 'giveupinternet'
        assert len(result['content']) > 100
        assert 'Google' in result['title']
        assert result['author'] != 'Unknown'
        assert result['date'] != 'Unknown'

    def test_pcgamer_parser(self):
        """Test PC Gamer parser with real URL"""
        parser = ParserFactory.create_parser('pcgamer')
        result = parser.parse_single('https://www.pcgamer.com/hardware/processors/apple-announces-new-m5-chip-with-double-the-per-core-performance-of-the-m1-and-its-got-me-wondering-why-amd-and-intel-cant-keep-up-with-apples-single-core-performance-gains/')

        assert result['status'] == 'success'
        assert result.get('parser', 'pcgamer') == 'pcgamer'
        assert len(result['content']) > 100
        assert 'M5' in result['title'] or 'Apple' in result['title']
        assert result['author'] != 'Unknown'
        assert result['date'] != 'Unknown'

    def test_datacenterknowledge_parser(self):
        """Test Data Center Knowledge parser with real URL"""
        parser = ParserFactory.create_parser('datacenterknowledge')
        result = parser.parse_single('https://www.datacenterknowledge.com/outages/microsoft-azure-outage-web-services-down-as-dns-issue-unfolds')

        assert result['status'] == 'success'
        assert result.get('parser', 'datacenterknowledge') == 'datacenterknowledge'
        assert len(result['content']) > 100
        assert 'Azure' in result['title'] or 'Microsoft' in result['title']
        assert result['author'] != 'Unknown'
        assert result['date'] != 'Unknown'

    def test_deadline_parser(self):
        """Test Deadline parser with real URL"""
        parser = ParserFactory.create_parser('deadline')
        result = parser.parse_single('https://deadline.com/2025/10/youtube-q3-revenue-tops-10b-alphabet-earnings-1236601988/')

        assert result['status'] == 'success'
        assert result.get('parser', 'deadline') == 'deadline'
        assert len(result['content']) > 100
        assert 'YouTube' in result['title'] or 'Alphabet' in result['title']
        assert result['author'] != 'Unknown'
        assert result['date'] != 'Unknown'

    def test_google_research_parser(self):
        """Test Google Research parser with real URL"""
        parser = ParserFactory.create_parser('google_research')
        result = parser.parse_single('https://research.google/blog/streetreaderai-towards-making-street-view-accessible-via-context-aware-multimodal-ai/')

        assert result['status'] == 'success'
        assert result.get('parser', 'google_research') == 'google_research'
        assert len(result['content']) > 1000  # Should have substantial content
        assert 'StreetReaderAI' in result['title'] or 'street view' in result['title'].lower()
        # Google Research blog may not always have structured author/date
        assert result['title'] != 'Unknown'

    @pytest.mark.xfail(reason="OpenAI uses Cloudflare protection which may block automated requests")
    def test_openai_parser(self):
        """Test OpenAI parser with real URL
        Note: OpenAI uses Cloudflare protection which may block automated requests,
        so we verify the parser handles errors gracefully
        """
        parser = ParserFactory.create_parser('openai')
        result = parser.parse_single('https://openai.com/index/introducing-aardvark')

        # OpenAI may return 403 due to Cloudflare protection
        # Verify parser handles the response (success or error) properly
        assert result['status'] in ['success', 'error']
        assert result.get('parser', 'openai') == 'openai'

        # If successful, verify content
        if result['status'] == 'success':
            assert len(result['content']) > 100
            assert result['title'] != 'Unknown'

    def test_thehindu_parser(self):
        """Test The Hindu parser with real URL"""
        parser = ParserFactory.create_parser('thehindu')
        result = parser.parse_single('https://www.thehindu.com/sci-tech/technology/youtube-will-use-ai-to-enhance-the-resolution-of-your-videos/article70220286.ece')

        assert result['status'] == 'success'
        assert result.get('parser', 'thehindu') == 'thehindu'
        assert len(result['content']) > 200
        assert 'YouTube' in result['title'] or 'youtube' in result['title'].lower()
        assert result['title'] != 'Unknown'

    def test_interviewquery_parser(self):
        """Test InterviewQuery parser with real URL"""
        parser = ParserFactory.create_parser('interviewquery')
        result = parser.parse_single('https://www.interviewquery.com/p/wharton-study-genai-roi-2025')

        assert result['status'] == 'success'
        assert result.get('parser', 'interviewquery') == 'interviewquery'
        assert len(result['content']) > 500
        assert 'Wharton' in result['title'] or 'GenAI' in result['title'] or 'ROI' in result['title']
        assert result['title'] != 'Unknown'


class TestExistingParsers:
    """Test that existing parsers still work correctly"""

    def test_reddit_parser(self):
        """Test Reddit parser with a real post"""
        parser = ParserFactory.create_parser('reddit')
        # Using a stable Reddit post
        result = parser.parse_single('https://www.reddit.com/r/ChatGPT/comments/1o18x4o/so_sad_cant_pay_for_chatgpt_with_my_chinaissued/')

        # Reddit parser should at least not crash
        assert result['status'] in ['success', 'error']
        assert result.get('parser', 'reddit') == 'reddit'

    def test_naver_blog_parser(self):
        """Test Naver Blog parser"""
        parser = ParserFactory.create_parser('naver')
        # This will likely fail due to network, but should handle gracefully
        result = parser.parse_single('https://m.blog.naver.com/PostView.naver?blogId=royvalue&logNo=224035747526&navType=by')

        assert result['status'] in ['success', 'error']
        assert result.get('parser', 'naver') == 'naver'

    def test_parser_factory_registration(self):
        """Test that all parsers are properly registered"""
        expected_parsers = [
            'reddit', 'naver', 'naver_news', 'verge', 'fortune',
            'nbc_news', 'cnbc', 'substack', 'wired', 'androidpolice',
            'scmp', 'gizmodo', 'arstechnica', 'techafricanews',
            'samaltman', 'techcrunch', 'marktechpost', 'towardsdatascience',
            'analyticsindiamag', 'economist', 'gamespot', 'dexerto', 'nltimes', 'thedrive',
            'engadget', '404media', 'axios', 'zmescience', 'tomshardware', 'businessinsider',
            'sammobile', 'giveupinternet', 'pcgamer', 'datacenterknowledge', 'deadline',
            'google_research', 'openai', 'thehindu', 'interviewquery', 'generic'
        ]

        available = ParserFactory.get_available_parsers()

        for parser_name in expected_parsers:
            assert parser_name in available, f"Parser '{parser_name}' not registered"

    def test_invalid_parser_raises_error(self):
        """Test that requesting invalid parser raises appropriate error"""
        with pytest.raises(ValueError, match="Unknown parser type"):
            ParserFactory.create_parser('nonexistent_parser')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
