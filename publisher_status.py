"""Conservative publisher closure evidence shared by local and regional triage.

This checks explicit status fields only, never incidental words in a bid scope.
A question-period closure is not a solicitation closure.
"""
import re

_CLOSED = re.compile(
    r"^(?:closed|awarded|cancelled|canceled|withdrawn|expired)"
    r"(?:$|[\\s:;,()\\-–—/])", re.I
)
_QUESTION_ONLY = re.compile(
    r"^closed\\s+(?:for|to)\\s+(?:questions?|inquir(?:y|ies)|"
    r"clarifications?|rfis?|addenda)\\b", re.I
)


def publisher_closed(notice):
    """True only when a publisher's status field explicitly closes the bid."""
    if not isinstance(notice, dict):
        return False
    for field in ("status", "open_status"):
        raw = notice.get(field)
        if not isinstance(raw, str):
            continue
        state = raw.strip().lower()
        for prefix in ("detail_listed_", "listing_"):
            if state.startswith(prefix):
                state = state[len(prefix):]
                break
        if _CLOSED.match(state) and not _QUESTION_ONLY.match(state):
            return True
    return False
