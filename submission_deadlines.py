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
    """Return the submission date, respecting explicit deadline revisions.

    Share the same evidence selection as submission_deadline_details so the
    date-only and date/time scanner paths cannot disagree on an amendment.
    """
    return submission_deadline_details(text)[0]


# A submission *date* alone cannot establish that a same-day bid has closed.
# Extract a clock time only when adjacent to the same validated submission label.
_CLOCK = r"(?:0?[1-9]|1[0-2])(?::[0-5]\d)?[ \t]*[AP]\.?[ \t]*M\.?"
# Accept "due DATE at 1:30 P.M." and "due DATE, at 1:30 P.M.".
# A word boundary after the final dot in P.M. would reject the clock.
_AFTER_DATE = re.compile(r"^[ \t]*(?:,[ \t]*)?(?:at[ \t]+)?(?P<clock>" + _CLOCK + r")(?=$|[ \t,;.)])", re.I)
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



# The ordinary label/date parser deliberately does not cross sentence dots.
# Match a clock BEFORE the date separately, including dotted "P.M.".
_DUE_BEFORE_DATE = re.compile(
    r"\b(?:sealed\s+)?(?:bids?|proposals?|quotes?|responses?)\s+"
    r"(?:due|must\s+be\s+submitted\s+by)\s+(?:at\s+)?"
    r"(?P<clock>" + _CLOCK + r")\s+(?:on\s+)?" + _DATE, re.I,
)

def _receipt_before_date_matches(text, with_position=False):
    for match in (m for pattern in (_RECEIPT_BEFORE_DATE, _DUE_BEFORE_DATE)
                  for m in pattern.finditer(text)):
        prefix = re.split(r"[.;\n]", text[max(0, match.start()-80):match.start()])[-1]
        if _OTHER_MILESTONE_END.search(prefix):
            continue
        date = _date(match.group("date"))
        if date is None:
            continue
        clock = re.sub(r"\.", "", match.group("clock").upper())
        clock = re.sub(r"\s+", " ", clock).strip()
        clock = re.sub(r"([AP])\s+(?=M\b)", r"\1", clock)
        if ":" not in clock:
            clock = re.sub(r"^(\d{1,2})", r"\1:00", clock)
        try:
            clock = dt.datetime.strptime(clock, "%I:%M %p").strftime("%I:%M %p").lstrip("0")
        except ValueError:
            continue
        yield (date, clock, match.start()) if with_position else (date, clock)



_REVISION_PREFIX = re.compile(
    r"\\b(?:amend(?:ed|ment)?|revis(?:ed|ion)?|updated|corrected|"
    r"rescheduled|addendum)(?:\\s*(?:#|no\\.?)?\\s*\\d+)?\\s*[:\\-]?\\s*$",
    re.I,
)


def _is_revised_submission(text, start):
    """Require an explicit amendment immediately before this submission label.

    A distant addendum or an amended *question* deadline must not rewrite the
    bid submission cutoff. Date parsing and question exclusions happen first.
    """
    prefix = re.split(r"[.;\\n]", text[max(0, start - 90):start])[-1]
    return bool(_REVISION_PREFIX.search(prefix))


def submission_deadline_details(text):
    """Return (ISO submission date, explicit 12-hour clock) or empty values.

    A question, walkthrough, or pre-bid date cannot supply the closing time.
    For revised deadlines, the latest submission date wins; on a tied date,
    the last submission statement controls its own clock; a later date-only\n    amendment must not inherit a stale time. No time is inferred.
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
            value = re.sub(r"\s+", " ", re.sub(r"\.", "", raw.group("clock").upper())).strip()
            value = re.sub(r"([AP])\s+(?=M\b)", r"\1", value)
            if ":" not in value:
                value = re.sub(r"^(\d{1,2})", r"\1:00", value)
            try:
                clock = dt.datetime.strptime(value, "%I:%M %p").strftime("%I:%M %p").lstrip("0")
            except ValueError:
                pass
        matches.append((date, clock, match.start(), _is_revised_submission(text, match.start())))
    matches.extend((date, clock, pos, _is_revised_submission(text, pos))
                   for date, clock, pos in _receipt_before_date_matches(text, with_position=True))
    if not matches:
        return "", ""
    # An explicit addendum can move a cutoff EARLIER as well as later.
    # Choosing the maximum date in that case would leave an expired notice
    # eligible for review. The last explicitly revised submission statement
    # supersedes original dates; without one, retain the conservative latest
    # date behavior for unordered source text.
    revisions = [item for item in matches if item[3]]
    if revisions:
        chosen = max(revisions, key=lambda item: item[2])
        return chosen[0].isoformat(), chosen[1]
    latest = max(date for date, _, _, _ in matches)
    matches.sort(key=lambda item: item[2])
    # A later amendment may restate the same date without a clock. Do not
    # carry an earlier (possibly superseded) cutoff into that notice: the
    # latest matching submission statement controls its own time evidence.
    latest_statement = next((clock for date, clock, _, _ in reversed(matches)
                             if date == latest), "")
    return latest.isoformat(), latest_statement



def eastern_deadline_timezone(value):
    """Recognize only explicit NY/PA Eastern timezone labels.

    Missing labels retain the existing NY/PA issuing-authority assumption.
    An explicit non-Eastern, negated or unknown label must never be
    interpreted as Eastern simply because it contains that word.
    """
    if value is None or value == "":
        return True
    if not isinstance(value, str):
        return False
    zone = value.strip().lower()
    if not zone:
        return True
    return zone in {
        "et", "est", "edt", "eastern", "eastern time",
        "eastern standard time", "eastern daylight time",
        "us/eastern", "america/new_york",
        "america/new_york (ny/pa agency-local assumption)",
    }


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
