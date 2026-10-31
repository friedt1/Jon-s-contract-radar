"""Explain monitoring coverage without confusing homepage access with bid extraction.

Source health is diagnostic, not a claim that a contract is open or a
crawler is authorized. A staged official URL never counts as a live adapter.
"""
import re

from source_config import direct_configured, direct_fetch_target, valid_public_https_url


def _number(pattern, status):
    match = re.search(pattern, status)
    return int(match.group(1)) if match else 0


def _access_error_types(names, count):
    """All observed access failures, not just the highest-priority one.

    A single scan may hit a robots refusal on one detail and an HTTP 429
    on another. Preserve both in structured diagnostics. Do not infer an
    access problem from error text when the recorded error count is zero.
    """
    if not count:
        return []
    types = []
    if "RobotsDenied" in names:
        types.append("robots_blocked")
    if re.search(r"\bHTTPError HTTP (?:401|403)\b", names):
        types.append("http_blocked")
    if "UnsafeRedirect" in names:
        types.append("redirect_blocked")
    if "HTTPError HTTP 429" in names:
        types.append("rate_limited")
    return types


def classify(source, status):
    mode = source.get("mode", "discovery_pending")
    configured = direct_configured(source)
    # Access requirements are configuration facts, not dependent on a
    # successful scanner run. Preserve them when the feed is stale or a
    # source is robots-blocked; never count a provider gateway as an
    # operational direct-fetch target merely because its status is missing.
    staged_provider_access_required = (
        not configured and mode == "discovery_pending"
        and valid_public_https_url(source.get("candidate_official_url"))
        and (source.get("provider_access_required") is True
             or bool(source.get("delegated_provider")))
    )
    provider_access_required = configured and (
        source.get("provider_access_required") is True
        or bool(source.get("delegated_provider"))
        or "individual listing ingestion not connected" in status
    )
    if not configured:
        direct_state = ("staged_official_url" if mode == "discovery_pending" and
                        valid_public_https_url(source.get("candidate_official_url"))
                        else "not_configured")
    elif provider_access_required:
        # Provider approval remains a prerequisite even when an older scan
        # recorded a robots refusal on the gateway page. Preserve that
        # refusal in the raw diagnostic, but do not misclassify the source
        # as a robot-only integration that would activate if robots changed.
        direct_state = "access_required"
    elif "direct blocked by robots policy" in status:
        direct_state = "robots_blocked"
    elif not direct_fetch_target(source):
        # Feed/API configuration is not operational until its own adapter exists.
        direct_state = "adapter_not_implemented"
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
    detail_error_types = _access_error_types(error_names, detail_errors)
    if "robots_blocked" in detail_error_types:
        detail_access_state = "robots_blocked"
    elif "http_blocked" in detail_error_types:
        detail_access_state = "http_blocked"
    elif "redirect_blocked" in detail_error_types:
        detail_access_state = "redirect_blocked"
    elif "rate_limited" in detail_error_types:
        detail_access_state = "rate_limited"
    elif detail_errors:
        detail_access_state = "partial_fetch_errors" if details_fetched else "fetch_error"
    elif details_fetched:
        detail_access_state = "retrieved_unverified"
    elif detail_checked:
        detail_access_state = "attempted_unverified"
    else:
        detail_access_state = "not_attempted"

    # Later listing pages may fail even when the first page succeeds.
    # Preserve that incomplete-coverage evidence instead of reporting success.
    pagination_errors = _number(r"\b(\d+) pagination errors:", status)
    pagination_section = re.search(r"\b\d+ pagination errors:\s*([^;]*)", status)
    pagination_names = pagination_section.group(1) if pagination_section else ""
    pagination_error_types = _access_error_types(pagination_names, pagination_errors)
    if "robots_blocked" in pagination_error_types:
        pagination_access_state = "robots_blocked"
    elif "http_blocked" in pagination_error_types:
        pagination_access_state = "http_blocked"
    elif "redirect_blocked" in pagination_error_types:
        pagination_access_state = "redirect_blocked"
    elif "rate_limited" in pagination_error_types:
        pagination_access_state = "rate_limited"
    elif pagination_errors:
        pagination_access_state = "partial_listing_errors"
    else:
        pagination_access_state = "no_reported_errors"

    return {
        "name": source["name"],
        "mode": mode,
        "direct_state": direct_state,
        "provider_access_required": provider_access_required,
        "staged_provider_access_required": staged_provider_access_required,
        "indirect_state": indirect_state,
        "direct_url": source.get("url", "") if configured else "",
        "staged_official_url": source.get("candidate_official_url", "") if not configured else "",
        "activation_gate": source.get("activation_gate", ""),
        "individual_bid_records_found": _number(r"\b(\d+) individual bid records\b", status),
        "detail_fetches_attempted": detail_checked,
        "detail_budget_deferred": _number(
            r"\b(\d+) individual bid records deferred at detail budget\b", status),
        "detail_candidates_deferred": _number(
            r"\b(\d+) detail candidates deferred at request budget\b", status),
        "individual_bid_details_fetched": details_fetched,
        "detail_errors": detail_errors,
        "pagination_errors": pagination_errors,
        "pagination_access_state": pagination_access_state,
        "pagination_error_types": pagination_error_types,
        "detail_access_state": detail_access_state,
        "detail_error_types": detail_error_types,
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
              "staged_official_url", "not_configured", "adapter_not_implemented")
    counts = {state: sum(row["direct_state"] == state for row in rows) for state in states}
    counts["configured_direct"] = sum(bool(row["direct_url"]) for row in rows)
    # Landing-page configuration is not a working provider integration.
    # These are potential fetch targets, not proof of permitted extraction.
    counts["configured_access_required"] = sum(
        row["provider_access_required"] for row in rows)
    # A staged official entrypoint may already require supplier registration.
    # Report it separately; it is NOT a configured direct integration.
    counts["staged_provider_access_required"] = sum(
        row["staged_provider_access_required"] for row in rows)
    counts["configured_unimplemented_adapters"] = sum(
        direct_configured(src) and not direct_fetch_target(src) for src in sources)
    counts["configured_fetch_targets"] = sum(
        direct_fetch_target(src) and not row["provider_access_required"]
        for src, row in zip(sources, rows))
    counts["indirect_robots_blocked"] = sum(row["indirect_state"] == "robots_blocked" for row in rows)
    counts["individual_bid_records_found"] = sum(row["individual_bid_records_found"] for row in rows)
    counts["detail_fetches_attempted"] = sum(row["detail_fetches_attempted"] for row in rows)
    counts["detail_budget_deferred"] = sum(row["detail_budget_deferred"] for row in rows)
    counts["detail_budget_incomplete_sources"] = sum(
        row["detail_budget_deferred"] > 0 for row in rows)
    counts["detail_candidates_deferred"] = sum(
        row["detail_candidates_deferred"] for row in rows)
    counts["detail_candidate_incomplete_sources"] = sum(
        row["detail_candidates_deferred"] > 0 for row in rows)
    counts["individual_bid_details_fetched"] = sum(row["individual_bid_details_fetched"] for row in rows)
    # Distinguish successfully opening a procurement landing page from
    # actually retrieving individual bid details. PDF checks are reported
    # separately; neither kind of retrieval verifies an open opportunity.
    counts["individual_detail_retrieval_sources"] = sum(
        row["individual_bid_details_fetched"] > 0 for row in rows)
    counts["fetched_without_individual_details_sources"] = sum(
        row["direct_state"] == "fetched_unverified"
        and row["individual_bid_details_fetched"] == 0 for row in rows)
    # A fetched landing page with incomplete pagination, request budgets,
    # or failed details cannot be described as complete listing coverage.
    counts["fetched_with_incomplete_extraction_sources"] = sum(
        row["direct_state"] == "fetched_unverified"
        and any(row[key] > 0 for key in (
            "pagination_errors", "detail_errors", "detail_budget_deferred",
            "detail_candidates_deferred", "pdf_budget_skips"))
        for row in rows)
    counts["detail_errors"] = sum(row["detail_errors"] for row in rows)
    counts["pagination_errors"] = sum(row["pagination_errors"] for row in rows)
    counts["pagination_incomplete_sources"] = sum(row["pagination_errors"] > 0 for row in rows)
    # The primary access state remains a single value for older dashboards.
    # Per-reason counts are intentionally non-exclusive: mixed failures in
    # one source must appear under every observed access restriction.
    for state in ("robots_blocked", "http_blocked", "redirect_blocked", "rate_limited"):
        counts["detail_" + state + "_sources"] = sum(
            state in row["detail_error_types"] for row in rows)
        counts["pagination_" + state + "_sources"] = sum(
            state in row["pagination_error_types"] for row in rows)
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
                    "Individual-detail robots blocks, HTTP refusals, redirects, rate limits "
                    "and other errors are reported separately, including mixed failure "
                    "types on the same source. "
                    "Listing pagination failures, deferred individual bid records, and "
                    "unfetched generic detail candidates mean extraction coverage may be incomplete. "
                    "Generic candidates are not verified individual solicitations. "
                    "External provider links require an approved adapter and are not followed. "
                    "Provider-access requirements persist even when a scan has no status. " 
                     "Configured access-required portals and unimplemented feed/API adapters "
                    "are not direct fetch targets. "
                    "HTTP refusals, unsafe redirects, rate limits and unsupported "
                    "content are distinguished from transient fetch errors. "
                    "Staged provider access gates are reported separately from "
                    "configured direct portals. Staged URLs are not monitored; "
                    "all leads remain unverified.")
    }
