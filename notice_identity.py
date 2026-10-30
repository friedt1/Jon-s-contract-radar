"""Stable identity for the same public notice linked through tracking variants.

Only discard known marketing parameters. Bid IDs, solicitation keys, pagination,
and unknown query parameters are retained; those may identify different notices.
This module never claims a notice is open, current, or geographically eligible.
"""
import hashlib
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_KEYS = frozenset({
    "fbclid", "gclid", "gbraid", "wbraid", "msclkid",
    "mc_cid", "mc_eid", "igshid", "ref_src",
})


def canonical_url(url):
    if not isinstance(url, str) or not url or any(ord(c) < 33 or ord(c) == 127 or c == "\\" for c in url):
        return ""
    try:
        parts = urlsplit(url)
        if parts.scheme.lower() not in ("https", "http") or not parts.hostname:
            return ""
        if parts.username is not None or parts.password is not None:
            return ""
        port = parts.port
        host = parts.hostname.lower()
        if ":" in host:
            host = "[" + host + "]"
        default = 443 if parts.scheme.lower() == "https" else 80
        netloc = host + (":" + str(port) if port is not None and port != default else "")
        # Leave all substantive query parameters intact, including duplicate
        # bidID keys. Do not strip generic 'ref' or arbitrary unknown keys.
        query = parts.query
        if query:
            pairs = parse_qsl(query, keep_blank_values=True)
            # Signed and token-bearing URLs can be order- and byte-sensitive.
            # Do not rewrite their query strings, even to remove tracking.
            protected = any(
                key.lower() in {"sig", "signature", "token", "auth", "api_key"}
                or key.lower().startswith(("x-amz-", "x-goog-"))
                for key, _ in pairs
            )
            if not protected:
                filtered = [(key, value) for key, value in pairs
                            if not (key.lower().startswith("utm_")
                                    or key.lower() in _TRACKING_KEYS)]
                # Ordinary distinct query keys are order-independent for
                # notice identity. Repeated keys may be order-sensitive:
                # retain their original order so different bids cannot merge.
                if len({key.lower() for key, _ in filtered}) == len(filtered):
                    filtered.sort(key=lambda pair: pair[0])
                # Normalize ordinary parameter order even when there are no
                # tracking parameters to remove. Previously, query variants
                # without utm_* were not deduplicated at all.
                if filtered != pairs:
                    query = urlencode(filtered)
        return urlunsplit((parts.scheme.lower(), netloc, parts.path, query, ""))
    except (ValueError, TypeError):
        return ""


def notice_id(url):
    normalized = canonical_url(url)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16] if normalized else ""
