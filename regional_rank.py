"""Conservative offline classifier for manually verified regional contract candidates.

Input: JSON array of public procurement notices (not fabricated leads).
Output: regional feed, strictly separate from the two-hour local radar.
Unknown travel times and missing evidence remain review-only.
"""
import argparse
import datetime as dt
import json
import pathlib
import math
from zoneinfo import ZoneInfo

from notice_identity import canonical_url
import civicplus_bids

KEYWORDS = ("debris removal", "disaster debris", "emergency tree", "vegetation management",
            "right-of-way", "tree removal", "stump removal", "stump grinding",
            "tree and stump removal", "tree & stump removal", "land clearing", "storm cleanup",
            "brush clearing", "forestry mulching", "hazard tree", "debris hauling", "road clearing", "roadside clearing",
            "highway clearing", "roadway debris", "blocked road", "downed trees",
            "line clearance", "line clearing", "power line clearing", "powerline clearing",
            "transmission line clearing", "distribution line clearing", "utility right-of-way",
            "utility vegetation", "electric utility vegetation", "storm restoration")
AGENCIES = ("fema", "usace", "army corps", "department of transportation",
            "state dot", "penndot", "nysdot", "emergency management")


def finite_number(value):
    """Treat malformed, non-finite and boolean numeric claims as unknown."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


_CLOSED = frozenset({"closed", "awarded", "cancelled", "canceled", "withdrawn", "expired"})


def _closed_by_publisher(notice):
    for field in ("status", "open_status"):
        state = str(notice.get(field) or "").strip().lower()
        for prefix in ("", "listing_", "detail_listed_"):
            if state.startswith(prefix) and state[len(prefix):] in _CLOSED:
                return True
    return False


def _deadline_state(notice, today, now=None):
    """A date never verifies an open bid; exclude known elapsed NY/PA cutoffs.

    A same-day clock is only actionable when an aware timestamp is available.
    Unknown or malformed clocks and explicitly non-Eastern timezones remain
    unverified rather than being interpreted as an Eastern submission cutoff.
    """
    raw = notice.get("deadline")
    if raw in (None, ""):
        return "unknown"
    if not isinstance(raw, str):
        return "invalid"
    try:
        due = dt.date.fromisoformat(raw)
    except ValueError:
        return "invalid"
    if due < today:
        return "expired"
    timezone = str(notice.get("deadline_timezone") or "").strip().lower()
    eastern = not timezone or "eastern" in timezone or "new_york" in timezone
    if (due == today and eastern and isinstance(now, dt.datetime)
            and now.tzinfo is not None and now.utcoffset() is not None
            and now.astimezone(ZoneInfo("America/New_York")).date() == today
            and civicplus_bids.closing_passed(
                due.isoformat(), str(notice.get("deadline_time") or ""), now)):
        return "expired"
    return "stated_unverified"


def classify(notice, today=None, now=None):
    if not isinstance(notice, dict):
        return None
    # Production scans check explicit same-day cutoffs using an aware Eastern
    # clock. Tests supplying a date alone do not silently invent a clock.
    if now is None and today is None:
        now = dt.datetime.now(ZoneInfo("America/New_York"))
    if today is None:
        today = (now.astimezone(ZoneInfo("America/New_York")).date()
                 if isinstance(now, dt.datetime) and now.tzinfo is not None
                 and now.utcoffset() is not None
                 else dt.datetime.now(ZoneInfo("America/New_York")).date())
    if _closed_by_publisher(notice):
        return None
    deadline_state = _deadline_state(notice, today, now=now)
    if deadline_state == "expired":
        return None
    title = str(notice.get("title") or "")
    description = str(notice.get("summary") or "")
    content = (title + " " + description).lower()
    if not any(term in content for term in KEYWORDS):
        return None
    url = canonical_url(notice.get("url"))
    if not url.startswith("https://"):
        return None
    hours = finite_number(notice.get("drive_hours"))
    if hours is not None and (hours < 0 or hours > 12):
        return None
    # Strings like "false" and NaN/Infinity must never certify travel.
    # Only an explicit boolean True plus a finite, in-range route can do so.
    travel_verified = notice.get("travel_verified") is True and hours is not None
    amount = finite_number(notice.get("estimated_value_usd"))
    days = finite_number(notice.get("estimated_duration_days"))
    if amount is not None and amount < 0:
        amount = None
    if days is not None and days < 0:
        days = None
    score = 0
    if amount is not None and amount >= 250000: score += 3
    elif amount is not None and amount >= 100000: score += 2
    if days is not None and days >= 7: score += 2
    if any(term in content for term in ("disaster debris", "emergency tree", "debris removal", "road clearing", "power line clearing", "line clearance", "storm restoration")): score += 2
    if any(term in content for term in AGENCIES): score += 1
    if notice.get("subcontracting_available") is True: score += 1
    result = dict(notice)
    result["url"] = url
    result["deadline_status"] = deadline_state
    result["drive_hours"] = hours
    result["travel_verified"] = travel_verified
    result["priority_score"] = score
    result["priority"] = "high" if score >= 5 else "medium" if score >= 3 else "review"
    result["distance_status"] = "verified" if travel_verified else "unverified"
    result["status"] = "review required"
    return result

def build(notices, today=None, now=None):
    # One public notice may appear through several marketing/tracking URLs.
    # Keep substantive query keys (including bid IDs) so distinct bids survive.
    by_url = {}
    for notice in notices:
        item = classify(notice, today=today, now=now)
        if item is None:
            continue
        key = item["url"]
        previous = by_url.get(key)
        quality = lambda n: (n["priority_score"], bool(n.get("deadline")),
                             len(str(n.get("summary") or "")))
        if previous is None or quality(item) > quality(previous):
            by_url[key] = item
    results = sorted(by_url.values(), key=lambda n: (-n["priority_score"], str(n.get("title", ""))))
    return {"updated": dt.datetime.now(dt.timezone.utc).isoformat(),
            "coverage_note": ("Review-only candidates; past deadlines and publisher-closed notices excluded. "
                              "Unknown deadlines, bid status, eligibility and travel require verification."),
            "opportunities": results}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    args = parser.parse_args()
    notices = json.loads(args.input.read_text(encoding="utf-8"))
    if not isinstance(notices, list): raise ValueError("Expected a JSON array of notices")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(build(notices), indent=2) + "\n", encoding="utf-8")
if __name__ == "__main__": main()
