"""
Output Strategy 모듈

Strategy Pattern을 사용하여 다양한 출력 형식을 지원합니다.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any
import pandas as pd
import json
import os
from datetime import datetime
from crawler.core.config import FileConfig
from crawler.constants import ParsingStatus, OutputConstants


class OutputStrategy(ABC):
    """출력 전략 추상 클래스"""

    def __init__(self, logger=None):
        """
        OutputStrategy 초기화

        Args:
            logger: 로거 객체 (선택)
        """
        self.logger = logger
        self.config = FileConfig()
        self.constants = OutputConstants()

    @abstractmethod
    def save(self, results: Any, output_path: str) -> None:
        """
        결과 저장 (추상 메서드)

        Args:
            results: 파싱 결과
            output_path: 저장 경로
        """
        pass

    def _log_info(self, message: str) -> None:
        """로그 출력 헬퍼"""
        if self.logger:
            self.logger.info(message)

    def _log_error(self, message: str) -> None:
        """에러 로그 출력 헬퍼"""
        if self.logger:
            self.logger.error(message)


class CSVOutputStrategy(OutputStrategy):
    """CSV 출력 전략"""

    def save(self, results: Any, output_path: str) -> None:
        """
        CSV 파일로 저장

        Args:
            results: 파싱 결과 (DataFrame 또는 리스트)
            output_path: 저장 경로
        """
        try:
            self._log_info(f"Saving results as CSV to: {output_path}")

            # DataFrame으로 변환
            if isinstance(results, list):
                df = pd.DataFrame(results)
            else:
                df = results.copy()

            # comments와 links 컬럼을 문자열로 변환
            if 'comments' in df.columns:
                df['comments'] = df['comments'].apply(lambda x: str(x))
            if 'links' in df.columns:
                df['links'] = df['links'].apply(lambda x: str(x))

            df.to_csv(output_path, index=False, encoding=self.config.encoding_csv)
            self._log_info(f"Saved CSV file: {output_path}")

        except Exception as e:
            self._log_error(f"Error saving CSV: {str(e)}")
            raise


class JSONOutputStrategy(OutputStrategy):
    """JSON 출력 전략"""

    def save(self, results: Any, output_path: str) -> None:
        """
        JSON 파일로 저장

        Args:
            results: 파싱 결과 (리스트 또는 DataFrame)
            output_path: 저장 경로
        """
        try:
            self._log_info(f"Saving results as JSON to: {output_path}")

            # 리스트로 변환
            if isinstance(results, pd.DataFrame):
                data = results.to_dict('records')
            else:
                data = results

            with open(output_path, 'w', encoding=self.config.encoding_text) as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self._log_info(f"Saved JSON file: {output_path}")

        except Exception as e:
            self._log_error(f"Error saving JSON: {str(e)}")
            raise


class TextOutputStrategy(OutputStrategy):
    """텍스트 출력 전략 (상세 버전)"""

    def save(self, results: Any, output_path: str) -> None:
        """
        상세한 텍스트 파일로 저장

        Args:
            results: 파싱 결과
            output_path: 저장 경로
        """
        try:
            self._log_info(f"Saving results as text to: {output_path}")

            # 리스트로 변환
            if isinstance(results, pd.DataFrame):
                data = results.to_dict('records')
            else:
                data = results

            with open(output_path, 'w', encoding=self.config.encoding_text) as f:
                for row in data:
                    if row['status'] == ParsingStatus.SUCCESS:
                        self._write_post(f, row)

            self._log_info(f"Saved text file: {output_path}")

        except Exception as e:
            self._log_error(f"Error saving text: {str(e)}")
            raise

    @abstractmethod
    def _write_post(self, file, post: Dict[str, Any]) -> None:
        """
        단일 포스트 작성 (하위 클래스에서 구현)

        Args:
            file: 파일 객체
            post: 포스트 데이터
        """
        pass


class RedditTextOutputStrategy(TextOutputStrategy):
    """Reddit 텍스트 출력 전략"""

    def _write_post(self, file, post: Dict[str, Any]) -> None:
        """Reddit 포스트를 상세 텍스트 형식으로 작성"""
        file.write(f"URL: {post['url']}\n")
        file.write(f"Post ID: {post['post_id']}\n")
        file.write(f"제목: {post['title']}\n")
        file.write(f"작성자: {post['author']}\n")
        file.write(f"작성일: {post['created_utc']}\n")
        file.write(f"점수: {post['score']} (상승률: {post['upvote_ratio']*100:.1f}%)\n")
        file.write(f"내용:\n{post['content']}\n")

        if post.get('links'):
            file.write(f"\n관련 링크:\n")
            for link in post['links']:
                file.write(f"- {link}\n")

        if post.get('comments'):
            file.write(f"\n댓글 ({len(post['comments'])}개):\n")
            for comment in post['comments']:
                file.write(self.constants.COMMENT_SEPARATOR + "\n")
                file.write(f"작성자: {comment['author']}\n")
                file.write(f"작성일: {comment['timestamp']}\n")
                file.write(f"점수: {comment['score']}\n")
                indent = "  " * comment.get('depth', 0)
                file.write(f"내용:\n{indent}{comment['content']}\n")

        file.write("\n" + self.constants.POST_SEPARATOR + "\n\n")


class RedditSimpleTextOutputStrategy(OutputStrategy):
    """Reddit 간단한 텍스트 출력 전략"""

    def save(self, results: Any, output_path: str) -> None:
        """
        간단한 형식으로 저장 (제목, URL, 본문, 댓글만)

        Args:
            results: 파싱 결과
            output_path: 저장 경로
        """
        try:
            self._log_info(f"Saving results in simple format to: {output_path}")

            # 리스트로 변환
            if isinstance(results, pd.DataFrame):
                data = results.to_dict('records')
            else:
                data = results

            formatted_posts = []

            for post in data:
                if post['status'] == ParsingStatus.SUCCESS:
                    post_lines = []

                    # 제목
                    if post.get('title'):
                        post_lines.append(post['title'])

                    # URL
                    if post.get('url'):
                        post_lines.append(post['url'])

                    # 본문
                    if post.get('content'):
                        post_lines.append(post['content'])

                    # 댓글
                    if post.get('comments'):
                        comment_texts = []
                        for comment in post['comments']:
                            if comment.get('content'):
                                # 댓글 깊이에 따라 들여쓰기 추가
                                indent = "  " * comment.get('depth', 0)
                                comment_texts.append(f"{indent}{comment['content']}")
                        if comment_texts:
                            post_lines.append('\n'.join(comment_texts))

                    # 하나의 포스트를 줄바꿈으로 구분하여 합치기
                    formatted_posts.append('\n\n'.join(post_lines))

            # 전체 결과를 구분자로 구분하여 저장
            with open(output_path, 'w', encoding=self.config.encoding_text) as f:
                f.write(f"\n\n{self.constants.POST_SEPARATOR_SHORT}\n\n".join(formatted_posts))

            self._log_info(f"Saved simple format file: {output_path}")

        except Exception as e:
            self._log_error(f"Error saving simple format: {str(e)}")
            raise


class NaverBlogTextOutputStrategy(TextOutputStrategy):
    """네이버 블로그 텍스트 출력 전략"""

    def _write_post(self, file, post: Dict[str, Any]) -> None:
        """네이버 블로그 포스트를 텍스트 형식으로 작성"""
        file.write(f"\n")
        file.write(f"제목: {post['title']} - {post['url']}\n")
        file.write(f"작성일: {post['date']}\n")
        file.write(f"내용:\n{post['content']}\n")
        file.write("\n" + self.constants.POST_SEPARATOR + "\n\n")


class OutputStrategyFactory:
    """
    출력 전략 팩토리 (레지스트리 패턴 적용)

    OCP 준수: 새로운 전략 추가 시 팩토리 수정 불필요
    """

    # 레지스트리: 전략 이름 -> 전략 클래스 매핑
    _registry: Dict[str, type] = {}

    # 프리셋: 플랫폼별 전략 조합
    _presets: Dict[str, List[str]] = {
        'reddit': ['csv', 'json', 'reddit_txt', 'reddit_simple'],
        'naver': ['csv', 'naver_txt']
    }

    @classmethod
    def register(cls, name: str, strategy_class: type) -> None:
        """
        새로운 출력 전략 등록 (확장 포인트)

        Args:
            name: 전략 이름
            strategy_class: 전략 클래스

        Example:
            OutputStrategyFactory.register('xml', XMLOutputStrategy)
        """
        cls._registry[name] = strategy_class

    @classmethod
    def create(cls, name: str, logger=None) -> OutputStrategy:
        """
        단일 전략 생성

        Args:
            name: 전략 이름
            logger: 로거 객체

        Returns:
            OutputStrategy 인스턴스

        Raises:
            ValueError: 등록되지 않은 전략 이름
        """
        if name not in cls._registry:
            available = ', '.join(cls._registry.keys())
            raise ValueError(f"Unknown strategy '{name}'. Available: {available}")

        return cls._registry[name](logger)

    @classmethod
    def create_preset(cls, preset_name: str, logger=None) -> Dict[str, OutputStrategy]:
        """
        프리셋에 따라 여러 전략 생성

        Args:
            preset_name: 프리셋 이름 ('reddit', 'naver')
            logger: 로거 객체

        Returns:
            전략 딕셔너리 {전략명: 전략 인스턴스}

        Raises:
            ValueError: 등록되지 않은 프리셋
        """
        if preset_name not in cls._presets:
            available = ', '.join(cls._presets.keys())
            raise ValueError(f"Unknown preset '{preset_name}'. Available: {available}")

        strategies = {}
        for strategy_name in cls._presets[preset_name]:
            # 별칭 처리 (reddit_txt -> txt)
            key = strategy_name.replace('reddit_', '').replace('naver_', '')
            strategies[key] = cls.create(strategy_name, logger)

        return strategies

    @classmethod
    def register_preset(cls, preset_name: str, strategy_names: List[str]) -> None:
        """
        새로운 프리셋 등록

        Args:
            preset_name: 프리셋 이름
            strategy_names: 포함할 전략 이름 리스트

        Example:
            OutputStrategyFactory.register_preset('twitter', ['csv', 'json'])
        """
        cls._presets[preset_name] = strategy_names

    # 하위 호환성 메서드
    @staticmethod
    def create_reddit_strategies(logger=None) -> Dict[str, OutputStrategy]:
        """Reddit용 출력 전략 (하위 호환성)"""
        return OutputStrategyFactory.create_preset('reddit', logger)

    @staticmethod
    def create_naver_strategies(logger=None) -> Dict[str, OutputStrategy]:
        """네이버용 출력 전략 (하위 호환성)"""
        return OutputStrategyFactory.create_preset('naver', logger)


# 전략 자동 등록
def _initialize_strategies():
    """내장 전략 자동 등록"""
    OutputStrategyFactory.register('csv', CSVOutputStrategy)
    OutputStrategyFactory.register('json', JSONOutputStrategy)
    OutputStrategyFactory.register('reddit_txt', RedditTextOutputStrategy)
    OutputStrategyFactory.register('reddit_simple', RedditSimpleTextOutputStrategy)
    OutputStrategyFactory.register('naver_txt', NaverBlogTextOutputStrategy)


# 모듈 로드 시 자동 등록
_initialize_strategies()
