"""Validate procurement entrypoints before counting or fetching direct sources.

This is URL hygiene, NOT independent proof that a site is an official
publisher, permits automated access, or exposes individual bid notices.
"""
import re
from urllib.parse import urlsplit

DIRECT_MODES = frozenset({"direct_page", "official_feed", "authorized_api"})
_HOST_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$", re.I)
_ENCODED_CONTROL = re.compile(r"%(?:0[0-9a-f]|1[0-9a-f]|7f)", re.I)


def valid_public_https_url(value):
    """Require a conventional, uncredentialed HTTPS hostname and safe URL."""
    if not isinstance(value, str) or not value or any(
        ord(char) < 33 or ord(char) == 127 or char == "\\" for char in value
    ) or _ENCODED_CONTROL.search(value):
        return False
    try:
        parsed = urlsplit(value)
        host = parsed.hostname
        if (parsed.scheme != "https" or not host
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443)
                or parsed.fragment):
            return False
        labels = host.split(".")
        return (len(labels) >= 2 and all(_HOST_LABEL.fullmatch(label) for label in labels)
                and host.lower() != "localhost")
    except ValueError:
        return False


def direct_configured(source):
    return (source.get("mode") in DIRECT_MODES
            and source.get("verified_url") is True
            and valid_public_https_url(source.get("url")))
