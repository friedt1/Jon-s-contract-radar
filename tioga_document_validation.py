"""Offline response-evidence gate for Tioga bid documents; never fetches URLs.

The caller must supply the *final* response URL after redirects and response
bytes. A passing result is only document evidence, not bid eligibility.
"""
from urllib.parse import urlsplit
import re

OFFICIAL_HOST = 'tiogacountyny.com'
MAX_DOCUMENT_BYTES = 25 * 1024 * 1024  # Bound offline evidence processing; not a fetch limit.


def document_response_status(requested_url, final_url, status_code, content_type, body):
    """Return a fail-closed reason or 'verified_document_response'."""
    try:
        requested = urlsplit(requested_url)
        final = urlsplit(final_url)
        for raw in (requested_url, final_url):
            if (not isinstance(raw, str) or any(ord(ch) <= 32 or ord(ch) == 127 or ch == '\\' for ch in raw)
                    or re.search(r'%(?:0[0-9a-f]|1[0-9a-f]|20|2f|5c|7f|(?:25)+(?:0[0-9a-f]|1[0-9a-f]|20|2f|5c|7f))', raw, re.I)):
                return 'untrusted_url'
        for parsed in (requested, final):
            if (parsed.scheme != 'https' or parsed.hostname != OFFICIAL_HOST
                    or parsed.port not in (None, 443)
                    or parsed.username is not None or parsed.password is not None
                    or parsed.query or parsed.fragment):
                return 'untrusted_url'
    except (TypeError, ValueError, AttributeError):
        return 'untrusted_url'
    if status_code != 200:
        return 'http_error'
    if not isinstance(body, bytes) or not body:
        return 'empty_or_invalid_body'
    if len(body) > MAX_DOCUMENT_BYTES:
        return 'document_size_limit_exceeded'
    if not isinstance(content_type, str):
        return 'unsupported_or_mismatched_document'
    # Reject control characters before parsing MIME: a forged header must not
    # be accepted merely because its first line says application/pdf.
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in content_type):
        return 'unsupported_or_mismatched_document'
    media_type = content_type.split(';', 1)[0].strip().lower()
    if (media_type == 'application/pdf' and body.startswith(b'%PDF-')
            and body.rstrip(bytes((0, 9, 10, 12, 13, 32))).endswith(b'%%EOF')):
        return 'verified_document_response'
    return 'unsupported_or_mismatched_document'
