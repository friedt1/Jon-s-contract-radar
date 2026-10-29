"""Conservative Granicus/PrimeGov RFP notice diagnostics.

Only same-host HTTPS /Home/Components/RFP/RFP/{id}/{module} pages are
recognized. This parser supplies staging evidence, NOT a live bid feed.
"""
import datetime as dt
import re
from urllib.parse import urljoin, urlsplit

SOURCES = frozenset({"City of Binghamton"})
PATH = re.compile(r"^/Home/Components/RFP/RFP/([1-9][0-9]*)(?:/([0-9]+))?/?$", re.I)
DATE = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{4})(?:\s+(\d{1,2}:\d{2}\s*[AP]M))?\b", re.I)
CLOSED = frozenset({"closed", "awarded", "cancelled", "canceled"})


def individual_url(href, origin):
    """Require a same-host, stable individual RFP ID; reject external links."""
    if not isinstance(href, str) or not href or any(
        ord(ch) < 33 or ord(ch) == 127 or ch == "\\" for ch in href
    ) or re.search(r"%(?:0[0-9a-f]|1[0-9a-f]|7f)", href, re.I):
        return ""
    try:
        url = urljoin(origin, href)
        target, base = urlsplit(url), urlsplit(origin)
        if (target.scheme != "https" or target.hostname != base.hostname
                or target.username is not None or target.password is not None
                or target.port not in (None, 443) or target.query
                or not PATH.fullmatch(target.path)):
            return ""
        return url.split("#", 1)[0]
    except ValueError:
        return ""


def _date(match):
    if not match:
        return "", ""
    try:
        date = dt.datetime.strptime(match.group(1), "%m/%d/%Y").date().isoformat()
    except ValueError:
        return "", ""
    return date, (match.group(2) or "").strip()


def listing_records(page, origin):
    """Read individual Granicus RFP rows; never infer deadline from start date."""
    found = {}
    for title, href, _ in page.links:
        url = individual_url(href, origin)
        if not url or url in found:
            continue
        row = page.link_rows.get(href, "")
        dates = list(DATE.finditer(row))
        # Granicus rows contain Start Date then Close Date. One date alone
        # cannot safely be interpreted as a submission deadline.
        due, clock = _date(dates[1]) if len(dates) > 1 else ("", "")
        status_match = re.search(r"\b(Open|Closed|Awarded|Cancelled|Canceled)\s*$", row, re.I)
        found[url] = {
            "title": title.strip()[:220], "url": url,
            "open_status": status_match.group(1).lower() if status_match else "unknown",
            "deadline": due, "deadline_time": clock,
        }
    return list(found.values())


def detail_closing_of(text):
    """Only an individual Close Date field, never its Start Date or Q&A date."""
    match = re.search(r"\bClose\s+Date\s*:\s*" + DATE.pattern, text, re.I)
    return _date(match)


def detail_shape(text):
    """A listing or generic homepage must not count as an individual notice."""
    return bool(re.search(r"\bStart\s+Date\s*:\s*" + DATE.pattern, text, re.I)
                and re.search(r"\bClose\s+Date\s*:\s*" + DATE.pattern, text, re.I))


def status_of(text):
    match = re.search(r"\bStatus\s*:\s*(Open|Closed|Awarded|Cancelled|Canceled)\b", text, re.I)
    return match.group(1).lower() if match else "unknown"
