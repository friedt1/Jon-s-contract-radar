"""Tioga-style embedded procurement notices are discovery text, not verified bids.

Synthetic offline fixtures only. Never seed these examples into live feeds.
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


class EmbeddedTiogaNoticeTests(unittest.TestCase):
    def test_embedded_current_notice_without_individual_url_is_not_published(self):
        # A department landing page can describe a current project in full.
        # It is not an individual solicitation URL, even with a deadline.
        page = """
        <h2>Notice to Bidders</h2>
        <p>Tree and stump removal contract. Sealed bids due December 1, 2026.</p>
        <h2>2026 Bid Results</h2>
        <a href="/media/tree-results.pdf">Tree Removal 2026 Bid Results</a>
        """
        requests = []

        def fetch(url, binary=False):
            requests.append(url)
            if url != SOURCE["url"]:
                raise AssertionError("Historical results must not be fetched")
            return page, "text/html", url

        with (patch.object(scan, "NOW", dt.datetime(
                2026, 11, 10, 16, tzinfo=dt.timezone.utc)),
              patch.object(scan, "fetch", side_effect=fetch)):
            leads, status = scan.scan_direct(SOURCE)

        self.assertEqual(leads, [])
        self.assertEqual(requests, [SOURCE["url"]])
        self.assertIn("result/award links excluded", status)

    def test_embedded_demolition_and_tree_results_do_not_become_tree_leads(self):
        page = """
        <h2>Current Bids</h2>
        <p>67 Central Avenue Demolition Rebid, Owego NY.
        Bids due November 13, 2026. Site restoration.</p>
        <h2>Bid Results</h2>
        <a href="/media/vegetation-results.pdf">
          Guiderail Vegetation Control 2026 Bid Results
        </a>
        """
        with (patch.object(scan, "NOW", dt.datetime(
                2026, 11, 10, 16, tzinfo=dt.timezone.utc)),
              patch.object(scan, "fetch", return_value=(
                  page, "text/html", SOURCE["url"]))):
            leads, status = scan.scan_direct(SOURCE)

        self.assertEqual(leads, [])
        self.assertIn("result/award links excluded", status)


if __name__ == "__main__":
    unittest.main()
