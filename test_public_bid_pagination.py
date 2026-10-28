import unittest
from unittest.mock import patch
import public_bid_pagination as pages
import scan

SOURCE = {"name": "Chemung County bids", "url": "https://example.gov/Bids.aspx", "mode": "direct_page"}

class PublicPaginationTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(scan, "NOW", scan.dt.datetime(2026, 10, 28, 18, tzinfo=scan.dt.timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def test_only_same_path_same_host_https_pages(self):
        links = [
            ("Next", "?page=2", 0),
            ("3", "/Bids.aspx?page=3", 0),
            ("Next", "https://evil.test/Bids.aspx?page=4", 0),
            ("Next", "http://example.gov/Bids.aspx?page=4", 0),
            ("Next", "/different?page=5", 0),
            ("View bid", "?page=9", 0),
        ]
        self.assertEqual(pages.next_pages(links, SOURCE["url"], {SOURCE["url"]}),
                         ["https://example.gov/Bids.aspx?page=2", "https://example.gov/Bids.aspx?page=3"])

    def test_second_page_bid_extracted_and_deduplicated(self):
        listing2 = "https://example.gov/Bids.aspx?page=2"
        detail = "https://example.gov/bid/99"
        content = {
            SOURCE["url"]: '<a href="?page=2">Next</a>',
            listing2: '<table><tr><td>Tree removal bid due 11/19/2026</td><td><a href="/bid/99">Details</a></td></tr></table><a href="?page=2">Next</a>',
            detail: "<h1>Tree removal bid due 11/19/2026</h1>",
        }
        def fake(url, binary=False):
            value = content[url]
            return (value.encode() if binary else value, "text/html", url)
        with patch.object(scan, "fetch", side_effect=fake):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["url"], detail)
        self.assertEqual(leads[0]["deadline"], "2026-11-19")
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("2 listing pages", status)

    def test_more_than_eighteen_public_details(self):
        first = "".join('<a href="/bid/%s">Tree removal bid</a>' % i for i in range(25))
        def fake(url, binary=False):
            value = "<h1>Tree removal bid due 11/19/2026</h1>" if binary else first
            return (value.encode() if binary else value, "text/html", url)
        with patch.object(scan, "fetch", side_effect=fake):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(len(leads), 25)
        self.assertIn("25 details checked", status)

if __name__ == "__main__":
    unittest.main()
