#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SFGate Parser
Parse articles from sfgate.com
"""

from crawler.core.base_parser import BaseParser
from typing import Dict, Any


class SFGateParser(BaseParser):
    """Parser for sfgate.com articles"""

    def __init__(self, max_workers: int = 3, log_level: int = 20, format_preset: str = None):
        """Initialize parser (format_preset is ignored, for compatibility)"""
        super().__init__(max_workers=max_workers, log_level=log_level)

    def _get_logger_name(self) -> str:
        """Get logger name"""
        return 'sfgate_parser'

    def parse_single(self, url: str) -> Dict[str, Any]:
        """
        Parse a single sfgate.com article

        Args:
            url: Article URL

        Returns:
            Parsed article data
        """
        # SFGate requires specific headers to avoid 403
        custom_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }

        return self.parse_with_extractor(
            url=url,
            parser_name='sfgate',
            default_author='Unknown',
            custom_content_selectors=[
                ('article', {}),
                ('main', {}),
            ],
            use_paragraphs=True,
            headers=custom_headers
        )
