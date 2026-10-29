"""Official CivicPlus source wiring; synthetic notices are not live bids."""
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import civicplus_bids
import scan


EXPECTED = {
    "Town of Horseheads": "https://www.townofhorseheads.gov/Bids.aspx",
    "City of Ithaca": "https://www.cityofithacany.gov/Bids.aspx",
}


class OfficialCivicPlusSourceTests(unittest.TestCase):
    def test_official_listing_urls_are_configured(self):
        sources = json.loads((Path(__file__).parent / "sources.json").read_text())
        self.assertEqual(len(sources), 102)
        for name, url in EXPECTED.items():
            with self.subTest(name=name):
                src = next(x for x in sources if x["name"] == name)
                self.assertEqual(src["url"], url)
                self.assertEqual(src["mode"], "direct_page")
                self.assertTrue(src["verified_url"])
                self.assertIn(name, civicplus_bids.SOURCES)

    def test_individual_bid_required_and_closed_not_published(self):
        with patch.object(scan, "NOW", scan.dt.datetime(2026, 10, 28, 19, tzinfo=scan.dt.timezone.utc)):
            for name, url in EXPECTED.items():
                with self.subTest(name=name):
                    html = (
                        '<article><a href="/Bids.aspx?bidID=101">Tree trimming bid</a>'
                        '<p>Status:</p><p>Closes:</p><p>Open</p><p>11/19/2026 1:45 PM</p></article>'
                        '<article><a href="/Bids.aspx?bidID=102">Tree removal bid</a>'
                        '<p>Status:</p><p>Closes:</p><p>Closed</p><p>11/20/2026</p></article>'
                    )
                    def fake_fetch(target, binary=False):
                        if binary:
                            body = ('<p>Status: Open</p><p>Description: Tree trimming of '
                                    'roadside limbs.</p><p>Closing Date/Time: 11/19/2026 1:45 PM</p>')
                            return body.encode(), "text/html", target
                        return html, "text/html", target
                    with patch.object(scan, "fetch", side_effect=fake_fetch):
                        leads, status = scan.scan_direct({"name": name, "url": url, "mode": "direct_page"})
                    self.assertEqual(len(leads), 1)
                    self.assertEqual(leads[0]["url"], url + "?bidID=101")
                    self.assertEqual(leads[0]["status"], "unverified")
                    self.assertFalse(leads[0]["travel_verified"])
                    self.assertIn("1 closed", status)

    def test_unreadable_detail_does_not_generate_lead(self):
        for name, url in EXPECTED.items():
            with self.subTest(name=name):
                html = ('<article><a href="/Bids.aspx?bidID=201">Tree removal bid</a>'
                        '<p>Status: Open</p><p>Closes: 11/19/2026</p></article>')
                def fake_fetch(target, binary=False):
                    if binary:
                        raise OSError("test failure")
                    return html, "text/html", target
                with patch.object(scan, "fetch", side_effect=fake_fetch):
                    leads, status = scan.scan_direct({"name": name, "url": url, "mode": "direct_page"})
                self.assertEqual(leads, [])
                self.assertIn("detail errors", status)


if __name__ == "__main__":
    unittest.main()
