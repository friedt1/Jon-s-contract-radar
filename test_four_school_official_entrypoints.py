"""Verified school publisher entrypoints are not individual-bid monitoring.

All notices here are synthetic or expired regression strings, not live leads.
"""
import datetime as dt
import json
from pathlib import Path
import unittest

from audit_source_coverage import audit
from source_config import direct_fetch_target
from source_health import summarize
import scan


OFFICIAL = {
    "Waverly Central School District": "https://www.waverlyschools.com/",
    "Ithaca College": "https://www.ithaca.edu/procurement/information-suppliers",
    "Northern Tier Career Center": "https://www.ntccschool.org/",
    "Wellsboro Area School District": "https://www.wellsborosd.org/page/business-office",
}


class SchoolEntrypointStagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = json.loads((Path(__file__).parent / "sources.json").read_text())
        cls.by_name = {source["name"]: source for source in cls.sources}

    def test_official_entrypoints_are_staged_not_scanned(self):
        for name, url in OFFICIAL.items():
            with self.subTest(name=name):
                source = self.by_name[name]
                self.assertEqual(source["candidate_official_url"], url)
                self.assertEqual(source["mode"], "discovery_pending")
                self.assertEqual(source["url"], "")
                self.assertIs(source["verified_url"], False)
                self.assertFalse(direct_fetch_target(source))
                self.assertTrue(source["activation_gate"])
                self.assertIn(source["official_page_role"],
                              ("publisher_entrypoint_only", "supplier_information_only",
                               "procurement_contact_only"))

    def test_new_staging_has_unambiguous_utc_timestamp(self):
        # A date-only value cannot prove that an entry was staged after an
        # earlier scan on the same calendar day. The published feed must
        # remain valid until the next successful scanner refresh.
        for name in OFFICIAL:
            with self.subTest(name=name):
                checked = dt.datetime.fromisoformat(
                    self.by_name[name]["official_url_checked_at"])
                self.assertIsNotNone(checked.tzinfo)
                self.assertIsNotNone(checked.utcoffset())

    def test_private_supplier_bids_require_permission(self):
        ithaca = self.by_name["Ithaca College"]
        self.assertIs(ithaca["provider_access_required"], True)
        rows = summarize([self.by_name[name] for name in OFFICIAL], {})
        self.assertEqual(rows["counts"]["configured_direct"], 0)
        self.assertEqual(rows["counts"]["configured_fetch_targets"], 0)
        self.assertEqual(rows["counts"]["staged_official_url"], 4)
        self.assertEqual(rows["counts"]["staged_provider_access_required"], 1)
        self.assertEqual(rows["counts"]["individual_bid_details_fetched"], 0)

    def test_full_coverage_audit_remains_honest(self):
        result = audit(self.sources)
        self.assertEqual(result["total"], 102)
        self.assertEqual(result["direct_configured"], 18)
        self.assertEqual(result["not_directly_monitored"], 84)
        self.assertEqual(result["official_urls_staged"], 73)
        self.assertEqual(result["discovery_required"], 11)
        rows = {row["source"]: row for row in result["sources"]}
        for name in OFFICIAL:
            self.assertTrue(rows[name]["official_url_staged"])
            self.assertFalse(rows[name]["direct_fetch_target"])
        self.assertTrue(rows["Ithaca College"]["staged_provider_access_required"])

    def test_historical_unrelated_or_expired_notices_never_become_live(self):
        today = dt.date(2026, 11, 1)
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            "PennBid platform", today=today))
        self.assertFalse(scan.eligible(
            "Owego demolition and site restoration bid due November 13, 2026",
            "Tioga County NY", today=today))
        self.assertFalse(scan.eligible(
            "Wellsboro technology infrastructure analysis bid due April 14, 2025",
            "Wellsboro Area School District", today=today))


if __name__ == "__main__":
    unittest.main()
