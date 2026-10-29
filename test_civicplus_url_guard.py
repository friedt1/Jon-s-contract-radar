"""CivicPlus malformed-link regression tests (synthetic HTML only)."""
import unittest

import civicplus_bids
import scan


class CivicPlusUrlGuardTests(unittest.TestCase):
    def test_rejects_malformed_and_untrusted_individual_links(self):
        origin = "https://example.gov/Bids.aspx"
        invalid = [
            "http://[bad/Bids.aspx?bidID=4",
            "https://evil.example/Bids.aspx?bidID=4",
            "https://user:password@example.gov/Bids.aspx?bidID=4",
            "https://example.gov:8443/Bids.aspx?bidID=4",
            "/Bids.aspx?bidID=4%0a",
            "/Bids.aspx?bidID=4\\bad",
            "javascript:alert(1)",
            "/Bids.aspx?bidID=not-a-number",
        ]
        for href in invalid:
            with self.subTest(href=href):
                self.assertEqual(civicplus_bids.individual_url(href, origin), "")
        self.assertEqual(civicplus_bids.individual_url("/Bids.aspx?bidID=4", origin),
                         "https://example.gov/Bids.aspx?bidID=4")

    def test_malformed_card_does_not_abort_other_bid_records(self):
        origin = "https://example.gov/Bids.aspx"
        html = ('<article><a href="http://[bad/Bids.aspx?bidID=1">'
                'Bad link</a></article>'
                '<article><a href="/Bids.aspx?bidID=2">'
                'Tree removal bid</a></article>')
        records = civicplus_bids.listing_records(scan.parse_html(html), origin)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["url"], origin + "?bidID=2")


if __name__ == "__main__":
    unittest.main()
