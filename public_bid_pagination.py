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


def valid_pagination_redirect(requested, final):
    """Accept a fetched page only if its publisher kept the same listing/cursor.

    A public pager can redirect to a login, an unrelated bid detail, the
    first page, or another host. Those responses must not be treated as a
    second listing page, even if they contain tree-service keywords.
    """
    if not isinstance(final, str) or not final or any(
        ord(char) < 33 or ord(char) == 127 or char == "\\\\" for char in final
    ) or _ENCODED_CONTROL.search(final):
        return False
    try:
        before, after = urlparse(requested), urlparse(final)
        if (before.scheme != "https" or after.scheme != "https"
                or before.hostname != after.hostname
                or before.port not in (None, 443) or after.port not in (None, 443)
                or after.username is not None or after.password is not None
                or after.fragment
                or before.path.lower().rstrip("/") != after.path.lower().rstrip("/")):
            return False
        def query_parts(parts):
            # Preserve every non-cursor filter and its value. A redirect
            # keeping page=2 but replacing status=open with status=closed,
            # adding a login flag, or dropping a category is not the page
            # we requested. Cursor key casing is harmless; other keys may
            # be case-sensitive on the publisher.
            return [(key.lower() if key.lower() in PAGE_KEYS else key, value)
                    for key, value in parse_qsl(parts.query, keep_blank_values=True)]
        original, destination = query_parts(before), query_parts(after)
        cursors = [(key, value) for key, value in original if key in PAGE_KEYS]
        return (bool(cursors)
                and not any(key.lower() == "bidid" for key, _ in original + destination)
                and sorted(original) == sorted(destination)
                and all(value.isascii() and value.isdigit()
                        for _, value in cursors)
                and all(len({value for key, value in cursors if key == name}) == 1
                        for name, _ in cursors))
    except ValueError:
        return False


def next_pages(links, listing_url, seen):
    """Return bounded same-page listing URLs, never individual bids or logins.

    The label must indicate pagination, the query must contain a numeric page
    cursor, and the URL must remain on the same HTTPS host and path. This is
    only discovery of public listings, not evidence of an open solicitation.
    """
    base = urlparse(listing_url)
    # The current page's non-cursor query is part of its listing identity.
    # A pager labelled "Next" must not silently switch open to closed bids,
    # drop an agency/category filter, or introduce a login parameter. Keep
    # duplicate filters: a dict would hide conflicting publisher values.
    base_filters = sorted((key, value) for key, value in
                          parse_qsl(base.query, keep_blank_values=True)
                          if key.lower() not in PAGE_KEYS)
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
            # Compare non-cursor filters to the page that supplied the link,
            # not merely to the URL returned after fetching it. The latter
            # check cannot prevent a wrong-filter request from being sent.
            candidate_filters = sorted((key, value) for key, value in
                                       parse_qsl(parsed.query, keep_blank_values=True)
                                       if key.lower() not in PAGE_KEYS)
            if candidate_filters != base_filters:
                continue
            cursors = [value for key, value in params if key in PAGE_KEYS]
            # Publishers legitimately use page+offset or repeat the same
            # numeric page key. Reject conflicting values for one key, which
            # different servers can resolve to different pages.
            if not cursors or not all(value.isascii() and value.isdigit()
                                      for value in cursors):
                continue
            if any(len({value for key, value in params if key == name}) > 1
                   for name, _ in params if name in PAGE_KEYS):
                continue
            # Fragments never change the listing page; avoid duplicate fetches.
            url = parsed._replace(fragment="").geturl()
            if url not in seen and url not in found:
                found.append(url)
        except ValueError:
            continue
    return found
