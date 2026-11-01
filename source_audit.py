"""Legacy CLI coverage report, reconciled with the canonical configuration audit.

A public homepage, staged URL, or unconnected procurement provider is not
an operational individual-bid integration. Never count unverified/unsafe URLs.
"""
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

from audit_source_coverage import audit as coverage_audit
from source_config import direct_configured

ROOT = Path(__file__).resolve().parent


def audit(sources):
    coverage = coverage_audit(sources)
    configured = [s for s in sources if direct_configured(s)]
    direct_pages = [s for s in configured if s.get("mode") == "direct_page"]
    hosts = sorted({urlsplit(s["url"]).hostname for s in direct_pages})
    platforms = [s["name"] for s in configured if s.get("type") == "platform"]
    return {
        "total_targets": coverage["total"],
        "unique_named_targets": coverage["unique_named_targets"],
        "duplicate_source_names": coverage["duplicate_source_names"],
        "duplicate_source_rows": coverage["duplicate_source_rows"],
        "inventory_integrity_ok": coverage["inventory_integrity_ok"],
        "direct_page_targets": len(direct_pages),
        "direct_configured": coverage["direct_configured"],
        "direct_fetch_targets": coverage["direct_fetch_targets"],
        "configured_provider_access_required": coverage["configured_provider_access_required"],
        "staged_provider_access_required": coverage["staged_provider_access_required"],
        "unique_direct_page_hosts": len(hosts),
        "hosts": hosts,
        # This legacy field means *not configured for direct retrieval*, and
        # includes staged official URLs; it does not mean every URL is unknown.
        "pending_discovery_targets": coverage["not_directly_monitored"],
        "staged_official_urls": coverage["official_urls_staged"],
        "distinct_official_entrypoints": coverage["distinct_official_entrypoints"],
        "shared_official_entrypoint_groups": coverage["shared_official_entrypoint_groups"],
        "shared_official_entrypoint_targets": coverage["shared_official_entrypoint_targets"],
        "discovery_required": coverage["discovery_required"],
        "invalid_direct_configurations": coverage["invalid_direct_configurations"],
        "platforms_configured_not_proven_ingested": platforms,
        "modes": dict(Counter(s.get("mode", "unknown") for s in sources)),
        "warning": (
            "Only verified, safe HTTPS configurations count as direct targets. "
            "Staged URLs are not live monitoring; provider access-required "
            "configurations are not fetch targets. Even a successful listing "
            "fetch does not prove permitted individual-bid extraction or an open contract. "
            "Staged supplier-registration gateways remain access-required, not live feeds. "
            "Shared publisher gateways are not independent feeds. "
            "Duplicate source names are not additional named targets."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(audit(json.loads((ROOT / "sources.json").read_text())), indent=2))
