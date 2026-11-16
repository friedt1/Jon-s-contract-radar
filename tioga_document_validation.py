"""Offline response-evidence gate for Tioga bid documents; never fetches URLs.

The caller must supply the *final* response URL after redirects and response
bytes. A passing result is only document evidence, not bid eligibility.
"""
from urllib.parse import urlsplit
import re

OFFICIAL_HOST = 'tiogacountyny.com'


def document_response_status(requested_url, final_url, status_code, content_type, body):
    """Return a fail-closed reason or 'verified_document_response'."""
    try:
        requested = urlsplit(requested_url)
        final = urlsplit(final_url)
        for raw in (requested_url, final_url):
            if (not isinstance(raw, str) or any(ord(ch) <= 32 or ord(ch) == 127 or ch == '\\' for ch in raw)
                    or re.search(r'%(?:0[0-9a-f]|1[0-9a-f]|20|5c|7f)', raw, re.I)):
                return 'untrusted_url'
        for parsed in (requested, final):
            if (parsed.scheme != 'https' or parsed.hostname != OFFICIAL_HOST
                    or parsed.port not in (None, 443)
                    or parsed.username is not None or parsed.password is not None
                    or parsed.fragment):
                return 'untrusted_url'
    except (TypeError, ValueError, AttributeError):
        return 'untrusted_url'
    if status_code != 200:
        return 'http_error'
    if not isinstance(body, bytes) or not body:
        return 'empty_or_invalid_body'
    media_type = (content_type or '').split(';', 1)[0].strip().lower()
    if media_type == 'application/pdf' and body.startswith(b'%PDF-'):
        return 'verified_document_response'
    return 'unsupported_or_mismatched_document'
