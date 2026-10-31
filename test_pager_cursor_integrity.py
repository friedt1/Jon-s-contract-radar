"""Offline public listing pager safety regressions; no real bids are fetched."""
import unittest

from public_bid_pagination import next_pages

BASE = "https://county.example/Bids.aspx"


class PagerCursorIntegrityTests(unittest.TestCase):
    def test_malformed_duplicate_and_mixed_case_cursors_are_rejected(self):
        hrefs = (
            "?page=2&page=bad",
            "?PAGE=bad&page=2",
            "?page=2&offset=not-a-number",
            "?page=2&page=",
            "?page=2&Page=%0a",
            "?page=2&%62idID=123",
            "?page=2&bidID=",
        )
        links = [("Next", href, index) for index, href in enumerate(hrefs)]
        self.assertEqual(next_pages(links, BASE, {BASE}), [])

    def test_encoded_controls_in_pager_url_are_rejected(self):
        hrefs = (
            "?page=2%0a",
            "?page=2&tracking=%0d",
            "?page=2#heading%7F",
            "?page=2%00",
            "?page=2%09",
        )
        links = [("Next", href, index) for index, href in enumerate(hrefs)]
        self.assertEqual(next_pages(links, BASE, {BASE}), [])

    def test_valid_numeric_pagination_remains_available(self):
        links = [
            ("Next", "?page=2&offset=40", 0),
            ("Next", "?PAGE=3", 1),
            ("Next", "?page=%34", 2),
            ("Next", "?page=5&page=5", 3),
        ]
        self.assertEqual(next_pages(links, BASE, {BASE}), [
            BASE + "?page=2&offset=40",
            BASE + "?PAGE=3",
            BASE + "?page=%34",
            BASE + "?page=5&page=5",
        ])


if __name__ == "__main__":
    unittest.main()
