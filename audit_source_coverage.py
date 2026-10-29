"""Audit configured source monitoring: indirect news is not direct bid monitoring.

Run: python audit_source_coverage.py
Use --strict to fail until every target has an authorized direct listing method.
"""
import argparse
import json
from pathlib import Path

DIRECT_MODES = {"direct_page", "official_feed", "authorized_api"}


def audit(sources):
    results = []
    for source in sources:
        mode = source.get("mode", "missing")
        url = source.get("url", "")
        direct = mode in DIRECT_MODES and bool(url) and source.get("verified_url") is True
        results.append({
            "source": source["name"],
            "mode": mode,
            "direct_configured": direct,
            "target_url": url if direct else None,
            "status": "configured; live ingestion not independently verified" if direct else
                      "not directly monitored; requires official source discovery or access",
        })
    return {
        "total": len(results),
        "direct_configured": sum(x["direct_configured"] for x in results),
        "not_directly_monitored": sum(not x["direct_configured"] for x in results),
        "sources": results,
        "warning": "Direct configuration does not prove that individual bids are extracted or that automation is permitted."
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--sources", default="sources.json")
    args = parser.parse_args()
    results = audit(json.loads(Path(args.sources).read_text(encoding="utf-8")))
    print(json.dumps(results, indent=2))
    return 1 if args.strict and results["not_directly_monitored"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
