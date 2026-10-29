"""Conservative extraction of *submission* dates from public bid text.

Questions, addenda, walkthroughs and pre-bid meeting dates are not submission
deadlines. This parser never establishes a notice's open status or time zone.
"""
import datetime as dt
import re

_DATE = (r"(?P<date>(?:\d{4}-\d{1,2}-\d{1,2})|"
         r"(?:\d{1,2}/\d{1,2}/\d{2,4})|"
         r"(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|"
         r"May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|"
         r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4}))")
_LABEL = (
    r"(?P<label>\b(?:due(?:\s+date)?|closing(?:\s+date(?:/time)?)?|"
    r"(?:sealed\s+)?bids?\s+(?:due|received|submitted|"
    r"(?:must|will|shall)\s+be\s+(?:received|submitted))|"
    r"(?:sealed\s+)?proposals?\s+(?:due|received|submitted|"
    r"(?:must|will|shall)\s+be\s+(?:received|submitted))|"
    r"(?:quotes?|responses?)\s+(?:due|received|submitted|"
    r"(?:must|will|shall)\s+be\s+(?:received|submitted))|"
    r"(?:bid|proposal|quote|response)\s+(?:submission\s+)?deadline|"
    r"submission\s+deadline|submit(?:ted)?\s+(?:by|until)|deadline))"
)
_CANDIDATE = re.compile(_LABEL + r"(?P<between>[^.;\n]{0,65}?)" + _DATE, re.I)
_OTHER_MILESTONE = re.compile(
    r"(?:questions?|q\s*&\s*a|inquir(?:y|ies)|clarifications?|"
    r"requests?\s+for\s+(?:information|clarification)|rfis?|answers?|"
    r"addenda|addendums?|pre[- ]?bid\s+(?:meetings?|conferences?)|"
    r"site\s+visits?|walk[- ]?throughs?|mandatory\s+meetings?)",
    re.I,
)
_OTHER_MILESTONE_END = re.compile(
    r"(?:questions?|q\s*&\s*a|inquir(?:y|ies)|clarifications?|"
    r"rfis?|answers?|addenda|addendums?|meetings?|conferences?|"
    r"site\s+visits?|walk[- ]?throughs?)(?:\s+(?:about|regarding|concerning)"
    r"(?:\s+(?:bids?|proposals?|quotes?|responses?))?)?\s*$",
    re.I,
)


def _date(value):
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%B %d %Y", "%b %d %Y"):
        try:
            cleaned = re.sub(r"(?<=\d)(?:st|nd|rd|th)(?=,?\s*\d{4}$)", "", value, flags=re.I)
            cleaned = re.sub(r",\s*(?=\d{4}$)", " ", cleaned)
            return dt.datetime.strptime(cleaned.replace(",", ""), fmt).date()
        except ValueError:
            continue
    return None


def submission_deadline(text):
    """Return ISO date only from an explicit bid-submission date label.

    When multiple actual bid submission dates appear (for example, an
    amendment), the latest is retained; this is still unverified evidence.
    """
    if not isinstance(text, str):
        return ""
    dates = []
    for match in _CANDIDATE.finditer(text):
        # Restrict prefix to the current sentence/field, so an earlier
        # unrelated "questions" label cannot poison the next bid deadline.
        prefix = re.split(r"[.;\n]", text[max(0, match.start()-80):match.start()])[-1]
        between = match.group("between")
        if _OTHER_MILESTONE_END.search(prefix) or _OTHER_MILESTONE.search(between):
            continue
        parsed = _date(match.group("date"))
        if parsed:
            dates.append(parsed)
    dates.extend(date for date, _ in _receipt_before_date_matches(text))
    return max(dates).isoformat() if dates else ""


# A submission *date* alone cannot establish that a same-day bid has closed.
# Extract a clock time only when adjacent to the same validated submission label.
_CLOCK = r"(?:0?[1-9]|1[0-2])(?::[0-5]\d)?\s*[AP]\.?M\.?"
_AFTER_DATE = re.compile(r"^\s*(?:,\s*|at\s+)?(?P<clock>" + _CLOCK + r")\b", re.I)
_BEFORE_DATE = re.compile(r"(?P<clock>" + _CLOCK + r")\s*(?:on\s+)?$", re.I)

# Some official notices place the clock before the date and include a mailing
# address: "Sealed bids will be received in ... until 1:45 P.M. on Oct 23,2025".
# Require the receipt verb, "until", clock and date together; a bid-opening
# time or a question deadline must never substitute for the submission cutoff.
_RECEIPT_BEFORE_DATE = re.compile(
    r"\b(?:sealed\s+)?(?:bids?|proposals?|quotes?|responses?)\s+"
    r"(?:(?:will|shall|must)\s+be\s+)?received\b"
    r"[^\n]{0,260}?\buntil\s+(?P<clock>" + _CLOCK + r")\s+"
    r"(?:local\s+time\s+)?on\s+"
    r"(?:(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+)?"
    + _DATE, re.I,
)


def _receipt_before_date_matches(text):
    for match in _RECEIPT_BEFORE_DATE.finditer(text):
        prefix = re.split(r"[.;\n]", text[max(0, match.start()-80):match.start()])[-1]
        if _OTHER_MILESTONE_END.search(prefix):
            continue
        date = _date(match.group("date"))
        if date is None:
            continue
        clock = re.sub(r"\.", "", match.group("clock").upper())
        clock = re.sub(r"\s+", " ", clock).strip()
        if ":" not in clock:
            clock = re.sub(r"^(\d{1,2})", r"\1:00", clock)
        try:
            clock = dt.datetime.strptime(clock, "%I:%M %p").strftime("%I:%M %p").lstrip("0")
        except ValueError:
            continue
        yield date, clock



def submission_deadline_details(text):
    """Return (ISO submission date, explicit 12-hour clock) or empty values.

    A question, walkthrough, or pre-bid date cannot supply the closing time.
    For revised deadlines, the latest submission date wins; on a tied date,
    the last explicit time is used. No time is inferred from a date alone.
    """
    if not isinstance(text, str):
        return "", ""
    matches = []
    for match in _CANDIDATE.finditer(text):
        prefix = re.split(r"[.;\n]", text[max(0, match.start()-80):match.start()])[-1]
        between = match.group("between")
        if _OTHER_MILESTONE_END.search(prefix) or _OTHER_MILESTONE.search(between):
            continue
        date = _date(match.group("date"))
        if date is None:
            continue
        after = _AFTER_DATE.match(text[match.end():match.end()+30])
        before = _BEFORE_DATE.search(between)
        raw = (after or before)
        clock = ""
        if raw:
            value = re.sub(r"\s+", " ", raw.group("clock").upper()).strip()
            if ":" not in value:
                value = re.sub(r"^(\d{1,2})", r"\1:00", value)
            try:
                clock = dt.datetime.strptime(value, "%I:%M %p").strftime("%I:%M %p").lstrip("0")
            except ValueError:
                pass
        matches.append((date, clock))
    matches.extend(_receipt_before_date_matches(text))
    if not matches:
        return "", ""
    latest = max(date for date, _ in matches)
    times = [clock for date, clock in matches if date == latest and clock]
    return latest.isoformat(), (times[-1] if times else "")


def explicit_closing_passed(text, now):
    """Check explicit submission time against NY/PA agency-local Eastern time.

    Only call this for NY/PA issuing authorities; the text itself may omit a
    timezone. Missing or malformed times are never guessed.
    """
    from zoneinfo import ZoneInfo
    date, clock = submission_deadline_details(text)
    if not date or not clock:
        return False
    local = now.astimezone(ZoneInfo("America/New_York"))
    due = dt.date.fromisoformat(date)
    if due != local.date():
        return due < local.date()
    closing = dt.datetime.strptime(clock, "%I:%M %p").time()
    return local.time().replace(tzinfo=None) >= closing
