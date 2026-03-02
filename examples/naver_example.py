"""
네이버 블로그 파싱 예제

이 스크립트는 네이버 블로그 크롤링을 Python 코드에서 직접 사용하는 방법을 보여줍니다.
"""

from crawler.factory import ParserFactory
from crawler.parsers import NaverBlogParser

def example_using_factory():
    """팩토리 패턴을 사용한 예제"""
    print("=" * 60)
    print("Example 1: Using ParserFactory")
    print("=" * 60)

    # 파서 생성
    parser = ParserFactory.create_parser('naver', max_workers=3, delay=1.0)

    # URL 리스트 파싱
    urls = [
        'https://blog.naver.com/user1/post1',
        'https://blog.naver.com/user2/post2'
    ]

    # 파싱 실행
    results = parser.parse_multiple_blogs(urls, output_dir='parsed_blogs')

    # 결과 확인
    success_count = parser.get_success_count(results)
    print(f"\nParsing completed: {success_count} successful out of {len(results)} total")
    print(f"\nResults saved to: parsed_blogs/")

    return results


def example_using_direct_import():
    """직접 import를 사용한 예제"""
    print("\n" + "=" * 60)
    print("Example 2: Using Direct Import")
    print("=" * 60)

    # 파서 직접 생성
    naver = NaverBlogParser(max_workers=3, delay=1.0)

    # URL 리스트 파싱
    urls = [
        'https://blog.naver.com/user1/post1',
        'https://blog.naver.com/user2/post2'
    ]

    # 파싱 실행
    results = naver.parse_multiple_blogs(urls, 'parsed_blogs')

    # 결과 확인
    success_count = naver.get_success_count(results)
    print(f"\nParsing completed: {success_count} successful out of {len(results)} total")

    return results


def example_single_url():
    """단일 URL 파싱 예제"""
    print("\n" + "=" * 60)
    print("Example 3: Parsing Single URL")
    print("=" * 60)

    parser = ParserFactory.create_parser('naver')

    # 단일 URL 파싱
    url = 'https://blog.naver.com/icarus-/224025444860'
    result = parser.parse_single(url)

    print(f"\nURL: {result['url']}")
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Title: {result.get('title', 'N/A')}")
        print(f"Content length: {len(result.get('content', ''))} characters")

    return result


def example_with_custom_options():
    """커스텀 옵션을 사용한 예제"""
    print("\n" + "=" * 60)
    print("Example 4: Using Custom Options")
    print("=" * 60)

    # 커스텀 설정으로 파서 생성
    parser = ParserFactory.create_parser(
        'naver',
        max_workers=5,      # 동시 처리 개수 증가
        delay=2.0,          # 요청 간격 증가
        log_level=10        # DEBUG 레벨 (10=DEBUG, 20=INFO)
    )

    urls = [
        'https://blog.naver.com/user1/post1',
        'https://blog.naver.com/user2/post2',
        'https://blog.naver.com/user3/post3'
    ]

    results = parser.parse_multiple_blogs(urls, output_dir='my_custom_output')

    print(f"\nResults saved to: my_custom_output/")
    print(f"Total URLs processed: {len(results)}")

    return results


if __name__ == '__main__':
    print("\n")
    print("=" * 60)
    print("NAVER BLOG PARSING EXAMPLES")
    print("=" * 60)
    print("\n")

    # 실제 사용 시에는 원하는 예제의 주석을 해제하세요

    # Example 1: 팩토리 패턴 사용
    # example_using_factory()

    # Example 2: 직접 import 사용
    # example_using_direct_import()

    # Example 3: 단일 URL 파싱
    example_single_url()

    # Example 4: 커스텀 옵션 사용
    # example_with_custom_options()

    print("\n[NOTE] Uncomment the examples above to run them")
    print("       Replace the example URLs with real Naver blog URLs\n")
