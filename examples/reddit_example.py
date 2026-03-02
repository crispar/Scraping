"""
Reddit 파싱 예제

이 스크립트는 Reddit 크롤링을 Python 코드에서 직접 사용하는 방법을 보여줍니다.
"""

from crawler.factory import ParserFactory
from crawler.parsers import RedditParser

def example_using_factory():
    """팩토리 패턴을 사용한 예제"""
    print("=" * 60)
    print("Example 1: Using ParserFactory")
    print("=" * 60)

    # 파서 생성
    parser = ParserFactory.create_parser(
        'reddit',
        max_workers=3,
        min_delay=2.0,
        max_delay=4.0
    )

    # 파일에서 URL 읽어서 파싱
    results = parser.parse_from_file('input.txt', output_dir='parsed_reddit')

    # 결과 확인
    if results is not None:
        success_count = parser.get_success_count(results)
        print(f"\nParsing completed: {success_count} successful out of {len(results)} total")
        print(f"\nResults saved to: parsed_reddit/")

    return results


def example_using_direct_import():
    """직접 import를 사용한 예제"""
    print("\n" + "=" * 60)
    print("Example 2: Using Direct Import")
    print("=" * 60)

    # 파서 직접 생성
    reddit = RedditParser(max_workers=3, min_delay=2.0, max_delay=4.0)

    # 파일에서 URL 읽어서 파싱
    results = reddit.parse_from_file('input.txt', 'parsed_reddit')

    if results is not None:
        success_count = reddit.get_success_count(results)
        print(f"\nParsing completed: {success_count} successful out of {len(results)} total")

    return results


def example_single_url():
    """단일 URL 파싱 예제"""
    print("\n" + "=" * 60)
    print("Example 3: Parsing Single URL")
    print("=" * 60)

    parser = ParserFactory.create_parser('reddit')

    # 단일 URL 파싱
    url = 'https://www.reddit.com/r/python/comments/example/example_post/'
    result = parser.parse_single(url)

    print(f"\nURL: {result['url']}")
    print(f"Status: {result['status']}")
    if result['status'] == 'success':
        print(f"Title: {result.get('title', 'N/A')}")
        print(f"Comments: {result.get('comment_count', 0)}")

    return result


def example_url_list():
    """URL 리스트 파싱 예제"""
    print("\n" + "=" * 60)
    print("Example 4: Parsing URL List")
    print("=" * 60)

    parser = ParserFactory.create_parser('reddit', max_workers=5)

    # URL 리스트 직접 파싱
    urls = [
        'https://www.reddit.com/r/python/comments/example1/post1/',
        'https://www.reddit.com/r/python/comments/example2/post2/'
    ]

    results = parser.parse_multiple(urls, output_dir='parsed_reddit')

    success_count = parser.get_success_count(results)
    print(f"\nParsing completed: {success_count} successful out of {len(results)} total")

    return results


if __name__ == '__main__':
    print("\n")
    print("=" * 60)
    print("REDDIT PARSING EXAMPLES")
    print("=" * 60)
    print("\n")

    # 실제 사용 시에는 원하는 예제의 주석을 해제하세요

    # Example 1: 팩토리 패턴 사용
    # example_using_factory()

    # Example 2: 직접 import 사용
    # example_using_direct_import()

    # Example 3: 단일 URL 파싱
    # example_single_url()

    # Example 4: URL 리스트 파싱
    # example_url_list()

    print("\n[NOTE] Uncomment the examples above to run them")
    print("       Replace the example URLs with real Reddit URLs\n")
