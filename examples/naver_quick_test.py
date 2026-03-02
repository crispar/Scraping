"""
네이버 블로그 빠른 테스트 - 파일 출력 포함
"""

from crawler.factory import ParserFactory

# 파서 생성
parser = ParserFactory.create_parser('naver', max_workers=3, delay=1.0)

# URL 리스트 (실제 URL로 변경하세요)
urls = [
    'https://blog.naver.com/kckh3333/224028690459'
    # 더 추가 가능
]

# 파싱 실행 - 파일로 저장됨!
print("Parsing started...")
results = parser.parse_multiple_blogs(urls, output_dir='parsed_blogs')

# 결과 확인
success_count = parser.get_success_count(results)
print(f"\nParsing completed!")
print(f"Success: {success_count} / {len(results)}")
print(f"\nFiles saved to: parsed_blogs/")
print("  - parsed_blogs_YYYYMMDD_HHMMSS.csv")
print("  - parsed_blogs_YYYYMMDD_HHMMSS.txt")
