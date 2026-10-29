"""Diagnostic-only parser for City of Binghamton's official Granicus bid table.

This module discovers candidate *links* for staged-source diagnostics. It does
not fetch notices, activate a source, or publish opportunities. Listing 'Open'
badges are not proof that the closing time has not already passed.
"""
import datetime as dt
import re
from urllib.parse import urljoin, urlsplit

import civicplus_bids

_DATE = re.compile(r"\b(?P<date>\d{1,2}/\d{1,2}/\d{4})(?:\s+(?P<time>\d{1,2}:\d{2}\s*[AP]M))?\b", re.I)
_PATH = re.compile(r"^/Home/Components/RFP/RFP/\d+/\d+/?$", re.I)
_STATUS = re.compile(r"\b(Open|Closed|Awarded|Cancelled|Canceled)\s*$", re.I)


def individual_url(href, origin):
    """Accept only official same-host HTTPS individual Granicus RFP URLs."""
    if not isinstance(href, str) or not href or any(
            ord(char) < 33 or ord(char) == 127 or char == "\\" for char in href):
        return ""
    if re.search(r"%(?:0[0-9a-f]|1[0-9a-f]|7f)", href, re.I):
        return ""
    try:
        url = urljoin(origin, href)
        base, parsed = urlsplit(origin), urlsplit(url)
        if (base.scheme != "https" or parsed.scheme != "https"
                or not base.hostname or parsed.hostname != base.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.port not in (None, 443)
                or not _PATH.fullmatch(parsed.path)):
            return ""
        return url.split("#", 1)[0]
    except ValueError:
        return ""


def listing_records(page, origin, now=None):
    """Extract distinct row-scoped links, never a standalone solicitation."""
    now = now or dt.datetime.now(dt.timezone.utc)
    records = []
    seen = set()
    for label, href, _ in page.links:
        url = individual_url(href, origin)
        if not url or url in seen:
            continue
        row = page.link_rows.get(href, "")
        if not row:
            # A link outside an isolated table row cannot establish a deadline.
            continue
        seen.add(url)
        dates = list(_DATE.finditer(row))
        # Granicus displays Starting and Closing in separate columns. If
        # another date appears, ambiguity is safer than choosing the wrong one.
        due, due_time = "", ""
        if len(dates) == 2:
            try:
                due = dt.datetime.strptime(dates[1].group("date"), "%m/%d/%Y").date().isoformat()
                due_time = " ".join((dates[1].group("time") or "").upper().split())
            except ValueError:
                pass
        status_match = _STATUS.search(row)
        status = status_match.group(1).lower() if status_match else "unknown"
        records.append({
            "title": label.strip(), "url": url, "publisher_status": status,
            "deadline": due, "deadline_time": due_time,
            "deadline_passed": civicplus_bids.closing_passed(due, due_time, now),
        })
    return records
