"""Evidence-based review ordering for UNVERIFIED procurement candidates.

Scores represent which notices deserve a human check first, not the probability
that a bid is open, local, eligible, or worth a particular contract value.
Never use this module to promote a source or verify an opportunity.
"""
import datetime as dt

import civicplus_bids
from submission_deadlines import eastern_deadline_timezone
from publisher_status import publisher_closed

CATEGORY_POINTS = {
    "Tree removal": 30,
    "Storm cleanup": 30,
    "Tree trimming": 28,
    "Vegetation management": 23,
    "Land clearing": 20,
    # Adjacent site-prep work is intentionally ranked below tree/clearing.
    "Related site prep": 10,
}
EVIDENCE_POINTS = {
    "individual county bid candidate": 32,
    "individual metadata bid candidate": 27,
    "PDF bid candidate": 23,
    "direct detail candidate": 18,
    "public bid RSS candidate": 10,
    "indirect news candidate": 0,
}


def review_assessment(lead, today=None, now=None):
    """Add transparent triage metadata; leave original status untouched."""
    today = today or dt.date.today()
    # A notice without a supported service category is not a review lead.
    # Strong metadata (individual detail, future deadline, worksite text) must
    # never compensate for unrelated work such as demolition-only Owego bids.
    if lead.get("category") not in CATEGORY_POINTS:
        return {
            "review_score": 0, "review_priority": "excluded",
            "review_factors": ["no supported tree/clearing/site-prep category"],
            "review_disclaimer": "Triage only; not an open-contract or travel verification",
        }
    score = CATEGORY_POINTS[lead["category"]]
    factors = ["service-category match (not worksite verification)"]
    kind = lead.get("lead_type", "")
    score += EVIDENCE_POINTS.get(kind, 0)
    if kind in ("individual county bid candidate", "individual metadata bid candidate"):
        factors.append("individual notice fetched; open status unverified")
    elif kind == "PDF bid candidate":
        factors.append("PDF notice parsed; open status unverified")
    elif kind == "indirect news candidate":
        factors.append("news mention only; original notice not verified")
    else:
        factors.append("source evidence requires manual review")

    due = lead.get("deadline") or ""
    try:
        parsed = dt.date.fromisoformat(due) if due else None
    except (ValueError, TypeError):
        parsed = None
    # Do not prioritize a notice that the publisher explicitly marks closed,
    # even if its original deadline was later extended or is still in the future.
    if publisher_closed(lead):
        return {
            "review_score": 0, "review_priority": "expired_check",
            "review_factors": factors + ["publisher indicates closed/awarded/cancelled; exclude from active review"],
            "review_disclaimer": "Triage only; not an open-contract or travel verification",
        }

    # A same-day submission time can already have passed. Evaluate it only
    # when the caller supplies an aware scan timestamp; never infer a time
    # from a date-only notice or assume a timezone for a naive timestamp.
    time_passed = (parsed is not None and now is not None
                   and isinstance(now, dt.datetime) and now.tzinfo is not None
                   and now.utcoffset() is not None
                   and bool(lead.get("deadline_time"))
                   and eastern_deadline_timezone(lead.get("deadline_timezone"))
                   and civicplus_bids.closing_passed(
                       parsed.isoformat(), str(lead["deadline_time"]), now))
    if parsed and (parsed < today or time_passed):
        return {
            "review_score": 0, "review_priority": "expired_check",
            "review_factors": factors + ["stated submission cutoff has passed; exclude from active review"],
            "review_disclaimer": "Triage only; not an open-contract or travel verification",
        }
    if parsed:
        score += 12
        factors.append("submission date stated; amendments still unverified")
        if lead.get("deadline_time"):
            score += 4
            factors.append("submission time stated; timezone still requires confirmation")
    else:
        score -= 10
        factors.append("submission deadline unknown")

    if lead.get("scope"):
        score += 8
        factors.append("individual scope field extracted")
    if lead.get("open_status") == "detail_listed_open":
        score += 6
        factors.append("publisher marks detail open; may be stale")
    elif lead.get("open_status") == "listing_open":
        score += 2
        factors.append("publisher marks listing open; may be stale")
    if lead.get("location") and not str(lead["location"]).lower().startswith(
            ("worksite unverified", "ny/pa target area")):
        score += 4
        factors.append("worksite text present; two-hour drive unverified")

    score = max(0, min(100, score))
    return {
        "review_score": score,
        "review_priority": "high" if score >= 70 else "medium" if score >= 45 else "low",
        "review_factors": factors,
        "review_disclaimer": "Triage only; not an open-contract or travel verification",
    }
