#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Web Content Extractor - Flask Web Application

GUI와 동일한 CrawlerService/ParserFactory를 사용하여
웹 브라우저에서 콘텐츠 추출 기능을 제공합니다.
"""

import os
import sys
import time
import uuid
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from flask import Flask, render_template, request, jsonify

# Ensure src directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(current_dir, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from crawler.factory import ParserFactory
from crawler.services.crawler_service import CrawlerService
from crawler.utils.url_validator import URLValidator


def _validate_url_or_error(url: str):
    """Validate URL, returning (cleaned_url, flask_error_response_or_None)."""
    url = (url or '').strip()
    is_valid, error_msg = URLValidator.validate(url)
    if not is_valid:
        return url, (jsonify({'error': error_msg}), 400)
    return url, None


def _build_result_dict(raw: dict, url: str, platform: str) -> dict:
    """Build standardized result dict from raw parser output."""
    return {
        'url': raw.get('url', url),
        'title': raw.get('title', 'Unknown'),
        'author': raw.get('author', 'Unknown'),
        'date': raw.get('date', 'Unknown'),
        'content': raw.get('content', ''),
        'parser': raw.get('parser', platform),
        'status': raw.get('status', ''),
    }


# ---------------------------------------------------------------------------
# 비동기 추출 작업 저장소 (in-memory)
#
# 본문 이미지 VLM 해석이 붙으면 추출이 수 분 걸릴 수 있는데, 단일 HTTP 요청을
# 그 시간 내내 열어두면 모바일 브라우저/셀룰러 망이 유휴 연결을 끊어버려
# "Failed to fetch"가 뜬다. 그래서 POST는 job_id만 즉시 돌려주고 실제 추출은
# 백그라운드 워커 풀에서 돌린 뒤, 클라이언트가 짧은 폴링으로 결과를 가져간다.
#
# 주의: 이 저장소는 프로세스 로컬이므로 gunicorn은 반드시 단일 워커로 띄워야
# 한다(Dockerfile: --workers 1 --threads N --worker-class gthread). 워커가
# 여러 개면 POST를 받은 워커와 폴링을 받은 워커가 달라 job을 못 찾는다.
# ---------------------------------------------------------------------------
_JOB_TTL = 1800  # 30분 지난 작업은 정리


def _env_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.environ.get(name, default)))
    except ValueError:
        return default


class JobStore:
    """
    추출 작업 저장소 + 크기 제한 워커 풀.

    요청마다 스레드를 새로 띄우면 요청이 몰릴 때 스레드와 VLM 호출이 무제한으로
    늘어난다. 동시 실행은 워커 수로, 대기열은 max_pending 으로 제한하고 넘치면
    호출부가 429 로 거절한다.
    """

    def __init__(self, workers: int, max_pending: int):
        self._jobs = {}
        self._lock = threading.Lock()
        self._max_pending = max_pending
        self._executor = ThreadPoolExecutor(
            max_workers=workers, thread_name_prefix='extract'
        )

    def _purge_expired(self):
        """TTL 지난 작업 제거 (호출자가 _lock 을 잡은 상태여야 함)."""
        now = time.time()
        for jid in [j for j, job in self._jobs.items() if now - job['created'] > _JOB_TTL]:
            del self._jobs[jid]

    def submit(self, fn, *args):
        """작업을 대기열에 넣고 job_id 반환. 대기열이 가득 차면 None."""
        with self._lock:
            self._purge_expired()
            in_flight = sum(1 for job in self._jobs.values() if job['status'] == 'pending')
            if in_flight >= self._max_pending:
                return None
            job_id = uuid.uuid4().hex
            self._jobs[job_id] = {
                'status': 'pending', 'created': time.time(),
                'result': None, 'error': None,
            }
        self._executor.submit(self._run, job_id, fn, *args)
        return job_id

    def _run(self, job_id, fn, *args):
        try:
            update = {'status': 'done', 'result': fn(*args)}
        except Exception as e:  # noqa: BLE001 - 어떤 예외든 작업 실패로 기록
            logging.getLogger('web_app').exception(f"Job {job_id} failed")
            update = {'status': 'error', 'error': str(e)}
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(update)

    def get(self, job_id):
        """작업 상태의 사본 반환 (없거나 만료됐으면 None)."""
        with self._lock:
            self._purge_expired()
            job = self._jobs.get(job_id)
            return dict(job) if job else None


def create_app():
    """Flask application factory"""
    app = Flask(
        __name__,
        template_folder=os.path.join(current_dir, 'templates'),
        static_folder=os.path.join(current_dir, 'static'),
    )
    app.config['JSON_AS_ASCII'] = False

    service = CrawlerService()
    logger = logging.getLogger('web_app')
    # 동시 추출 수. VLM 서버 슬롯(기본 2)을 여러 작업이 나눠 쓰므로 크게 잡을 이유가 없다.
    jobs = JobStore(
        workers=_env_int('EXTRACT_WORKERS', 2),
        max_pending=_env_int('EXTRACT_MAX_PENDING', 20),
    )

    def _extract_payload(url: str) -> dict:
        """URL을 추출해 프론트가 기대하는 표준 응답 dict로 변환."""
        result = service.extract_content(url)
        return {
            'success': result.success,
            'message': result.message,
            'platform': result.platform,
            'formatted_text': result.formatted_text,
            'result': _build_result_dict(result.raw_result, url, result.platform),
        }

    @app.route('/')
    def index():
        parsers = ParserFactory.get_available_parsers()
        return render_template('index.html', parsers=parsers)

    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'parsers_count': len(ParserFactory.get_available_parsers()),
        })

    @app.route('/api/parsers')
    def get_parsers():
        return jsonify({
            'parsers': ParserFactory.get_available_parsers(),
        })

    @app.route('/api/detect', methods=['POST'])
    def detect_platform():
        data = request.get_json(silent=True) or {}
        url, error = _validate_url_or_error(data.get('url', ''))
        if error:
            return error

        platform = service.detect_platform(url)
        return jsonify({'platform': platform, 'url': url})

    @app.route('/api/extract', methods=['POST'])
    def extract_content():
        data = request.get_json(silent=True) or {}
        url, error = _validate_url_or_error(data.get('url', ''))
        if error:
            return error
        blocked = URLValidator.check_public_host(url)
        if blocked:
            return jsonify({'error': blocked}), 400

        # 하위호환: {"sync": true}면 예전처럼 동기로 결과를 바로 반환한다
        # (외부 스크립트/짧은 페이지용). 웹 UI는 아래 비동기 경로를 쓴다.
        if data.get('sync'):
            logger.info(f"Extracting (sync): {url}")
            return jsonify(_extract_payload(url))

        # 비동기: 즉시 job_id 반환 → 워커 풀에서 추출 → 클라 폴링
        job_id = jobs.submit(_extract_payload, url)
        if job_id is None:
            return jsonify({'error': '추출 요청이 많습니다. 잠시 후 다시 시도해주세요.'}), 429
        logger.info(f"Extracting (async job={job_id}): {url}")
        return jsonify({'job_id': job_id, 'status': 'pending'}), 202

    @app.route('/api/extract/result/<job_id>', methods=['GET'])
    def extract_result(job_id):
        job = jobs.get(job_id)
        if job is None:
            return jsonify({'status': 'not_found'}), 404
        if job['status'] == 'pending':
            return jsonify({'status': 'pending'}), 200
        if job['status'] == 'error':
            return jsonify({'status': 'error', 'message': job['error']}), 200
        payload = dict(job['result'])
        payload['status'] = 'done'
        return jsonify(payload), 200

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
