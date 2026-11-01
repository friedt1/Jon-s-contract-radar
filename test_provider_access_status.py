import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import scan

class ProviderStatusTests(unittest.TestCase):
    def test_unconnected_platforms_are_not_reported_as_live(self):
        for name in ("BidNet NY platform", "PennBid platform"):
            src = {"name": name, "url": "https://example.org", "mode": "direct_page"}
            with patch.object(scan, "scan_direct", return_value=([], "direct fetched; 0 candidates")), patch.object(scan, "scan_news", return_value=[]):
                _, status, leads = scan.run(src)
            self.assertEqual(leads, [])
            self.assertIn("individual listing ingestion not connected", status)

    def test_feed_reports_nyscr_access_blocker(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data").mkdir()
            with patch.object(scan, "ROOT", root), patch.object(scan, "OUT", root / "data/opportunities.json"), patch.object(scan, "run", side_effect=lambda s, news_access=None: (s["name"], "indirect RSS ok; 0 candidates", [])), patch.object(scan.robots_policy, "allowed", return_value=(True, "synthetic policy")):
                scan.main()
            result = json.loads((root / "data/opportunities.json").read_text())
            self.assertIn("NYS Contract Reporter", result["integration_status"])
            self.assertIn("blocked", result["integration_status"]["NYS Contract Reporter"])
            self.assertIn("not connected", result["integration_status"]["BidNet Direct"])

if __name__ == "__main__":
    unittest.main()
