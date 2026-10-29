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
         r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?\s+\d{4}))")
_LABEL = (r"(?P<label>due(?:\s+date)?|closing(?:\s+date(?:/time)?)?|"
          r"bids?\s+(?:due|received)|submit(?:ted)?\s+(?:by|until)|deadline)")
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
    r"site\s+visits?|walk[- ]?throughs?)\s*$",
    re.I,
)


def _date(value):
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%B %d %Y", "%b %d %Y"):
        try:
            return dt.datetime.strptime(value.replace(",", ""), fmt).date()
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
    return max(dates).isoformat() if dates else ""
