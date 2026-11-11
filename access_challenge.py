"""Detect explicit anti-bot interstitials returned as HTTP 200 HTML.

This is a narrow, fail-closed signal; not an authorization check. Ordinary
procurement pages mentioning CAPTCHA or Cloudflare must not be rejected.
"""
import re


class AccessChallenge(RuntimeError):
    """Publisher returned an interstitial, not a public procurement document."""


def challenge_kind(body, content_type=""):
    """Return a stable diagnostic label, or None when no clear challenge exists."""
    if not isinstance(body, (bytes, str)):
        return None
    sample = (body[:131072].decode("utf-8", "replace") if isinstance(body, bytes)
              else body[:131072]).lower()
    # Require an HTML document opening, not a marker embedded in a PDF, JSON,
    # or a plain-text procurement attachment.
    if not re.match(r"^\s*(?:<!doctype\s+html\b|<html\b)", sample):
        return None
    if ("/cdn-cgi/challenge-platform/" in sample or "cf-chl-" in sample
            or re.search(r"<title[^>]*>\s*attention required!?\s*\|\s*cloudflare", sample)):
        return "cloudflare_challenge"
    if ("aws-waf-token" in sample and
            ("captcha" in sample or "challenge" in sample)):
        return "waf_challenge"
    if (re.search(r"(?:id|class)\s*=\s*['\"][^'\"]*(?:px-captcha|h-captcha|g-recaptcha|arkose)", sample)
            and re.search(r"verify you are human|robot check|captcha", sample)):
        return "captcha_challenge"
    return None
