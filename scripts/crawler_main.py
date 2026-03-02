"""
통합 크롤링 시스템 메인 스크립트 (리팩토링 버전)

Factory Pattern을 사용하여 의존성을 역전시키고 확장성을 높였습니다.
기존 동작을 100% 유지합니다.
"""

import argparse
import os
import logging
from datetime import datetime
from crawler.utils.logger_config import setup_logger
from crawler.factory import ParserFactory
from crawler.utils.file_manager import FileManager


def parse_arguments():
    """
    명령줄 인자 파싱

    Returns:
        argparse.Namespace: 파싱된 인자
    """
    parser = argparse.ArgumentParser(description='통합 크롤링 시스템')

    # 서브파서 생성
    subparsers = parser.add_subparsers(dest='command', help='수행할 명령')

    # Reddit 파싱 인자
    reddit_parser = subparsers.add_parser('reddit', help='Reddit 게시물 파싱')
    reddit_parser.add_argument('input_file', help='Reddit URL이 포함된 입력 파일')
    reddit_parser.add_argument('--output-dir', default='parsed_reddit', help='출력 디렉토리 (기본: parsed_reddit)')
    reddit_parser.add_argument('--batch-size', type=int, default=10, help='배치 크기 (기본: 10)')
    reddit_parser.add_argument('--min-delay', type=float, default=2.0, help='최소 요청 지연 시간 (초) (기본: 2.0)')
    reddit_parser.add_argument('--max-delay', type=float, default=4.0, help='최대 요청 지연 시간 (초) (기본: 4.0)')
    reddit_parser.add_argument('--max-workers', type=int, default=3, help='최대 작업자 수 (기본: 3)')
    reddit_parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                              default='INFO', help='로깅 레벨 (기본: INFO)')

    # 네이버 블로그 파싱 인자
    naver_parser = subparsers.add_parser('naver', help='네이버 블로그 파싱')
    naver_parser.add_argument('urls', nargs='+', help='네이버 블로그 URL 목록')
    naver_parser.add_argument('--output-dir', default='parsed_blogs', help='출력 디렉토리 (기본: parsed_blogs)')
    naver_parser.add_argument('--delay', type=float, default=1.0, help='요청 지연 시간 (초) (기본: 1.0)')
    naver_parser.add_argument('--max-workers', type=int, default=3, help='최대 작업자 수 (기본: 3)')
    naver_parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                             default='INFO', help='로깅 레벨 (기본: INFO)')

    # 파일 정리 인자
    cleanup_parser = subparsers.add_parser('cleanup', help='오래된 파일 정리')
    cleanup_parser.add_argument('directory', help='정리할 디렉토리')
    cleanup_parser.add_argument('--days', type=int, default=1, help='유지할 일수 (기본: 1)')
    cleanup_parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
                               default='INFO', help='로깅 레벨 (기본: INFO)')

    return parser.parse_args()


def get_log_level(level_str: str) -> int:
    """
    문자열 로그 레벨을 logging 모듈 상수로 변환

    Args:
        level_str: 로그 레벨 문자열 ('DEBUG', 'INFO', 등)

    Returns:
        logging 모듈 로그 레벨 상수
    """
    log_levels = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    return log_levels.get(level_str, logging.INFO)


def handle_reddit_command(args, log_level: int, logger: logging.Logger) -> None:
    """
    Reddit 파싱 커맨드 처리

    Args:
        args: 파싱된 명령줄 인자
        log_level: 로그 레벨
        logger: 로거 객체
    """
    logger.info(f"Starting Reddit parsing from file: {args.input_file}")

    # 팩토리를 통해 파서 생성 (의존성 역전)
    parser = ParserFactory.create_parser(
        'reddit',
        max_workers=args.max_workers,
        min_delay=args.min_delay,
        max_delay=args.max_delay,
        log_level=log_level
    )

    results = parser.parse_from_file(args.input_file, args.output_dir)

    if results is not None:
        success_count = parser.get_success_count(results)
        logger.info(f"Reddit parsing completed: {success_count} successful out of {len(results)} total")


def handle_naver_command(args, log_level: int, logger: logging.Logger) -> None:
    """
    네이버 블로그 파싱 커맨드 처리

    Args:
        args: 파싱된 명령줄 인자
        log_level: 로그 레벨
        logger: 로거 객체
    """
    logger.info(f"Starting Naver blog parsing for {len(args.urls)} URLs")

    # 팩토리를 통해 파서 생성 (의존성 역전)
    parser = ParserFactory.create_parser(
        'naver',
        max_workers=args.max_workers,
        delay=args.delay,
        log_level=log_level
    )

    results = parser.parse_multiple_blogs(args.urls, args.output_dir)

    success_count = parser.get_success_count(results)
    logger.info(f"Naver blog parsing completed: {success_count} successful out of {len(args.urls)} total")


def handle_cleanup_command(args, log_level: int, logger: logging.Logger) -> None:
    """
    파일 정리 커맨드 처리

    Args:
        args: 파싱된 명령줄 인자
        log_level: 로그 레벨
        logger: 로거 객체
    """
    logger.info(f"Cleaning up files older than {args.days} days in {args.directory}")

    # FileManager를 통해 파일 정리
    file_manager = FileManager(logger)
    deleted_count = file_manager.delete_old_files(args.directory, days=args.days)

    logger.info(f"Cleanup completed: {deleted_count} files deleted")


def main():
    """
    메인 실행 함수
    """
    args = parse_arguments()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 로그 설정
    if args.command:
        log_level = get_log_level(args.log_level)
        logger = setup_logger(f'crawler_main_{args.command}_{timestamp}', level=log_level)
        logger.info(f"Starting {args.command} command with args: {args}")
    else:
        logger = setup_logger(f'crawler_main_{timestamp}')
        logger.info("No command specified. Use -h for help.")
        return

    try:
        # 커맨드 핸들러 매핑 (Strategy Pattern 변형)
        command_handlers = {
            'reddit': handle_reddit_command,
            'naver': handle_naver_command,
            'cleanup': handle_cleanup_command
        }

        # 해당 커맨드 핸들러 실행
        if args.command in command_handlers:
            command_handlers[args.command](args, log_level, logger)
        else:
            logger.error(f"Unknown command: {args.command}")
            return

    except Exception as e:
        logger.error(f"Error in {args.command} command: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
