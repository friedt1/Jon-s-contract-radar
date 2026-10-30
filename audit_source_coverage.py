"""Audit configured source monitoring: indirect news is not direct bid monitoring.

Run: python audit_source_coverage.py
Use --strict to fail until every target has an authorized direct listing method.
"""
import argparse
import json
from pathlib import Path

from scan import UNCONNECTED_PLATFORMS
from source_config import DIRECT_MODES, direct_configured, valid_public_https_url


def audit(sources):
    results = []
    for source in sources:
        mode = source.get("mode", "missing")
        url = source.get("url", "")
        direct = direct_configured(source)
        access_required = direct and source["name"] in UNCONNECTED_PLATFORMS
        staged = (not direct and mode == "discovery_pending"
                  and valid_public_https_url(source.get("candidate_official_url")))
        invalid_direct = mode in DIRECT_MODES and not direct
        results.append({
            "source": source["name"],
            "mode": mode,
            "direct_configured": direct,
            "direct_fetch_target": direct and not access_required,
            "provider_access_required": access_required,
            "official_url_staged": staged,
            "invalid_direct_configuration": invalid_direct,
            "candidate_official_url": source.get("candidate_official_url") if staged else None,
            "activation_gate": source.get("activation_gate", "") if staged else "",
            "target_url": url if direct else None,
            "status": ("configured URL only; provider-approved individual-listing ingestion not connected"
                       if access_required else
                       "configured; live ingestion not independently verified" if direct else
                       "official URL staged; individual-notice extraction and permissions not verified" if staged else
                       "invalid direct configuration; verified HTTPS URL required" if invalid_direct else
                       "not directly monitored; official source discovery required"),
        })
    return {
        "total": len(results),
        "direct_configured": sum(x["direct_configured"] for x in results),
        "direct_fetch_targets": sum(x["direct_fetch_target"] for x in results),
        "configured_provider_access_required": sum(x["provider_access_required"] for x in results),
        "not_directly_monitored": sum(not x["direct_configured"] for x in results),
        "official_urls_staged": sum(x["official_url_staged"] for x in results),
        "invalid_direct_configurations": sum(x["invalid_direct_configuration"] for x in results),
        "discovery_required": sum(not x["direct_configured"] and not x["official_url_staged"]
                                  and not x["invalid_direct_configuration"] for x in results),
        "sources": results,
        "warning": ("Direct configuration is not operational monitoring. Provider landing URLs "
                    "without approved individual-listing ingestion are access-required, not fetch targets. "
                    "Even other fetch targets do not prove permitted or successful bid extraction. "
                    "Malformed, insecure, or unverified URLs do not count as direct "
                    "configuration; staged URLs are not active monitoring.")
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--sources", default="sources.json")
    args = parser.parse_args()
    results = audit(json.loads(Path(args.sources).read_text(encoding="utf-8")))
    print(json.dumps(results, indent=2))
    return 1 if args.strict and (results["not_directly_monitored"] or
                                 results["configured_provider_access_required"]) else 0


if __name__ == "__main__":
    raise SystemExit(main())
