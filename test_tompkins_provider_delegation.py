"""Tompkins County provider delegation regressions; no live bids are seeded."""
import contextlib
import datetime as dt
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import audit_source_coverage
import scan
import source_health


class TompkinsProviderDelegationTests(unittest.TestCase):
    @staticmethod
    def tompkins():
        sources = json.loads(scan.SOURCES.read_text(encoding="utf-8"))
        assert len(sources) == 102
        return next(s for s in sources if s["name"] == "Tompkins County purchasing")

    def test_official_county_gateway_is_access_required_not_an_individual_feed(self):
        source = self.tompkins()
        self.assertEqual(source["delegated_provider"], "BidNet Direct")
        self.assertIn("authorized individual-listing", source["activation_gate"])
        self.assertIn(source["name"], scan.UNCONNECTED_PLATFORMS)
        with patch.object(scan, "scan_direct", side_effect=AssertionError(
            "Provider-delegated archive must not be crawled"
        )) as direct, patch.object(scan, "scan_news", return_value=[]):
            name, status, leads = scan.run(source)
        direct.assert_not_called()
        self.assertEqual(name, source["name"])
        self.assertEqual(leads, [])
        self.assertIn("direct access required:", status)
        self.assertNotIn("direct fetched;", status)
        row = source_health.classify(source, status)
        self.assertEqual(row["direct_state"], "access_required")
        self.assertEqual(row["individual_bid_details_fetched"], 0)
        audit = audit_source_coverage.audit([source])
        self.assertEqual(audit["direct_configured"], 1)
        self.assertEqual(audit["direct_fetch_targets"], 0)
        self.assertEqual(audit["configured_provider_access_required"], 1)

    def test_strict_audit_fails_when_every_url_is_configured_but_access_blocked(self):
        source = self.tompkins()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sources.json"
            path.write_text(json.dumps([source]), encoding="utf-8")
            with patch("sys.argv", ["audit_source_coverage.py", "--strict",
                                    "--sources", str(path)]), contextlib.redirect_stdout(io.StringIO()):
                result = audit_source_coverage.main()
        self.assertEqual(result, 1)

    def test_erie_expired_and_owego_demolition_never_become_live_tree_bids(self):
        today = dt.date(2026, 10, 30)
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid submission deadline October 28, 2026",
            today=today))
        self.assertFalse(scan.eligible(
            "Owego demolition and site restoration bid due November 13, 2026",
            today=today))


if __name__ == "__main__":
    unittest.main()
