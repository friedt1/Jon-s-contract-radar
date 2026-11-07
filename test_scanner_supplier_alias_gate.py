"""Fail closed when a delegated supplier platform is renamed with case/spacing."""
import unittest
from unittest.mock import patch

import scan


class ScannerSupplierAliasGateTests(unittest.TestCase):
    def test_aliases_never_fetch_direct_supplier_portal(self):
        for label in ("  pennbid   PLATFORM ", "BIDNET ny platform", " tompkins  county purchasing "):
            with self.subTest(label=label), patch.object(scan, "scan_direct") as direct:
                name, status, leads = scan.run({
                    "name": label,
                    "mode": "direct_page",
                    "verified_url": True,
                    "url": "https://procurement.example.org/bids",
                }, news_access=(False, "offline test"))
                direct.assert_not_called()
                self.assertIn("direct access required", status)
                self.assertEqual(leads, [])

    def test_unrestricted_direct_source_keeps_existing_path(self):
        with patch.object(scan, "scan_direct", return_value=([], "direct fetched")) as direct:
            _, status, leads = scan.run({
                "name": "Example County purchasing",
                "mode": "direct_page",
                "verified_url": True,
                "url": "https://procurement.example.org/bids",
            }, news_access=(False, "offline test"))
            direct.assert_called_once()
            self.assertIn("direct fetched", status)
            self.assertEqual(leads, [])


if __name__ == "__main__":
    unittest.main()
