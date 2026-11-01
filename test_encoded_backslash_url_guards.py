"""Offline URL safety regression; these synthetic URLs are not live bids."""
import unittest
from unittest.mock import patch

import audit_source_coverage
import civicplus_bids
import granicus_rfps
import probe_staged_sources
import scan
import source_config
import source_health


class EncodedBackslashUrlTests(unittest.TestCase):
    def test_public_source_and_notice_urls_reject_encoded_backslash(self):
        origin = "https://county.example/Bids.aspx"
        city = "https://city.example/government/departments/purchasing/bids-rfps"
        for escape in ("%5c", "%5C"):
            with self.subTest(escape=escape):
                bad = origin + "?bidID=7&note=" + escape + "admin"
                self.assertFalse(source_config.valid_public_https_url(bad))
                self.assertEqual(scan.safe_detail_url(origin, bad), "")
                self.assertEqual(civicplus_bids.individual_url(bad, origin), "")
                self.assertIsNone(probe_staged_sources._safe_link(origin, bad))
                # A fragment is stripped before navigating; still reject
                # malformed links rather than treating them as bid evidence.
                granicus_bad = (
                    "https://city.example/Home/Components/RFP/RFP/440/90#"
                    + escape + "admin"
                )
                self.assertEqual(granicus_rfps.individual_url(granicus_bad, city), "")

    def test_malformed_source_cannot_inflate_coverage_or_be_fetched(self):
        bad = "https://county.example/Bids.aspx?folder=tree%5cprivate"
        staged = {
            "name": "Staged fixture", "mode": "discovery_pending",
            "url": "", "verified_url": False,
            "candidate_official_url": bad,
        }
        direct = {
            "name": "Direct fixture", "mode": "direct_page",
            "url": bad, "verified_url": True,
        }
        coverage = audit_source_coverage.audit([staged, direct])
        self.assertEqual(coverage["official_urls_staged"], 0)
        self.assertEqual(coverage["direct_configured"], 0)
        self.assertEqual(coverage["invalid_direct_configurations"], 1)
        self.assertEqual(source_health.classify(staged, "")["direct_state"], "not_configured")
        with patch.object(scan, "scan_direct") as direct_fetch, patch.object(
            scan, "scan_news", return_value=[]
        ):
            _, status, leads = scan.run(direct)
        direct_fetch.assert_not_called()
        self.assertIn("direct not configured", status)
        self.assertEqual(leads, [])

    def test_ordinary_bid_urls_still_pass(self):
        origin = "https://county.example/Bids.aspx"
        valid = origin + "?bidID=7"
        self.assertTrue(source_config.valid_public_https_url(valid))
        self.assertEqual(scan.safe_detail_url(origin, valid), valid)
        self.assertTrue(civicplus_bids.individual_url(valid, origin))
        self.assertIsNotNone(probe_staged_sources._safe_link(origin, valid))
        city = "https://city.example/government/departments/purchasing/bids-rfps"
        notice = "https://city.example/Home/Components/RFP/RFP/440/90"
        self.assertEqual(granicus_rfps.individual_url(notice, city), notice)


if __name__ == "__main__":
    unittest.main()
