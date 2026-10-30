"""Conservative publisher closure evidence shared by local and regional triage.

This checks explicit status fields only, never incidental words in a bid scope.
A question-period closure is not a solicitation closure.
"""
import re

_CLOSED = re.compile(
    r"^(?:closed|awarded|cancelled|canceled|withdrawn|expired)"
    r"(?:$|[\s:;,()\-–—/])", re.I
)
# Only strip an explicit status-field label, not arbitrary scope prose.
# Publishers sometimes store "Bid Status: Awarded" as the field value.
_LABELED_STATUS = re.compile(
    r"^(?:(?:bid|solicitation|notice|procurement|current)\s+)?"
    r"status\s*[:\-–—]\s*", re.I
)
_QUESTION_ONLY = re.compile(
    # Publisher labels such as "Closed - for questions" and "Closed: Q&A"
    # describe a Q&A milestone, not the submission status.
    r"^closed[\s:;,()\-–—/]+(?:(?:for|to)\s+)?"
    r"(?:questions?|q\s*&\s*a|inquir(?:y|ies)|"
    r"clarifications?|rfis?|addenda)\b", re.I
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
        state = _LABELED_STATUS.sub("", state, count=1)
        if _CLOSED.match(state) and not _QUESTION_ONLY.match(state):
            return True
    return False
