"""Audit configured procurement sources without claiming portals are live integrations."""
import json
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent

def audit(sources):
    configured = [s for s in sources if s.get("url") and s.get("mode") == "direct_page"]
    pending = [s for s in sources if not s.get("url") or s.get("mode") == "discovery_pending"]
    hosts = sorted({urlparse(s["url"]).hostname for s in configured if urlparse(s["url"]).hostname})
    platforms = [s["name"] for s in configured if s.get("type") == "platform"]
    return {
        "total_targets": len(sources),
        "direct_page_targets": len(configured),
        "unique_direct_page_hosts": len(hosts),
        "hosts": hosts,
        "pending_discovery_targets": len(pending),
        "platforms_configured_not_proven_ingested": platforms,
        "modes": dict(Counter(s.get("mode", "unknown") for s in sources)),
        "warning": "A configured source is not proof of a successful fetch or an actionable bid. Platform pages may require JavaScript or authentication."
    }

if __name__ == "__main__":
    print(json.dumps(audit(json.loads((ROOT / "sources.json").read_text())), indent=2))
