"""Synthetic shared-gateway accounting; never creates or publishes live bids."""
import datetime as dt
import json
from pathlib import Path
import unittest

import audit_source_coverage
import scan
import source_audit


class SharedOfficialEntrypointTests(unittest.TestCase):
    def test_duplicate_official_gateway_does_not_inflate_unique_endpoints(self):
        shared = "https://county.example/Bids.aspx?agency=county&category=roads"
        rows = [
            {"name": "County procurement", "mode": "direct_page",
             "url": shared, "verified_url": True},
            {"name": "Airport procurement", "mode": "discovery_pending",
             "url": "", "verified_url": False,
             "candidate_official_url":
                 "https://COUNTY.example:443/Bids.aspx?agency=county&category=roads"},
            {"name": "City procurement", "mode": "discovery_pending",
             "url": "", "verified_url": False, "candidate_official_url": shared},
            {"name": "Unrelated agency", "mode": "discovery_pending",
             "url": "", "verified_url": False,
             "candidate_official_url": "https://district.example/procurement"},
            {"name": "Unverified direct", "mode": "direct_page",
             "url": shared, "verified_url": False},
        ]
        coverage = audit_source_coverage.audit(rows)
        self.assertEqual(coverage["total"], 5)
        self.assertEqual(coverage["direct_configured"], 1)
        self.assertEqual(coverage["direct_fetch_targets"], 1)
        self.assertEqual(coverage["official_urls_staged"], 3)
        self.assertEqual(coverage["not_directly_monitored"], 4)
        self.assertEqual(coverage["distinct_official_entrypoints"], 2)
        self.assertEqual(coverage["shared_official_entrypoint_targets"], 3)
        self.assertEqual(coverage["shared_official_entrypoint_groups"], {
            shared: ["Airport procurement", "City procurement", "County procurement"]
        })
        by_name = {row["source"]: row for row in coverage["sources"]}
        for name in ("County procurement", "Airport procurement", "City procurement"):
            self.assertTrue(by_name[name]["shared_official_entrypoint"])
        self.assertFalse(by_name["Unrelated agency"]["shared_official_entrypoint"])
        self.assertFalse(by_name["Unverified direct"]["shared_official_entrypoint"])
        legacy = source_audit.audit(rows)
        self.assertEqual(legacy["shared_official_entrypoint_groups"],
                         coverage["shared_official_entrypoint_groups"])
        self.assertEqual(legacy["distinct_official_entrypoints"], 2)

    def test_duplicate_named_rows_are_not_counted_as_independent_publishers(self):
        # Synthetic entries only; repeated rows cannot create a second agency.
        url = "https://county.example/Bids.aspx"
        rows = [
            {"name": "County procurement", "mode": "direct_page",
             "url": url, "verified_url": True},
            {"name": "County procurement", "mode": "direct_page",
             "url": url, "verified_url": True},
        ]
        result = audit_source_coverage.audit(rows)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["unique_named_targets"], 1)
        self.assertEqual(result["duplicate_source_names"], ["County procurement"])
        self.assertEqual(result["duplicate_source_rows"], 1)
        self.assertFalse(result["inventory_integrity_ok"])
        self.assertEqual(result["distinct_official_entrypoints"], 1)
        self.assertEqual(result["shared_official_entrypoint_groups"], {})
        self.assertEqual(result["shared_official_entrypoint_targets"], 0)
        self.assertTrue(all(row["duplicate_source_name"] for row in result["sources"]))
        legacy = source_audit.audit(rows)
        self.assertEqual(legacy["unique_named_targets"], 1)
        self.assertFalse(legacy["inventory_integrity_ok"])

    def test_real_shared_gateway_counts_distinct_agencies_only(self):
        url = "https://county.example/Bids.aspx"
        rows = [
            {"name": "County", "mode": "direct_page", "url": url,
             "verified_url": True},
            {"name": "County", "mode": "direct_page", "url": url,
             "verified_url": True},
            {"name": "Airport", "mode": "discovery_pending",
             "candidate_official_url": url},
        ]
        result = audit_source_coverage.audit(rows)
        self.assertEqual(result["shared_official_entrypoint_groups"],
                         {url: ["Airport", "County"]})
        self.assertEqual(result["shared_official_entrypoint_targets"], 2)
        self.assertEqual(result["duplicate_source_rows"], 1)

    def test_current_inventory_and_historical_negative_cases_unchanged(self):
        sources = json.loads((Path(__file__).parent / "sources.json").read_text())
        coverage = audit_source_coverage.audit(sources)
        self.assertEqual(coverage["total"], 102)
        self.assertEqual(coverage["unique_named_targets"], 102)
        self.assertEqual(coverage["duplicate_source_names"], [])
        self.assertTrue(coverage["inventory_integrity_ok"])
        self.assertEqual(coverage["direct_configured"], 18)
        self.assertEqual(coverage["official_urls_staged"], 84)
        self.assertEqual(coverage["not_directly_monitored"], 84)
        self.assertLess(coverage["distinct_official_entrypoints"],
                        coverage["direct_configured"] + coverage["official_urls_staged"])
        today = dt.date(2026, 11, 1)
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            "PennBid platform", today=today))
        self.assertFalse(scan.eligible(
            "Owego demolition and site restoration bid due November 13, 2026",
            "Tioga County NY", today=today))


if __name__ == "__main__":
    unittest.main()
