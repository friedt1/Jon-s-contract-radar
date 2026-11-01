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
    ) or re.search(r"%(?:0[0-9a-f]|1[0-9a-f]|7f|5c)", href, re.I):
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


def listing_closing_of(row):
    """Require a closing-field label when a row has extra date evidence.

    A two-date Granicus table row ordinarily shows start then close. If a
    question deadline, pre-bid meeting, or third date appears, position alone
    cannot identify the submission cutoff. An explicit Close Date/Closes
    field takes precedence; ambiguous rows remain unknown and unverified.
    """
    close_label = (
        r"\b(?:Close(?:ing)?\s+Date(?:/Time)?|Closes|"
        r"Bid(?:ding)?\s+(?:Due|Deadline)|Submission\s+Deadline|"
        r"Proposals?\s+Due)\s*:"
    )
    labelled = re.search(close_label + r"\s*" + DATE.pattern, row, re.I)
    if labelled:
        return _date(labelled)
    if re.search(close_label, row, re.I):
        return "", ""  # Malformed closing field must not borrow another date.
    dates = list(DATE.finditer(row))
    if len(dates) != 2 or re.search(
        r"\b(?:questions?|q\s*&\s*a|inquir(?:y|ies)|pre[- ]?bid|"
        r"site\s+visit|clarifications?|addenda)\b", row, re.I
    ):
        return "", ""
    return _date(dates[1])


def listing_records(page, origin):
    """Read individual Granicus RFP rows; never infer deadline from start date."""
    # One Granicus notice can appear in multiple listing rows (for example,
    # a featured row and a department row). An href-keyed row map keeps only
    # the last row and can erase contradictory closing evidence. Use the
    # original enclosing row for EACH link, then reconcile by notice ID.
    grouped = {}
    for index, (title, href, _) in enumerate(page.links):
        url = individual_url(href, origin)
        if not url:
            continue
        row = page.link_contexts.get(index, page.link_rows.get(href, ""))
        due, clock = listing_closing_of(row)
        status_match = re.search(r"\b(Open|Closed|Awarded|Cancelled|Canceled)\s*$", row, re.I)
        grouped.setdefault(url, []).append((
            title.strip()[:220],
            status_match.group(1).lower() if status_match else "unknown",
            due, clock,
        ))

    records = []
    for url, observations in grouped.items():
        statuses = {status for _, status, _, _ in observations if status != "unknown"}
        closed = bool(statuses & CLOSED)
        open_seen = "open" in statuses
        status_conflict = closed and open_seen
        # Closed and Awarded are both closed states, not a false conflict.
        status = ("unknown" if status_conflict else
                  "closed" if closed else "open" if open_seen else "unknown")
        dates = {due for _, _, due, _ in observations if due}
        clocks = {clock.upper().replace(" ", "")
                  for _, _, due, clock in observations if due and clock}
        deadline_conflict = len(dates) > 1 or len(clocks) > 1
        due = next(iter(dates)) if len(dates) == 1 and not deadline_conflict else ""
        clock = next((clock for _, _, date, clock in observations
                      if date == due and clock), "") if due else ""
        title = next((title for title, _, _, _ in observations
                      if title and title.lower() not in {
                          "view", "view details", "details", "read more"
                      }), observations[0][0])
        records.append({
            "title": title, "url": url,
            "open_status": status, "deadline": due, "deadline_time": clock,
            "listing_status_conflict": status_conflict,
            "listing_deadline_conflict": deadline_conflict,
            "listing_status_evidence": sorted(statuses),
            "listing_deadline_evidence": sorted(
                {(" ".join((date, time))).strip()
                 for _, _, date, time in observations if date}),
        })
    return records


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
