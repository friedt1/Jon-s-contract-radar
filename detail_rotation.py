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
    # Keep the first ranked link stable even if every candidate ties. This
    # preserves predictable first-notice checks on small municipal indexes.
    start = max(1, start)
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


def rotate_selected_boundary_ties(ordered, budget, now, priority, selected):
    """Rotate tied candidates at a *separate* request budget boundary.

    Some detail links consume both the general detail budget and a smaller
    PDF download budget. Rotating only at the general boundary can retry the
    same five PDFs forever when the page lists fewer than MAX_DETAIL links.
    Rotate only selected (PDF-shaped) links in their existing slots, leaving
    HTML candidates and higher-ranked PDF groups untouched. This changes
    fetch order, not access permission, eligibility, or publication status.
    """
    items = list(ordered)
    if not isinstance(budget, int) or budget <= 0:
        return items
    positions = [i for i, item in enumerate(items) if selected(item)]
    if len(positions) <= budget:
        return items
    subset = [items[i] for i in positions]
    rotated = rotate_boundary_ties(subset, budget, now, priority)
    for index, item in zip(positions, rotated):
        items[index] = item
    return items
