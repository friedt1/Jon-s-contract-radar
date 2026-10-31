"""Summarize published scanner coverage without inventing opportunities.

Usage: python source_diagnostics.py [data/opportunities.json]
Optional: python source_diagnostics.py --strict [path]
"""
import argparse
import json
from collections import Counter
from pathlib import Path


def report(payload):
    sources = payload.get("source_status", {})
    leads = payload.get("opportunities", [])
    if not isinstance(sources, dict) or not isinstance(leads, list):
        raise ValueError("invalid published scan schema")
    health = payload.get("source_health", {})
    if health is None:
        health = {}
    if not isinstance(health, dict) or not isinstance(health.get("sources", []), list):
        raise ValueError("invalid source health schema")
    health_names = [row["name"] for row in health.get("sources", [])
                    if isinstance(row, dict) and isinstance(row.get("name"), str)]
    duplicate_health_names = sorted(
        name for name, count in Counter(health_names).items() if count > 1)
    by_name = {row["name"]: row for row in health.get("sources", [])
               if isinstance(row, dict) and isinstance(row.get("name"), str)}
    has_health = "source_health" in payload and payload["source_health"] is not None
    coverage = payload.get("source_coverage", {})
    expected = coverage.get("total_targets") if isinstance(coverage, dict) else None
    if isinstance(expected, bool) or not isinstance(expected, int) or expected < 0:
        expected = None
    # SAM.gov is separately deferred, not one of the 102 named targets.
    # A count-only comparison misses a source replaced by an unexpected name.
    observed_targets = (set(sources) | set(by_name)) - {"SAM.gov"}
    expected_names = coverage.get("expected_source_names") if isinstance(coverage, dict) else None
    if expected_names is not None:
        if (not isinstance(expected_names, list)
                or any(not isinstance(name, str) or not name.strip()
                       for name in expected_names)
                or len(set(expected_names)) != len(expected_names)
                or (expected is not None and len(expected_names) != expected)):
            raise ValueError("invalid expected source inventory")
        named_targets = set(expected_names)
        missing_inventory_sources = sorted(named_targets - observed_targets)
        unexpected_inventory_sources = sorted(observed_targets - named_targets)
        unaccounted_targets = len(missing_inventory_sources)
        health_inventory_shortfall = (len(named_targets - set(by_name))
                                      if has_health else 0)
    else:
        # Backward compatibility for historical count-only feeds.
        missing_inventory_sources = []
        unexpected_inventory_sources = []
        unaccounted_targets = (max(0, expected - len(observed_targets))
                               if has_health and expected is not None else 0)
        health_inventory_shortfall = (max(0, expected - len(by_name))
                                      if has_health and expected is not None else 0)
    results = []
    # A source present in health but missing from source_status must not
    # disappear from diagnostics. Conversely, missing health rows are a gap
    # when the feed claims to include structured health.
    for name in sorted(set(sources) | set(by_name)):
        status_missing = name not in sources
        message = str(sources.get(name, ""))
        low = message.lower()
        import re
        def count(pattern):
            match = re.search(pattern, low)
            return int(match.group(1)) if match else None
        row = by_name.get(name, {})
        direct = row.get("direct_state", "unknown")
        indirect = row.get("indirect_state", "unknown")
        detail_errors = row.get("detail_errors", 0)
        pagination_errors = row.get("pagination_errors", 0)
        detail_budget_deferred = row.get(
            "detail_budget_deferred",
            count(r"(\d+) individual bid records deferred at detail budget") or 0)
        detail_candidates_deferred = row.get(
            "detail_candidates_deferred",
            count(r"(\d+) detail candidates deferred at request budget") or 0)
        pdf_budget_skips = row.get("pdf_budget_skips", 0)
        # SAM.gov is intentionally deferred and excluded from the 102-source
        # structured health report; it is not a missing health record.
        health_missing = (has_health and name not in by_name
                          and not (name == "SAM.gov" and message == "deferred"))
        duplicate_health_row = name in duplicate_health_names
        coverage_incomplete = bool(
            detail_errors or pagination_errors or detail_budget_deferred
            or detail_candidates_deferred or pdf_budget_skips)
        # An indirect RSS robots error must not turn a successful direct
        # fetch into a direct-source failure.
        # HTTP denials, unsafe redirects, rate limits, and unsupported
        # responses are direct-source failures too. Keep access-required
        # portals separate: missing authorization is not a transient error.
        direct_error = direct in {
            "robots_blocked", "http_blocked", "redirect_blocked",
            "rate_limited", "unsupported_content", "fetch_error",
        }
        indirect_error = indirect in {"robots_blocked", "error"}
        if not row:  # Backward-compatible fallback for historical feeds.
            direct_error = ("direct error:" in low or "direct blocked" in low
                            or low.startswith("blocked:")
                            or "unsupported content type" in low)
            indirect_error = "indirect rss error:" in low
        results.append({
            "source": name,
            "listing_pages": count(r"(\d+) listing pages"),
            "individual_records": row.get("individual_bid_records_found",
                                          count(r"(\d+) individual bid records")),
            "details_checked": row.get("detail_fetches_attempted",
                                       count(r"(\d+) (?:relevant )?details checked")),
            "candidates": row.get("unverified_candidates",
                                  count(r"(\d+) (?:unverified )?candidates")),
            "direct_state": direct,
            "indirect_state": indirect,
            "detail_access_state": row.get("detail_access_state", "unknown"),
            "access_required": direct == "access_required" or
                               (not row and "access required" in low),
            "direct_error": direct_error,
            "indirect_error": indirect_error,
            "detail_errors": detail_errors,
            "pagination_errors": pagination_errors,
            "detail_budget_deferred": detail_budget_deferred,
            "detail_candidates_deferred": detail_candidates_deferred,
            "coverage_incomplete": coverage_incomplete,
            "status_missing": status_missing,
            "health_missing": health_missing,
            "duplicate_health_row": duplicate_health_row,
            "unexpected_inventory_source": name in unexpected_inventory_sources,
            "pagination_access_state": row.get("pagination_access_state", "unknown"),
            "pdf_fetch_attempts": row.get("pdf_fetch_attempts", 0),
            "pdf_budget_skips": pdf_budget_skips,
            "result_award_links_excluded": row.get("result_award_links_excluded", 0),
            "external_provider_links_skipped": row.get("external_provider_links_skipped", 0),
            "error": (direct_error or bool(detail_errors) or bool(pagination_errors)
                      or status_missing or health_missing or duplicate_health_row
                      or name in unexpected_inventory_sources),
            "raw_status": message,
        })
    return {
        "updated": payload.get("updated"),
        "published_opportunities": len(leads),
        "verified_open_opportunities": sum(
            1 for x in leads if isinstance(x, dict) and
            x.get("status") == "verified" and x.get("open_status") == "verified_open"
        ),
        "source_coverage": payload.get("source_coverage", {}),
        "health_counts": health.get("counts", {}),
        "detail_budget_deferred": sum(row["detail_budget_deferred"] for row in results),
        "detail_candidates_deferred": sum(row["detail_candidates_deferred"] for row in results),
        "incomplete_detail_sources": sum(row["coverage_incomplete"] for row in results),
        "diagnostic_gaps": (sum(
            row["status_missing"] or row["health_missing"] for row in results)
            + unaccounted_targets + len(duplicate_health_names)
            + len(unexpected_inventory_sources)),
        "unaccounted_targets": unaccounted_targets,
        "missing_inventory_sources": missing_inventory_sources,
        "unexpected_inventory_sources": unexpected_inventory_sources,
        "health_inventory_shortfall": health_inventory_shortfall,
        "duplicate_health_rows": duplicate_health_names,
        "sources": results,
        "warning": ("Direct fetch, indirect RSS, provider access and individual-detail "
                    "failures, including incomplete listing pagination and deferred "
                    "detail requests, are separate. Missing per-source diagnostics "
                    "are reported rather than silently dropped; inventory-size "
                    "shortfalls, missing/unexpected named targets and duplicate "
                    "health records are also flagged. "
                    "A fetched page or unverified candidate "
                    "is not a verified open contract.")
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", default="data/opportunities.json")
    parser.add_argument("--strict", action="store_true",
                        help="exit nonzero when there are no verified open opportunities")
    args = parser.parse_args()
    data = report(json.loads(Path(args.path).read_text(encoding="utf-8")))
    print(json.dumps(data, indent=2))
    return 1 if args.strict and not data["verified_open_opportunities"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
