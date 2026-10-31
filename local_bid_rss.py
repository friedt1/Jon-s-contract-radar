"""Read the explicitly advertised Elmira Next local-bid RSS feed.

The feed is a discovery channel, never proof a bid is still open. Keep
candidates unverified until the issuing agency's original notice is checked.
"""
import datetime as dt
import email.utils
import xml.etree.ElementTree as ET
from html import unescape
from notice_identity import canonical_url
from source_config import valid_public_https_url

FEED_URL = "https://elmiranext.com/bids/feed.xml"


def _text(node, key):
    return (node.findtext(key) or "").strip()


def parse(xml_text, *, now=None):
    """Return individual RSS bids, preferring the latest dated copy of each URL."""
    now = now or dt.datetime.now(dt.timezone.utc)
    root = ET.fromstring(xml_text)
    if root.tag != "rss":
        raise ValueError("not an RSS feed")
    result, seen = [], {}
    for item in root.findall("./channel/item"):
        title = unescape(_text(item, "title"))
        description = unescape(_text(item, "description"))
        link = _text(item, "link")
        # Normalize tracking variants, but preserve solicitation identifiers,
        # signed query strings, and unknown parameters. Reject unsafe/private,
        # credentialed or malformed links without discarding the whole feed.
        canonical = canonical_url(link)
        if not canonical or not valid_public_https_url(canonical):
            continue
        pub = _text(item, "pubDate")
        try:
            published = email.utils.parsedate_to_datetime(pub)
            if published.tzinfo is None:
                published = published.replace(tzinfo=dt.timezone.utc)
            published_utc = published.astimezone(dt.timezone.utc)
            age = (now - published_utc).total_seconds()
        except (ValueError, TypeError, OverflowError):
            age = None
        if age is None or age < 0 or age > 90 * 86400:
            continue
        # Feed order is not guaranteed. An older, still-recent posting may
        # contain an expired cutoff while a later amendment extends it.
        # Prefer the newest publication for the same notice identity, without
        # combining stale deadline text or asserting that the bid is open.
        previous = seen.get(canonical)
        if previous is not None and published_utc <= previous[1]:
            continue
        row = {
            "title": title,
            "description": description,
            "url": canonical,
            "published": published.date().isoformat(),
            "source": "Elmira Next bid RSS",
            "status": "unverified",
            "original_notice_confirmed": False,
        }
        if previous is None:
            seen[canonical] = (len(result), published_utc)
            result.append(row)
        else:
            index, _ = previous
            seen[canonical] = (index, published_utc)
            result[index] = row
    return result
