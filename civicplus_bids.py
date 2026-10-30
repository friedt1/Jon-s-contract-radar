"""Individual CivicPlus/CivicEngage county bid listings, without logins or search APIs.

This adapter reads publicly advertised Bids.aspx HTML and follows only same-host
individual bidID links. Each bid is parsed independently; a closed neighboring
bid cannot suppress an open one. All results remain unverified until worksite,
deadline, bid documents and travel time have been independently checked.
"""
import datetime as dt
import re
from urllib.parse import parse_qs, urljoin, urlparse
from zoneinfo import ZoneInfo

import public_bid_pagination as public_pages

SOURCES = frozenset({"Chemung County bids", "Steuben County bids",
                     "Town of Horseheads", "City of Ithaca",
                     "Cortland County", "Yates County", "Seneca County",
                     "Bradford County PA", "Livingston County", "Wyoming County",
                     "Village of Horseheads", "City of Cortland",
                     "City of Geneva"})
MAX_DETAILS = 36
_DATE_TEXT = (
    r"(?:\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2}|"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|"
    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4})"
)
# These are closing-field dates only; publication and meeting dates are not
# submission cutoffs. Keep the clock attached to the same field.
DATE = re.compile(
    r"\b(" + _DATE_TEXT + r")(?:\s*(?:,\s*)?(?:at\s+)?(\d{1,2}:\d{2}\s*[AP]M))?\b",
    re.I,
)


def _closing_date(value):
    cleaned = " ".join(value.replace(",", " ").split())
    for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%B %d %Y", "%b %d %Y"):
        try:
            return dt.datetime.strptime(cleaned, fmt).date().isoformat()
        except ValueError:
            continue
    return ""
STATUS = re.compile(r"\bStatus\s*:\s*(?:Closes\s*:\s*)?(Open|Closed|Awarded|Cancelled|Canceled|Withdrawn|Expired|Reopened)\b", re.I)
CLOSED = frozenset({"closed", "awarded", "cancelled", "canceled", "withdrawn", "expired"})
# A closed question period does not close submission of bids.
QUESTION_ONLY = re.compile(
    r"[\s:;,()\-–—/]+(?:(?:for|to)\s+)?"
    r"(?:questions?|q\s*&\s*a|inquir(?:y|ies)|clarifications?|rfis?|addenda)\b",
    re.I,
)


def individual_url(href, origin):
    """Only well-formed same-host HTTPS CivicPlus bid notices are fetchable."""
    if not isinstance(href, str) or not href or any(
        ord(c) < 33 or ord(c) == 127 or c == "\\" for c in href
    ) or re.search(r"%(?:0[0-9a-f]|1[0-9a-f]|7f)", href, re.I):
        return ""
    try:
        url = urljoin(origin, href)
        base, parsed = urlparse(origin), urlparse(url)
        if (parsed.scheme != "https" or not parsed.hostname
                or parsed.hostname != base.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443)):
            return ""
        query = parse_qs(parsed.query)
        if not any(k.lower() == "bidid" and values and values[0].isdigit()
                   for k, values in query.items()):
            return ""
        if not parsed.path.lower().endswith("/bids.aspx"):
            return ""
        return url.split("#", 1)[0]
    except ValueError:
        return ""


def status_of(text):
    match = STATUS.search(text)
    if not match:
        return "unknown"
    status = match.group(1).lower()
    if status == "closed" and QUESTION_ONLY.match(text[match.end():]):
        return "unknown"
    return status


def closing_of(text):
    """A listing deadline must be adjacent to its 'Closes' field, not a posted date."""
    match = re.search(r"\bCloses\s*:\s*(?:Open|Closed|Awarded|Cancelled|Canceled|Withdrawn|Expired|Reopened)?\s*"
                      + DATE.pattern, text, re.I)
    if not match:
        match = re.search(r"\bStatus\s*:\s*(?:Closes\s*:\s*)?"
                          r"(?:Open|Closed|Awarded|Cancelled|Canceled|Withdrawn|Expired|Reopened)\s+"
                          + DATE.pattern, text, re.I)
    if not match:
        return "", ""
    date = _closing_date(match.group(1))
    return date, (match.group(2) or "").strip() if date else ""



def detail_closing_of(text):
    """Read the individual notice's closing field, never its publication date.

    CivicPlus detail pages use 'Closing Date/Time' rather than the listing's
    'Closes' label. The returned date is authoritative when present.
    """
    match = re.search(r"\bClosing\s+Date(?:/Time|\s+and\s+Time)?\s*:\s*" + DATE.pattern, text, re.I)
    if not match:
        return "", ""
    due = _closing_date(match.group(1))
    return due, (match.group(2) or "").strip() if due else ""



def closing_passed(date, time, now):
    """Conservatively reject a known NY CivicPlus deadline after local closing time.

    The configured CivicPlus targets are NY/PA agencies; use Eastern local
    time including daylight saving. If a closing time is missing or malformed,
    do not invent one: the same-day notice remains unverified.
    """
    if not date:
        return False
    local = now.astimezone(ZoneInfo("America/New_York"))
    today = local.date().isoformat()
    if date < today:
        return True
    if date > today or not time:
        return False
    try:
        closing = dt.datetime.strptime(" ".join(time.upper().split()), "%I:%M %p").time()
    except ValueError:
        return False
    return local.time().replace(tzinfo=None) >= closing


def detail_description(text):
    """Extract actual notice scope without treating unrelated page chrome as scope."""
    match = re.search(
        r"\bDescription\s*:\s*(.+?)(?=\b(?:Related Documents|Contact Us|"
        r"Return To Main Bid Postings Page|Publication Date/Time|Closing Date/Time|"
        r"Status|Bid\s+(?:Number|Title)|Project Location|Work Location|Worksite|Site Location)\s*:|$)",
        text, re.I | re.S,
    )
    return " ".join(match.group(1).split())[:1200] if match else ""


def detail_worksite(text):
    """Only explicit worksite labels count; a purchasing office is not a job site."""
    match = re.search(
        r"\b(?:Project Location|Work Location|Worksite|Site Location)\s*:\s*"
        r"(.{1,180}?)(?=\b(?:Description|Status|Closing Date/Time|"
        r"Bid\s+(?:Number|Title)|Publication Date/Time|Related Documents)\s*:|$)",
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
        # A misleading bidID on a pager control is not a solicitation card.
        if url and not public_pages.pagination_label(label):
            links.append((position, label, url))
    links.sort()
    first = {}
    for position, label, url in links:
        if url not in first:
            first[url] = (position, label)
    unique = sorted(((position, label, url) for url, (position, label) in first.items()))
    records = []
    generic_labels = {"read on", "read more", "details", "view details",
                      "view bid", "view", "more info", "learn more", "click here"}
    for i, (start, title, url) in enumerate(unique):
        stop = unique[i + 1][0] if i + 1 < len(unique) else len(page.parts)
        # A public bid card often puts the title BEFORE its generic "Read on"
        # link. Use the isolated article/list/table row, never the prior card.
        href = next((href for label, href, pos in page.links
                     if pos == start and individual_url(href, origin) == url), "")
        card_text = page.link_rows.get(href, "") if href else ""
        if card_text and title.strip().lower() in generic_labels:
            prefix = re.split(
                r"\b(?:Bid\s+No\.?|Status|Closes|Publication Date/Time|"
                r"Closing Date/Time|Read on|Read more|View details)\b",
                card_text, maxsplit=1, flags=re.I,
            )[0].strip(" :-")
            if prefix and prefix.lower() not in generic_labels:
                title = prefix[:220]
        # Bound each record even if the site adds a long unrelated footer.
        text = card_text[:1600] if card_text else " ".join(page.parts[start:min(stop, start + 180)])
        status = status_of(text)
        due, due_time = closing_of(text)
        number = re.search(r"\bBid\s+No\.?\s*:?\s*([A-Za-z0-9-]+)", text, re.I)
        records.append({
            "title": title.strip(), "url": url, "description": text[:1400],
            "bid_number": number.group(1) if number else "",
            "open_status": status, "deadline": due, "deadline_time": due_time,
        })
    return records
