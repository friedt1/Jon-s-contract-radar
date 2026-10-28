"""Individual CivicPlus/CivicEngage county bid listings, without logins or search APIs.

This adapter reads publicly advertised Bids.aspx HTML and follows only same-host
individual bidID links. Each bid is parsed independently; a closed neighboring
bid cannot suppress an open one. All results remain unverified until worksite,
deadline, bid documents and travel time have been independently checked.
"""
import datetime as dt
import re
from urllib.parse import parse_qs, urljoin, urlparse

SOURCES = frozenset({"Chemung County bids", "Steuben County bids"})
MAX_DETAILS = 36
DATE = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{4})(?:\s+(\d{1,2}:\d{2}\s*[AP]M))?\b", re.I)
STATUS = re.compile(r"\bStatus\s*:\s*(?:Closes\s*:\s*)?(Open|Closed|Awarded|Cancelled|Canceled)\b", re.I)
CLOSED = frozenset({"closed", "awarded", "cancelled", "canceled"})


def individual_url(href, origin):
    url = urljoin(origin, href)
    base, parsed = urlparse(origin), urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != base.hostname:
        return ""
    query = parse_qs(parsed.query)
    if not any(k.lower() == "bidid" and values and values[0].isdigit()
               for k, values in query.items()):
        return ""
    if not parsed.path.lower().endswith("/bids.aspx"):
        return ""
    return url.split("#", 1)[0]


def status_of(text):
    match = STATUS.search(text)
    return match.group(1).lower() if match else "unknown"


def closing_of(text):
    """A listing deadline must be adjacent to its 'Closes' field, not a posted date."""
    match = re.search(r"\bCloses\s*:\s*(?:Open|Closed|Awarded|Cancelled|Canceled)?\s*"
                      + DATE.pattern, text, re.I)
    if not match:
        match = re.search(r"\bStatus\s*:\s*(?:Closes\s*:\s*)?"
                          r"(?:Open|Closed|Awarded|Cancelled|Canceled)\s+"
                          + DATE.pattern, text, re.I)
    if not match:
        return "", ""
    try:
        date = dt.datetime.strptime(match.group(1), "%m/%d/%Y").date().isoformat()
    except ValueError:
        return "", ""
    return date, (match.group(2) or "").strip()



def detail_closing_of(text):
    """Read the individual notice's closing field, never its publication date.

    CivicPlus detail pages use 'Closing Date/Time' rather than the listing's
    'Closes' label. The returned date is authoritative when present.
    """
    match = re.search(r"\bClosing\s+Date(?:/Time|\s+and\s+Time)?\s*:\s*" + DATE.pattern, text, re.I)
    if not match:
        return "", ""
    try:
        due = dt.datetime.strptime(match.group(1), "%m/%d/%Y").date().isoformat()
    except ValueError:
        return "", ""
    return due, (match.group(2) or "").strip()


def detail_description(text):
    """Extract actual notice scope without treating unrelated page chrome as scope."""
    match = re.search(
        r"\bDescription\s*:\s*(.+?)(?=\b(?:Related Documents|Contact Us|"
        r"Return To Main Bid Postings Page|Publication Date/Time|Closing Date/Time|Project Location|Work Location|Worksite|Site Location)\s*:|$)",
        text, re.I | re.S,
    )
    return " ".join(match.group(1).split())[:1200] if match else ""


def detail_worksite(text):
    """Only explicit worksite labels count; a purchasing office is not a job site."""
    match = re.search(
        r"\b(?:Project Location|Work Location|Worksite|Site Location)\s*:\s*"
        r"(.{1,180}?)(?=\b(?:Description|Status|Closing Date/Time|Related Documents)\s*:|$)",
        text, re.I | re.S,
    )
    return " ".join(match.group(1).split())[:180] if match else ""

def listing_records(page, origin):
    """Use link positions to isolate each individual bid from adjacent bid cards.

    Repeated 'Read on' links for the same bid are merged. The page's general
    'Show Closed...' control is outside the first record and cannot contaminate it.
    """
    links = []
    for label, href, position in page.links:
        url = individual_url(href, origin)
        if url:
            links.append((position, label, url))
    links.sort()
    first = {}
    for position, label, url in links:
        if url not in first:
            first[url] = (position, label)
    unique = sorted(((position, label, url) for url, (position, label) in first.items()))
    records = []
    for i, (start, title, url) in enumerate(unique):
        stop = unique[i + 1][0] if i + 1 < len(unique) else len(page.parts)
        # Bound each record even if the site adds a long unrelated footer.
        text = " ".join(page.parts[start:min(stop, start + 180)])
        status = status_of(text)
        due, due_time = closing_of(text)
        number = re.search(r"\bBid\s+No\.?\s*:?\s*([A-Za-z0-9-]+)", text, re.I)
        records.append({
            "title": title.strip(), "url": url, "description": text[:1400],
            "bid_number": number.group(1) if number else "",
            "open_status": status, "deadline": due, "deadline_time": due_time,
        })
    return records
