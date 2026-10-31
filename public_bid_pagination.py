"""Bounded navigation of explicitly public county bid listing pages.

Never used on NYSCR, BidNet or PennBid; those require a permitted
listing/export interface. Do not follow off-host or unrelated links.
"""
import re
from urllib.parse import urljoin, urlparse, parse_qsl

PUBLIC_LISTINGS = frozenset({
    "Chemung County bids", "Steuben County bids",
    "Schuyler County purchasing", "Tompkins County purchasing",
    "Elmira City bids",
})
PAGE_KEYS = frozenset({"page", "pagenumber", "pageno", "skip", "offset", "start"})
_ENCODED_CONTROL = re.compile(r"%(?:0[0-9a-f]|1[0-9a-f]|7f)", re.I)
MAX_PAGES = 3
MAX_PUBLIC_DETAILS = 36


def pagination_label(label):
    """Recognize common public-listing pager labels, not arbitrary navigation."""
    label = " ".join(label.lower().split())
    return bool(re.fullmatch(
        r"(?:next(?: page)?(?: [>»›]+| [0-9]+)?|[>»›]+|"
        r"page [0-9]+(?: of [0-9]+)?|[0-9]+(?: of [0-9]+)?)",
        label,
    ))


def next_pages(links, listing_url, seen):
    """Return bounded same-page listing URLs, never individual bids or logins.

    The label must indicate pagination, the query must contain a numeric page
    cursor, and the URL must remain on the same HTTPS host and path. This is
    only discovery of public listings, not evidence of an open solicitation.
    """
    base = urlparse(listing_url)
    found = []
    for label, href, _ in links:
        if not isinstance(href, str) or not href or not pagination_label(label):
            continue
        if (any(ord(c) < 33 or ord(c) == 127 or c == "\\" for c in href)
                or _ENCODED_CONTROL.search(href)):
            continue
        try:
            url = urljoin(listing_url, href)
            parsed = urlparse(url)
            if (parsed.scheme != "https" or parsed.hostname != base.hostname
                    or parsed.username is not None or parsed.password is not None
                    or parsed.port not in (None, 443)
                    or parsed.path.lower().rstrip("/") != base.path.lower().rstrip("/")):
                continue
            # Keep every cursor, including duplicate/mixed-case keys and empty
            # values. Collapsing into a dict could conceal a malformed cursor.
            params = [(key.lower(), value) for key, value in
                      parse_qsl(parsed.query, keep_blank_values=True)]
            if any(key == "bidid" for key, _ in params):
                continue  # a bid detail must never masquerade as a pager
            cursors = [value for key, value in params if key in PAGE_KEYS]
            if not cursors or not all(value.isascii() and value.isdigit()
                                      for value in cursors):
                continue
            # Fragments never change the listing page; avoid duplicate fetches.
            url = parsed._replace(fragment="").geturl()
            if url not in seen and url not in found:
                found.append(url)
        except ValueError:
            continue
    return found
