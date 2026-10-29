"""Explain monitoring coverage without confusing homepage access with bid extraction.

Source health is diagnostic, not a claim that a contract is open or a
crawler is authorized. A staged official URL never counts as a live adapter.
"""
import re


def _number(pattern, status):
    match = re.search(pattern, status)
    return int(match.group(1)) if match else 0


def classify(source, status):
    mode = source.get("mode", "discovery_pending")
    configured = (mode == "direct_page" and source.get("verified_url") is True
                  and bool(source.get("url")))
    if not configured:
        direct_state = "staged_official_url" if source.get("candidate_official_url") else "not_configured"
    elif "direct blocked by robots policy" in status:
        direct_state = "robots_blocked"
    elif "individual listing ingestion not connected" in status:
        direct_state = "access_required"
    elif "direct fetched;" in status:
        direct_state = "fetched_unverified"
    elif "direct error:" in status:
        direct_state = "fetch_error"
    else:
        direct_state = "not_fetched"

    if "indirect RSS ok;" in status:
        indirect_state = "ok"
    elif "indirect RSS error: RobotsDenied" in status:
        indirect_state = "robots_blocked"
    elif "indirect RSS error:" in status:
        indirect_state = "error"
    else:
        indirect_state = "not_run"

    # A successful listing fetch can conceal blocked or failed individual
    # notice requests. Record those separately from homepage availability.
    detail_errors = _number(r"\b(\d+) detail errors:", status)
    detail_checked = _number(r"\b(\d+) (?:relevant )?details checked\b", status)
    details_fetched = _number(r"\b(\d+) individual bid details fetched\b", status)
    error_section = re.search(r"\b\d+ detail errors:\s*([^;]*)", status)
    error_names = error_section.group(1) if error_section else ""
    if "RobotsDenied" in error_names:
        detail_access_state = "robots_blocked"
    elif detail_errors:
        detail_access_state = "partial_fetch_errors" if details_fetched else "fetch_error"
    elif details_fetched:
        detail_access_state = "retrieved_unverified"
    elif detail_checked:
        detail_access_state = "attempted_unverified"
    else:
        detail_access_state = "not_attempted"

    return {
        "name": source["name"],
        "mode": mode,
        "direct_state": direct_state,
        "indirect_state": indirect_state,
        "direct_url": source.get("url", "") if configured else "",
        "staged_official_url": source.get("candidate_official_url", "") if not configured else "",
        "activation_gate": source.get("activation_gate", ""),
        "individual_bid_records_found": _number(r"\b(\d+) individual bid records\b", status),
        "detail_fetches_attempted": detail_checked,
        "individual_bid_details_fetched": details_fetched,
        "detail_errors": detail_errors,
        "detail_access_state": detail_access_state,
        "pdf_budget_skips": _number(r"\b(\d+) PDF requests skipped at budget\b", status),
        "unverified_candidates": _number(r"\b(\d+) unverified candidates\b", status)
                                  or _number(r"; (\d+) candidates(?:;|$)", status),
        "diagnostic": status,
    }


def summarize(sources, statuses):
    rows = [classify(src, statuses.get(src["name"], "")) for src in sources]
    states = ("fetched_unverified", "robots_blocked", "access_required",
              "fetch_error", "not_fetched", "staged_official_url", "not_configured")
    counts = {state: sum(row["direct_state"] == state for row in rows) for state in states}
    counts["configured_direct"] = sum(bool(row["direct_url"]) for row in rows)
    counts["indirect_robots_blocked"] = sum(row["indirect_state"] == "robots_blocked" for row in rows)
    counts["individual_bid_records_found"] = sum(row["individual_bid_records_found"] for row in rows)
    counts["detail_fetches_attempted"] = sum(row["detail_fetches_attempted"] for row in rows)
    counts["individual_bid_details_fetched"] = sum(row["individual_bid_details_fetched"] for row in rows)
    counts["detail_errors"] = sum(row["detail_errors"] for row in rows)
    counts["detail_robots_blocked_sources"] = sum(row["detail_access_state"] == "robots_blocked" for row in rows)
    counts["pdf_budget_skips"] = sum(row["pdf_budget_skips"] for row in rows)
    counts["unverified_candidates"] = sum(row["unverified_candidates"] for row in rows)
    return {
        "counts": counts,
        "sources": rows,
        "warning": ("A source can be fetched without extracting individual bids. "
                    "Detail fetch attempts do not establish valid notices; "
                    "individual details fetched prove retrieval, not open status. "
                    "Individual-detail robots blocks and errors are reported separately. "
                    "Staged URLs are not monitored; all leads remain unverified.")
    }
