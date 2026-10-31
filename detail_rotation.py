"""Bounded, deterministic exploration of lower-ranked public bid detail links.

The scanner must keep high-priority notices ahead of generic archives, but a
fixed request budget must not inspect the exact same first N links forever.
This only changes WHICH permitted individual links are attempted; it never
changes eligibility, source permissions, deadlines, or publication status.
"""
import datetime as dt


def rotate_exploration_window(ordered, budget, now):
    """Preserve the top 75% of a request budget and rotate its remaining slots.

    The ordered argument is already ranked by the caller. Stable top slots
    retain urgent/relevant notices, while a bounded slice of remaining
    candidates advances each UTC hour. Return the full list (not truncated)
    so the caller can still report unfetched candidates accurately.

    A naive or missing clock cannot safely define a rotation window; retain
    the original order instead. No network requests happen here.
    """
    items = list(ordered)
    if not isinstance(budget, int) or budget <= 1 or len(items) <= budget:
        return items
    if (not isinstance(now, dt.datetime) or now.tzinfo is None
            or now.utcoffset() is None):
        return items
    exploration = max(1, (budget + 3) // 4)
    protected = budget - exploration
    tail = items[protected:]
    # The tail is strictly longer than exploration when len(items) > budget.
    hour = int(now.astimezone(dt.timezone.utc).timestamp() // 3600)
    offset = (hour * exploration) % len(tail)
    return items[:protected] + tail[offset:] + tail[:offset]
