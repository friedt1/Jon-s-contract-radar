"""Offline regression: adjacent Tioga-style notices cannot create a live tree bid.

All HTML, URLs, and dates below are synthetic fixtures, never production leads.
"""
import datetime as dt
import unittest
from unittest.mock import patch

import scan


SOURCE = {
    "name": "Synthetic County Public Works",
    "url": "https://example.gov/departments/public-works/",
    "mode": "direct_page",
    "verified_url": True,
}


class TiogaAdjacentNoticesTests(unittest.TestCase):
    def test_expired_demolition_and_tree_results_are_not_live_tree_bids(self):
        page = """
        <h2>Bids &amp; RFPs</h2>
        <h3>Bid: 67 Central Avenue Demolition Project Rebid</h3>
        <p>Owego, New York. Demolition and site restoration.
        Sealed bids due November 13, 2026 at 2:00 PM.</p>
        <a href="/documents/owego-demolition-rebid.pdf">Demolition bid packet</a>
        <h3>Bid: Public Safety Building Utility Roll-up Door Construction</h3>
        <p>Sealed bids due December 1, 2026 at 11:00 AM.</p>
        <a href="/documents/overhead-door.pdf">Door construction bid packet</a>
        <h2>Bid Results</h2>
        <a href="/documents/tree-results.pdf">Tree Removal 2026 Bid Results</a>
        """
        fetched = []

        def fake_fetch(url, binary=False):
            fetched.append(url)
            if url == SOURCE["url"]:
                return page, "text/html", url
            if url.endswith("owego-demolition-rebid.pdf"):
                return (b"NOTICE TO BIDDERS 67 Central Avenue Demolition "
                        b"Project Rebid. Bids due November 13, 2026.",
                        "application/pdf", url)
            if url.endswith("overhead-door.pdf"):
                return (b"Public Safety Building roll-up door construction. "
                        b"Bids due December 1, 2026.", "application/pdf", url)
            raise AssertionError("Historical result must never be fetched: " + url)

        with (patch.object(scan, "NOW", dt.datetime(
                2026, 11, 14, 16, tzinfo=dt.timezone.utc)),
              patch.object(scan, "fetch", side_effect=fake_fetch),
              patch.object(scan, "pdf_text", side_effect=lambda data: data.decode())):
            leads, status = scan.scan_direct(SOURCE)

        self.assertEqual(leads, [], status)
        self.assertNotIn(SOURCE["url"] + "documents/tree-results.pdf", fetched)
        self.assertIn("result/award links excluded", status)


if __name__ == "__main__":
    unittest.main()
