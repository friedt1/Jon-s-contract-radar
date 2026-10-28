"""Bounded navigation of explicitly public county bid listing pages.

Never used on NYSCR, BidNet or PennBid; those require a permitted
listing/export interface. Do not follow off-host or unrelated links.
"""
from urllib.parse import urljoin, urlparse, parse_qs

PUBLIC_LISTINGS = frozenset({
    "Chemung County bids", "Steuben County bids",
    "Schuyler County purchasing", "Tompkins County purchasing",
    "Elmira City bids",
})
PAGE_KEYS = frozenset({"page", "pagenumber", "pageno", "skip", "offset", "start"})
MAX_PAGES = 3
MAX_PUBLIC_DETAILS = 36


def next_pages(links, listing_url, seen):
    """Return candidate listing pagination URLs, never generic detail links."""
    base = urlparse(listing_url)
    found = []
    for label, href, _ in links:
        label = label.strip().lower()
        if not (label in {"next", "next page", "›", "»"} or label.isdigit()):
            continue
        url = urljoin(listing_url, href)
        parsed = urlparse(url)
        if (parsed.scheme != "https" or parsed.hostname != base.hostname
                or parsed.path.lower().rstrip("/") != base.path.lower().rstrip("/")
                or url in seen):
            continue
        params = {k.lower() for k in parse_qs(parsed.query)}
        if not params.intersection(PAGE_KEYS):
            continue
        found.append(url)
    return found
