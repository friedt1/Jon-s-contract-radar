"""Summarize published scanner coverage without inventing opportunities.

Usage: python source_diagnostics.py [data/opportunities.json]
Optional: python source_diagnostics.py --strict [path]
"""
import argparse
import json
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
    by_name = {row["name"]: row for row in health.get("sources", [])
               if isinstance(row, dict) and isinstance(row.get("name"), str)}
    results = []
    for name, status in sorted(sources.items()):
        message = str(status)
        low = message.lower()
        import re
        def count(pattern):
            match = re.search(pattern, low)
            return int(match.group(1)) if match else None
        row = by_name.get(name, {})
        direct = row.get("direct_state", "unknown")
        indirect = row.get("indirect_state", "unknown")
        detail_errors = row.get("detail_errors", 0)
        # An indirect RSS robots error must not turn a successful direct
        # fetch into a direct-source failure.
        direct_error = direct in {"robots_blocked", "fetch_error"}
        indirect_error = indirect in {"robots_blocked", "error"}
        if not row:  # Backward-compatible fallback for historical feeds.
            direct_error = ("direct error:" in low or "direct blocked" in low
                            or low.startswith("blocked:"))
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
            "error": direct_error or bool(detail_errors),
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
        "sources": results,
        "warning": ("Direct fetch, indirect RSS, provider access and individual-detail "
                    "failures are separate. A fetched page or unverified candidate "
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
