"""Offline regressions for verified official vendor entrypoints, not live bids."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from audit_source_coverage import audit
from source_config import direct_fetch_target
from source_health import summarize
import probe_staged_sources
import scan


OFFICIAL = {
    "Arnot Realty": "https://www.arnotrealty.com/property-asset-management",
    "Corning Natural Gas": "https://www.corninggas.com/",
    "Dandy Mini Marts": "https://www.godandy.com/contact-us/",
    "Brixmor Property Group": "https://www.brixmor.com/contact",
    "CBRE regional property management":
        "https://www.cbre.com/about-us/supply-chain/suppliers-supply-chain-technologies-and-registration",
    "JLL regional property management": "https://www.jll.com/en-us/vendors",
}


class VendorEntryPointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads((Path(__file__).parent / "sources.json").read_text())
        cls.by_name = {s["name"]: s for s in cls.sources}

    def test_official_pages_are_only_staged_and_require_access(self):
        self.assertEqual(len(cls_sources := self.sources), 102)
        self.assertEqual(len({s["name"] for s in cls_sources}), 102)
        for name, url in OFFICIAL.items():
            with self.subTest(name=name):
                source = self.by_name[name]
                self.assertEqual(source["candidate_official_url"], url)
                self.assertEqual(source["mode"], "discovery_pending")
                self.assertEqual(source["url"], "")
                self.assertIs(source["verified_url"], False)
                self.assertIs(source["provider_access_required"], True)
                self.assertTrue(source["require_local_evidence"])
                self.assertIn("NOT", source["official_page_role"])
                self.assertTrue(source["activation_gate"])
                self.assertFalse(direct_fetch_target(source))

    def test_vendor_gateways_never_become_scan_direct_targets(self):
        for name in OFFICIAL:
            with self.subTest(name=name):
                source = self.by_name[name]
                with (patch.object(scan, "scan_direct",
                                   side_effect=AssertionError("not a public bid feed")) as direct,
                      patch.object(scan, "scan_news", return_value=[])):
                    _, _, leads = scan.run(source)
                direct.assert_not_called()
                self.assertEqual(leads, [])

    def test_coverage_reports_staged_urls_not_live_contracts(self):
        result = audit(self.sources)
        self.assertEqual(result["total"], 102)
        self.assertEqual(result["direct_configured"], 18)
        self.assertEqual(result["not_directly_monitored"], 84)
        self.assertEqual(result["official_urls_staged"], 84)
        self.assertEqual(result["discovery_required"], 0)
        by_name = {row["source"]: row for row in result["sources"]}
        for name in OFFICIAL:
            self.assertTrue(by_name[name]["official_url_staged"])
            self.assertTrue(by_name[name]["staged_provider_access_required"])
            self.assertFalse(by_name[name]["direct_fetch_target"])
        health = summarize([self.by_name[name] for name in OFFICIAL], {})
        self.assertEqual(health["counts"]["configured_direct"], 0)
        self.assertEqual(health["counts"]["staged_provider_access_required"], 6)
        self.assertEqual(health["counts"]["individual_bid_details_fetched"], 0)

    def test_official_contact_pages_do_not_create_notices(self):
        for name in OFFICIAL:
            with self.subTest(name=name):
                source = self.by_name[name]
                result = probe_staged_sources.probe(
                    source,
                    fetch=lambda url, binary=False: (
                        "<h1>Contact our purchasing team</h1><p>Supplier registration</p>",
                        "text/html", url),
                )
                self.assertEqual(result["state"], "official_supplier_or_contact_gateway_access_required")
                self.assertFalse(result["individual_notice_retrieved"])
                self.assertFalse(result["direct_monitoring_activated"])
                self.assertNotIn("opportunities", result)


if __name__ == "__main__":
    unittest.main()
