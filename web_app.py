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
# 백그라운드 스레드에서 돌린 뒤, 클라이언트가 짧은 폴링으로 결과를 가져간다.
#
# 주의: 이 저장소는 프로세스 로컬이므로 gunicorn은 반드시 단일 워커로 띄워야
# 한다(Dockerfile: --workers 1 --threads N --worker-class gthread). 워커가
# 여러 개면 POST를 받은 워커와 폴링을 받은 워커가 달라 job을 못 찾는다.
# ---------------------------------------------------------------------------
_jobs = {}
_jobs_lock = threading.Lock()
_JOB_TTL = 1800  # 30분 지난 완료 작업은 정리


def _purge_old_jobs():
    """오래된 작업 제거 (호출자가 _jobs_lock을 이미 잡은 상태여야 함)."""
    now = time.time()
    for jid in list(_jobs.keys()):
        if now - _jobs[jid]['created'] > _JOB_TTL:
            _jobs.pop(jid, None)


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

    def _run_extraction(job_id: str, url: str):
        """백그라운드 스레드: 추출 후 결과를 작업 저장소에 기록."""
        try:
            payload = _extract_payload(url)
            with _jobs_lock:
                if job_id in _jobs:
                    _jobs[job_id].update(status='done', result=payload)
        except Exception as e:  # noqa: BLE001 - 어떤 예외든 작업 실패로 기록
            logger.exception(f"Extraction failed for {url}")
            with _jobs_lock:
                if job_id in _jobs:
                    _jobs[job_id].update(status='error', error=str(e))

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

        # 하위호환: {"sync": true}면 예전처럼 동기로 결과를 바로 반환한다
        # (외부 스크립트/짧은 페이지용). 웹 UI는 아래 비동기 경로를 쓴다.
        if data.get('sync'):
            logger.info(f"Extracting (sync): {url}")
            return jsonify(_extract_payload(url))

        # 비동기: 즉시 job_id 반환 → 백그라운드 스레드에서 추출 → 클라 폴링
        job_id = uuid.uuid4().hex
        with _jobs_lock:
            _purge_old_jobs()
            _jobs[job_id] = {
                'status': 'pending',
                'created': time.time(),
                'result': None,
                'error': None,
            }
        logger.info(f"Extracting (async job={job_id}): {url}")
        threading.Thread(
            target=_run_extraction, args=(job_id, url), daemon=True
        ).start()
        return jsonify({'job_id': job_id, 'status': 'pending'}), 202

    @app.route('/api/extract/result/<job_id>', methods=['GET'])
    def extract_result(job_id):
        with _jobs_lock:
            job = _jobs.get(job_id)
            if job is None:
                return jsonify({'status': 'not_found'}), 404
            status = job['status']
            if status == 'pending':
                return jsonify({'status': 'pending'}), 200
            if status == 'error':
                return jsonify({'status': 'error', 'message': job['error']}), 200
            payload = dict(job['result'])  # done
        payload['status'] = 'done'
        return jsonify(payload), 200

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
