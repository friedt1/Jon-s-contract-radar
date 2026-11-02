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
from submission_deadlines import eastern_deadline_timezone
from publisher_status import publisher_closed
from scan import positive_scope_text

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


def _closed_by_publisher(notice):
    return publisher_closed(notice)


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
    eastern = eastern_deadline_timezone(notice.get("deadline_timezone"))
    if (due == today and eastern and isinstance(now, dt.datetime)
            and now.tzinfo is not None and now.utcoffset() is not None
            and now.astimezone(ZoneInfo("America/New_York")).date() == today
            and civicplus_bids.closing_passed(
                due.isoformat(), str(notice.get("deadline_time") or ""), now)):
        return "expired"
    return "stated_unverified"


def _normalized_eastern_clock(notice):
    """Compare only valid, equivalent Eastern bid clocks across duplicates.

    Different textual renderings of the same cutoff (9 AM vs 09:00 am)
    must not manufacture a conflict. An invalid or non-Eastern clock
    cannot certify a cutoff or conflict with a valid Eastern clock.
    """
    if not eastern_deadline_timezone(notice.get("deadline_timezone")):
        return ""
    return civicplus_bids._clock(str(notice.get("deadline_time") or "")).lower()


def _normalized_bid_number(notice):
    """Normalize an explicit issuer bid number, never infer one from prose."""
    value = notice.get("bid_number")
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""


def _shared_listing_numbered_urls(notices):
    """Split a shared URL only with evidence of distinct relevant bid numbers.

    A single bid number and an unnumbered copy retain the old URL-based
    deduplication behavior. Distinct explicit numbers on the same official
    listing page must not overwrite one another or share deadline conflicts.
    """
    numbers = {}
    for notice in notices:
        if not isinstance(notice, dict):
            continue
        number = _normalized_bid_number(notice)
        url = canonical_url(notice.get("url"))
        scope = positive_scope_text(
            str(notice.get("title") or "") + " " +
            str(notice.get("summary") or ""))
        if (number and url.startswith("https://")
                and any(term in scope for term in KEYWORDS)):
            numbers.setdefault(url, set()).add(number)
    return {url for url, values in numbers.items() if len(values) > 1}


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
    content = positive_scope_text(title + " " + description)
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
    # Resolve a single Eastern reference date for every duplicate in this batch.
    if today is None:
        today = (now.astimezone(ZoneInfo("America/New_York")).date()
                 if isinstance(now, dt.datetime) and now.tzinfo is not None
                 and now.utcoffset() is not None
                 else dt.datetime.now(ZoneInfo("America/New_York")).date())
    # One public notice may appear through several marketing/tracking URLs.
    # Keep substantive query keys (including bid IDs) so distinct bids survive.
    # A publisher-closed copy must not be silently discarded before dedup:
    # an otherwise-open duplicate may be stale. Withhold the conflicting
    # identity from active review until its current publisher status is checked.
    # An old date alone does not trigger this gate (amendments can extend bids).
    notices = list(notices)
    numbered_listing_urls = _shared_listing_numbered_urls(notices)

    def identity(notice, url):
        # Only split a shared URL after seeing at least two independently
        # numbered relevant notices. Never manufacture bid IDs from titles.
        number = (_normalized_bid_number(notice)
                  if url in numbered_listing_urls else "")
        return (url, number)

    by_url = {}
    publisher_closed_urls = set()
    # Keep all independently stated submission cutoffs for the same notice.
    # A higher-value or longer duplicate is not evidence that its deadline
    # supersedes a different publisher cutoff.
    dates_by_url = {}
    clocks_by_url = {}
    # Explicit non-Eastern clocks cannot corroborate an NY/PA local cutoff.
    # Retain that contradictory evidence across canonical-URL duplicates.
    incompatible_clocks_by_url = set()
    # A same-day elapsed clock can be lost when classify() rejects that copy.
    # Retain its evidence so a duplicate without a clock cannot appear
    # uncontested or implicitly reopen an already elapsed submission cutoff.
    elapsed_same_day_clocks = {}
    for notice in notices:
        if not isinstance(notice, dict):
            continue
        if publisher_closed(notice):
            closed_url = canonical_url(notice.get("url"))
            if closed_url.startswith("https://"):
                publisher_closed_urls.add(identity(notice, closed_url))
            continue
        # Preserve valid Eastern same-day clock evidence *before* classify()
        # discards an already elapsed copy. Otherwise a 9 AM copy disappears
        # at 11 AM and a duplicate claiming 2 PM looks uncontested.
        # This never revives an elapsed notice: it only marks a surviving
        # duplicate's deadline as conflicting and unverified.
        candidate_url = canonical_url(notice.get("url"))
        candidate_key = identity(notice, candidate_url)
        candidate_date = notice.get("deadline")
        candidate_text = positive_scope_text(
            str(notice.get("title") or "") + " " +
            str(notice.get("summary") or ""))
        # Record every independently stated valid submission date before
        # classify() drops an expired copy. An older cutoff may have been
        # superseded by an amendment, but the surviving later date is not
        # independently verified while those copies disagree. Withhold the
        # selected deadline and show both dates for review instead.
        if (candidate_url.startswith("https://")
                and isinstance(candidate_date, str)
                and any(term in candidate_text for term in KEYWORDS)):
            try:
                dt.date.fromisoformat(candidate_date)
            except ValueError:
                pass
            else:
                dates_by_url.setdefault(candidate_key, set()).add(candidate_date)
                clock = _normalized_eastern_clock(notice)
                if clock:
                    clocks_by_url.setdefault((candidate_key, candidate_date), set()).add(clock)
                elif (not eastern_deadline_timezone(notice.get("deadline_timezone"))
                      and civicplus_bids._clock(str(notice.get("deadline_time") or ""))):
                    incompatible_clocks_by_url.add((candidate_key, candidate_date))
                # A known elapsed cutoff must survive even if classify()
                # drops this copy and a later duplicate remains.
                if (candidate_date == today.isoformat() and clock
                        and _deadline_state(notice, today, now=now) == "expired"):
                    elapsed_same_day_clocks.setdefault(candidate_key, set()).add(clock)
        item = classify(notice, today=today, now=now)
        if item is None:
            continue
        key = identity(notice, item["url"])
        due = item.get("deadline")
        if isinstance(due, str):
            try:
                dt.date.fromisoformat(due)
            except ValueError:
                pass
            else:
                dates_by_url.setdefault(key, set()).add(due)
                clock = _normalized_eastern_clock(item)
                if clock:
                    clocks_by_url.setdefault((key, due), set()).add(clock)
        previous = by_url.get(key)
        quality = lambda n: (n["priority_score"], bool(n.get("deadline")),
                             len(str(n.get("summary") or "")))
        if previous is None or quality(item) > quality(previous):
            by_url[key] = item
    for closed_key in publisher_closed_urls:
        if closed_key[1]:
            # A numbered closure applies to that solicitation only.
            by_url.pop(closed_key, None)
            # An unnumbered copy cannot independently establish that it is
            # a different live solicitation on the same listing page.
            by_url.pop((closed_key[0], ""), None)
        else:
            # A generic listing-level Closed status is ambiguous. Fail
            # closed rather than reviving one of its numbered candidates.
            for key in tuple(by_url):
                if key[0] == closed_key[0]:
                    by_url.pop(key, None)
    for key, item in by_url.items():
        dates = dates_by_url.get(key, set())
        if len(dates) > 1:
            # Do not publish one arbitrarily selected deadline as if it were
            # the current cutoff. Keep the notice review-only and expose the
            # conflicting date evidence for a human to check.
            item["deadline_conflict"] = sorted(dates)
            item["deadline"] = ""
            item["deadline_time"] = ""
            item["deadline_timezone"] = ""
            item["deadline_status"] = "conflicting_unverified"
        elif len(dates) == 1:
            due = next(iter(dates))
            clocks = clocks_by_url.get((key, due), set())
            if len(clocks) > 1 or (clocks and (key, due) in incompatible_clocks_by_url):
                # A duplicate with an explicit non-Eastern clock cannot
                # corroborate an Eastern bid cutoff. Neither version is
                # independently authoritative; withhold the selected time.
                conflict = set(clocks)
                if (key, due) in incompatible_clocks_by_url:
                    conflict.add("explicit non-Eastern timezone")
                item["deadline_conflict"] = sorted(conflict)
                item["deadline_time"] = ""
                item["deadline_timezone"] = ""
                item["deadline_status"] = "conflicting_unverified"
            elif due == today.isoformat() and key in elapsed_same_day_clocks:
                # A date-only or timezone-incompatible duplicate cannot
                # erase a publisher-stated cutoff that already elapsed.
                # Unlike two explicit conflicting clocks, the surviving
                # notice provides no independently confirmed later cutoff.
                item["deadline_conflict"] = sorted(
                    set(clocks) | {"later cutoff not independently confirmed"})
                item["deadline"] = ""
                item["deadline_time"] = ""
                item["deadline_timezone"] = ""
                item["deadline_status"] = "conflicting_unverified"
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
