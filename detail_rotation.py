"""Deterministic exploration of tied, deferred public bid detail links.

Never promote expired or lower-ranked notices ahead of future/relevant ones.
Rotate only the equal-priority group straddling the fixed request budget.
This changes retrieval order, not eligibility, permissions or publication.
"""
import datetime as dt


def rotate_boundary_ties(ordered, budget, now, priority):
    """Rotate a tied group crossing the bounded detail-request cutoff.

    Callers must sort the input by the same priority function first. Every
    higher-ranked group remains ahead of every lower-ranked group. If the
    boundary falls exactly between priority groups, leave the order unchanged
    rather than fetching lower-priority/expired notices prematurely.

    The full list is retained for honest deferred-count diagnostics. An
    aware UTC-hour clock makes repeated scans stable within an hour and
    advances a partial tie group in subsequent hours.
    """
    items = list(ordered)
    if (not isinstance(budget, int) or budget <= 0 or len(items) <= budget
            or not isinstance(now, dt.datetime) or now.tzinfo is None
            or now.utcoffset() is None):
        return items
    boundary = priority(items[budget - 1])
    start = budget - 1
    while start > 0 and priority(items[start - 1]) == boundary:
        start -= 1
    # With one available detail slot, pinning the first tied candidate would
    # starve every other notice forever. Keep that first link stable only when
    # at least two detail slots are available; otherwise rotate the full tie.
    start = max(1 if budget > 1 else 0, start)
    if start >= budget:
        return items
    end = budget
    while end < len(items) and priority(items[end]) == boundary:
        end += 1
    if end == budget:
        return items
    group = items[start:end]
    window = budget - start
    hour = int(now.astimezone(dt.timezone.utc).timestamp() // 3600)
    offset = (hour * window) % len(group)
    items[start:end] = group[offset:] + group[:offset]
    return items
