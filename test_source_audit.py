"""Coverage accounting tests; all URLs and bids in fixtures are synthetic."""
import json
from pathlib import Path
import unittest

from audit_source_coverage import audit as canonical_audit
from source_audit import audit


class SourceAuditTests(unittest.TestCase):
    def test_distinct_hosts_pending_and_unconnected_platforms(self):
        rows = [
            {"name": "PennBid platform", "type": "platform", "mode": "direct_page",
             "url": "https://pennbid.bonfirehub.com", "verified_url": True},
            {"name": "Another PennBid path", "mode": "direct_page",
             "url": "https://pennbid.bonfirehub.com/portal", "verified_url": True},
            {"name": "County", "mode": "discovery_pending", "url": ""},
        ]
        result = audit(rows)
        self.assertEqual(result["total_targets"], 3)
        self.assertEqual(result["direct_page_targets"], 2)
        self.assertEqual(result["unique_direct_page_hosts"], 1)
        self.assertEqual(result["pending_discovery_targets"], 1)
        self.assertEqual(result["configured_provider_access_required"], 1)
        self.assertEqual(result["direct_fetch_targets"], 1)
        self.assertIn("PennBid platform", result["platforms_configured_not_proven_ingested"])

    def test_unsafe_and_unverified_urls_are_not_direct(self):
        rows = [
            {"name": "Unsafe", "mode": "direct_page",
             "url": "https://user:secret@county.example/bids", "verified_url": True},
            {"name": "HTTP", "mode": "direct_page",
             "url": "http://county.example/bids", "verified_url": True},
            {"name": "Unverified", "mode": "direct_page",
             "url": "https://county.example/bids", "verified_url": False},
            {"name": "Staged", "mode": "discovery_pending", "url": "",
             "candidate_official_url": "https://county.example/notice"},
        ]
        result = audit(rows)
        self.assertEqual(result["direct_page_targets"], 0)
        self.assertEqual(result["unique_direct_page_hosts"], 0)
        self.assertEqual(result["pending_discovery_targets"], 4)
        self.assertEqual(result["invalid_direct_configurations"], 3)
        self.assertEqual(result["staged_official_urls"], 1)

    def test_actual_inventory_agrees_with_canonical_coverage_audit(self):
        rows = json.loads((Path(__file__).parent / "sources.json").read_text())
        result, canonical = audit(rows), canonical_audit(rows)
        self.assertEqual(result["total_targets"], 102)
        self.assertEqual(result["direct_configured"], canonical["direct_configured"])
        self.assertEqual(result["direct_fetch_targets"], canonical["direct_fetch_targets"])
        self.assertEqual(result["configured_provider_access_required"],
                         canonical["configured_provider_access_required"])
        self.assertEqual(result["staged_official_urls"], canonical["official_urls_staged"])
        self.assertEqual(result["pending_discovery_targets"],
                         canonical["not_directly_monitored"])
        self.assertEqual(result["discovery_required"], canonical["discovery_required"])


if __name__ == "__main__":
    unittest.main()
