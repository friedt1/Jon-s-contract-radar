"""Read the explicitly advertised Elmira Next local-bid RSS feed.

The feed is a discovery channel, never proof a bid is still open. Keep
candidates unverified until the issuing agency's original notice is checked.
"""
import datetime as dt
import email.utils
import xml.etree.ElementTree as ET
from html import unescape
from urllib.parse import urlparse

FEED_URL = "https://elmiranext.com/bids/feed.xml"
ALLOWED_SCHEMES = ("https",)


def _text(node, key):
    return (node.findtext(key) or "").strip()


def parse(xml_text, *, now=None):
    """Return individual RSS bids with original URL, deduplicated by link."""
    now = now or dt.datetime.now(dt.timezone.utc)
    root = ET.fromstring(xml_text)
    if root.tag != "rss":
        raise ValueError("not an RSS feed")
    result, seen = [], set()
    for item in root.findall("./channel/item"):
        title = unescape(_text(item, "title"))
        description = unescape(_text(item, "description"))
        link = _text(item, "link")
        parsed = urlparse(link)
        if parsed.scheme not in ALLOWED_SCHEMES or not parsed.hostname:
            continue
        if link in seen:
            continue
        seen.add(link)
        pub = _text(item, "pubDate")
        try:
            published = email.utils.parsedate_to_datetime(pub)
            if published.tzinfo is None:
                published = published.replace(tzinfo=dt.timezone.utc)
            age = (now - published.astimezone(dt.timezone.utc)).total_seconds()
        except (ValueError, TypeError, OverflowError):
            age = None
        if age is None or age < 0 or age > 90 * 86400:
            continue
        result.append({
            "title": title,
            "description": description,
            "url": link,
            "published": published.date().isoformat(),
            "source": "Elmira Next bid RSS",
            "status": "unverified",
            "original_notice_confirmed": False,
        })
    return result
