"""Summarize published scanner coverage without inventing opportunities.

Usage: python source_diagnostics.py [data/opportunities.json]
Optional: python source_diagnostics.py --strict [path]
"""
import argparse
import json
from pathlib import Path


def report(payload):
    sources = payload.get("source_status") or {}
    leads = payload.get("opportunities") or []
    if not isinstance(sources, dict) or not isinstance(leads, list):
        raise ValueError("invalid published scan schema")
    results = []
    for name, status in sorted(sources.items()):
        message = str(status)
        low = message.lower()
        import re
        def count(pattern):
            match = re.search(pattern, low)
            return int(match.group(1)) if match else None
        results.append({
            "source": name,
            "listing_pages": count(r"(\d+) listing pages"),
            "individual_records": count(r"(\d+) individual bid records"),
            "details_checked": count(r"(\d+) (?:relevant )?details checked"),
            "candidates": count(r"(\d+) (?:unverified )?candidates"),
            "error": ("error" in low or "failed" in low or "blocked" in low),
            "raw_status": message,
        })
    return {
        "updated": payload.get("updated"),
        "published_opportunities": len(leads),
        "verified_open_opportunities": sum(
            1 for x in leads if isinstance(x, dict) and
            x.get("status") == "verified" and x.get("open_status") == "verified_open"
        ),
        "sources": results,
        "warning": "A successful fetch or unverified candidate is not a verified open contract."
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
