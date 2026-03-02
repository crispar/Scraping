#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Web Content Extractor - Flask Web Application

GUI와 동일한 CrawlerService/ParserFactory를 사용하여
웹 브라우저에서 콘텐츠 추출 기능을 제공합니다.
"""

import os
import sys
import logging

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

        logger.info(f"Extracting: {url}")
        result = service.extract_content(url)

        return jsonify({
            'success': result.success,
            'message': result.message,
            'platform': result.platform,
            'formatted_text': result.formatted_text,
            'result': _build_result_dict(result.raw_result, url, result.platform),
        })

    return app


if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
