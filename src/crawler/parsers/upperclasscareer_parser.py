#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Upperclasscareer Parser
Parse articles from upperclasscareer.com
"""

from crawler.core.base_parser import BaseParser
from typing import Dict, Any


class UpperclasscareerParser(BaseParser):
    """Parser for upperclasscareer.com articles"""

    def __init__(self, max_workers: int = 3, log_level: int = 20, format_preset: str = None):
        """Initialize parser (format_preset is ignored, for compatibility)"""
        super().__init__(max_workers=max_workers, log_level=log_level)

    def _get_logger_name(self) -> str:
        """Get logger name"""
        return 'upperclasscareer_parser'

    def parse_single(self, url: str) -> Dict[str, Any]:
        """
        Parse a single upperclasscareer.com article

        Args:
            url: Article URL

        Returns:
            Parsed article data
        """
        return self.parse_with_extractor(
            url=url,
            parser_name='upperclasscareer',
            default_author='Unknown',
            custom_content_selectors=[
                ('div', {'class': 'entry-content'}),
                ('article', {}),
            ],
            use_paragraphs=True
        )
