"""URL validation utility."""

from urllib.parse import urlparse
from typing import Tuple, Optional


class URLValidator:
    """Shared URL validation logic for GUI and web app."""

    @staticmethod
    def validate(url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a URL.

        Returns:
            (is_valid, error_message_or_None)
        """
        if not url or not url.strip():
            return False, "Please enter a URL"

        url = url.strip()
        parsed = urlparse(url)

        if parsed.scheme not in ('http', 'https'):
            return False, "Please enter a valid URL starting with http:// or https://"

        if not parsed.netloc:
            return False, "Please enter a valid URL with a domain name"

        return True, None
