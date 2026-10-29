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

KEYWORDS = ("debris removal", "disaster debris", "emergency tree", "vegetation management",
            "right-of-way", "tree removal", "land clearing", "storm cleanup",
            "brush clearing", "forestry mulching", "hazard tree", "debris hauling", "road clearing", "roadside clearing",
            "highway clearing", "roadway debris", "blocked road", "downed trees",
            "line clearance", "line clearing", "power line clearing", "powerline clearing",
            "transmission line clearing", "distribution line clearing", "utility right-of-way",
            "utility vegetation", "electric utility vegetation", "storm restoration")
AGENCIES = ("fema", "usace", "army corps", "department of transportation",
            "state dot", "penndot", "nysdot", "emergency management")


def finite_nonnegative(value):
    """Treat malformed, non-finite and boolean numeric claims as unknown."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and number >= 0 else None


def classify(notice):
    title = str(notice.get("title") or "")
    description = str(notice.get("summary") or "")
    content = (title + " " + description).lower()
    if not any(term in content for term in KEYWORDS):
        return None
    url = str(notice.get("url") or "")
    if not url.startswith("https://"):
        return None
    hours = finite_nonnegative(notice.get("drive_hours"))
    if hours is not None and hours > 12:
        return None
    # Strings like "false" and NaN/Infinity must never certify travel.
    # Only an explicit boolean True plus a finite, in-range route can do so.
    travel_verified = notice.get("travel_verified") is True and hours is not None
    amount = finite_nonnegative(notice.get("estimated_value_usd"))
    days = finite_nonnegative(notice.get("estimated_duration_days"))
    score = 0
    if amount is not None and amount >= 250000: score += 3
    elif amount is not None and amount >= 100000: score += 2
    if days is not None and days >= 7: score += 2
    if any(term in content for term in ("disaster debris", "emergency tree", "debris removal", "road clearing", "power line clearing", "line clearance", "storm restoration")): score += 2
    if any(term in content for term in AGENCIES): score += 1
    if notice.get("subcontracting_available") is True: score += 1
    result = dict(notice)
    result["drive_hours"] = hours
    result["travel_verified"] = travel_verified
    result["priority_score"] = score
    result["priority"] = "high" if score >= 5 else "medium" if score >= 3 else "review"
    result["distance_status"] = "verified" if travel_verified else "unverified"
    result["status"] = "review required"
    return result

def build(notices):
    results = [x for n in notices if (x := classify(n)) is not None]
    results.sort(key=lambda n: (-n["priority_score"], str(n.get("title", ""))))
    return {"updated": dt.datetime.now(dt.timezone.utc).isoformat(),
            "coverage_note": "Candidate notices only; bid status, eligibility and drive time must be verified at source.",
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
