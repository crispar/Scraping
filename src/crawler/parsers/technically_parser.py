#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Technical.ly Parser
Parse articles from technical.ly
"""

from crawler.core.base_parser import BaseParser
from typing import Dict, Any


class TechnicallyParser(BaseParser):
    """Parser for technical.ly articles"""

    def __init__(self, max_workers: int = 3, log_level: int = 20, format_preset: str = None):
        """Initialize parser (format_preset is ignored, for compatibility)"""
        super().__init__(max_workers=max_workers, log_level=log_level)

    def _get_logger_name(self) -> str:
        """Get logger name"""
        return 'technically_parser'

    def parse_single(self, url: str) -> Dict[str, Any]:
        """
        Parse a single technical.ly article

        Args:
            url: Article URL

        Returns:
            Parsed article data
        """
        return self.parse_with_extractor(
            url=url,
            parser_name='technical.ly',
            default_author='Unknown',
            custom_content_selectors=[
                ('div', {'class': 'entry-content'}),
                ('article', {}),
            ],
            use_paragraphs=True
        )
