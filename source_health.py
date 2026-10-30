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
    configured = (mode in {"direct_page", "official_feed", "authorized_api"}
                  and source.get("verified_url") is True
                  and bool(source.get("url")))
    if not configured:
        direct_state = "staged_official_url" if source.get("candidate_official_url") else "not_configured"
    elif "direct blocked by robots policy" in status:
        direct_state = "robots_blocked"
    elif "individual listing ingestion not connected" in status:
        direct_state = "access_required"
    # An HTTP refusal, rejected redirect, and rate limit are not ordinary
    # transient fetch errors or successful individual-notice ingestion.
    # A 403 may be anti-bot protection rather than a login requirement:
    # label it as HTTP-blocked, not "credentials required".
    elif re.search(r"\bdirect error: HTTPError HTTP (?:401|403)\b", status):
        direct_state = "http_blocked"
    elif "direct error: UnsafeRedirect" in status:
        direct_state = "redirect_blocked"
    elif "direct error: HTTPError HTTP 429" in status:
        direct_state = "rate_limited"
    elif "unsupported content type" in status:
        direct_state = "unsupported_content"
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
        "pdf_fetch_attempts": _number(r"\b(\d+) PDF-shaped requests attempted\b", status),
        "pdf_budget_skips": _number(r"\b(\d+) PDF requests skipped at budget\b", status),
        "result_award_links_excluded": _number(r"\b(\d+) result/award links excluded\b", status),
        "external_provider_links_skipped": _number(
            r"\b(\d+) external provider links skipped \(access required\)", status),
        "unverified_candidates": _number(r"\b(\d+) unverified candidates\b", status)
                                  or _number(r"; (\d+) candidates(?:;|$)", status),
        "diagnostic": status,
    }


def summarize(sources, statuses):
    rows = [classify(src, statuses.get(src["name"], "")) for src in sources]
    states = ("fetched_unverified", "robots_blocked", "access_required",
              "http_blocked", "redirect_blocked", "rate_limited",
              "unsupported_content", "fetch_error", "not_fetched",
              "staged_official_url", "not_configured")
    counts = {state: sum(row["direct_state"] == state for row in rows) for state in states}
    counts["configured_direct"] = sum(bool(row["direct_url"]) for row in rows)
    # Landing-page configuration is not a working provider integration.
    # These are potential fetch targets, not proof of permitted extraction.
    counts["configured_access_required"] = sum(
        bool(row["direct_url"]) and row["direct_state"] == "access_required" for row in rows)
    counts["configured_fetch_targets"] = (
        counts["configured_direct"] - counts["configured_access_required"])
    counts["indirect_robots_blocked"] = sum(row["indirect_state"] == "robots_blocked" for row in rows)
    counts["individual_bid_records_found"] = sum(row["individual_bid_records_found"] for row in rows)
    counts["detail_fetches_attempted"] = sum(row["detail_fetches_attempted"] for row in rows)
    counts["individual_bid_details_fetched"] = sum(row["individual_bid_details_fetched"] for row in rows)
    counts["detail_errors"] = sum(row["detail_errors"] for row in rows)
    counts["detail_robots_blocked_sources"] = sum(row["detail_access_state"] == "robots_blocked" for row in rows)
    counts["pdf_fetch_attempts"] = sum(row["pdf_fetch_attempts"] for row in rows)
    counts["pdf_budget_skips"] = sum(row["pdf_budget_skips"] for row in rows)
    counts["result_award_links_excluded"] = sum(
        row["result_award_links_excluded"] for row in rows)
    counts["external_provider_links_skipped"] = sum(
        row["external_provider_links_skipped"] for row in rows)
    counts["unverified_candidates"] = sum(row["unverified_candidates"] for row in rows)
    return {
        "counts": counts,
        "sources": rows,
        "warning": ("A source can be fetched without extracting individual bids. "
                    "Detail fetch attempts do not establish valid notices; "
                    "individual details fetched prove retrieval, not open status. "
                    "Individual-detail robots blocks and errors are reported separately. "
                    "External provider links require an approved adapter and are not followed. "
                    "Configured access-required portals are not direct fetch targets. "
                    "HTTP refusals, unsafe redirects, rate limits and unsupported "
                    "content are distinguished from transient fetch errors. "
                    "Staged URLs are not monitored; all leads remain unverified.")
    }
