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

    def test_common_pager_labels_and_safe_numeric_cursors(self):
        links = [
            ("Next »", "?page=2", 0),
            ("Page 3", "?page=3", 1),
            ("2 of 4", "?page=4", 2),
            ("Next >", "?offset=40", 3),
            ("Next page 5", "?pageno=5", 4),
            ("View bid", "?page=9", 5),
            ("Older news", "?page=10", 6),
        ]
        self.assertEqual(pages.next_pages(links, SOURCE["url"], {SOURCE["url"]}), [
            "https://example.gov/Bids.aspx?page=2",
            "https://example.gov/Bids.aspx?page=3",
            "https://example.gov/Bids.aspx?page=4",
            "https://example.gov/Bids.aspx?offset=40",
            "https://example.gov/Bids.aspx?pageno=5",
        ])

    def test_pagination_rejects_credentialed_malformed_or_bid_detail_urls(self):
        links = [
            ("Next", "https://user:secret@example.gov/Bids.aspx?page=2", 0),
            ("Next", "https://example.gov:8443/Bids.aspx?page=2", 0),
            ("Next", "?page=next", 0),
            ("Next", "?page=-2", 0),
            ("Next", "?page=2&bidID=42", 0),
            ("Next", "/Bids.aspx?page=2\\n", 0),
            ("Next", "https://other.gov/Bids.aspx?page=2", 0),
            ("Next", "?page=2#top", 0),
            ("Next", "?page=2#duplicate", 0),
        ]
        self.assertEqual(pages.next_pages(links, SOURCE["url"], {SOURCE["url"]}),
                         ["https://example.gov/Bids.aspx?page=2"])

    def test_next_arrow_reaches_third_page_individual_bid(self):
        second = "https://example.gov/Bids.aspx?page=2"
        third = "https://example.gov/Bids.aspx?page=3"
        detail = "https://example.gov/bid/103"
        pages_by_url = {
            SOURCE["url"]: '<a href="?page=2">Next »</a>',
            second: '<a href="?page=3">Page 3</a>',
            third: '<a href="/bid/103">Tree removal bid</a>',
            detail: "<h1>Tree removal bid due November 19, 2026</h1>",
        }
        fetched = []
        def fake(url, binary=False):
            fetched.append(url)
            body = pages_by_url[url]
            return (body.encode() if binary else body, "text/html", url)
        with patch.object(scan, "fetch", side_effect=fake):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(fetched, [SOURCE["url"], second, third, detail])
        self.assertEqual([lead["url"] for lead in leads], [detail])
        self.assertIn("3 listing pages", status)
        self.assertIn("1 details checked", status)

    def test_ambiguous_page_cursors_are_not_fetched(self):
        links = [
            ("Next", "?page=2&page=3", 0),
            ("Next", "?page=2&offset=40", 0),
            ("Next", "?page=2&page=2", 0),
            ("Next", "?page=2&bidID=99", 0),
            ("Next", "?page=2", 0),
            ("Page 3", "?pageno=3", 0),
        ]
        self.assertEqual(pages.next_pages(links, SOURCE["url"], {SOURCE["url"]}), [
            "https://example.gov/Bids.aspx?page=2",
            "https://example.gov/Bids.aspx?pageno=3",
        ])

    def test_redirected_pagination_must_preserve_listing_and_cursor(self):
        requested = "https://example.gov/Bids.aspx?page=2"
        for final in (
            "https://example.gov/Login.aspx?page=2",
            "https://example.gov/Bids.aspx?page=1",
            "https://example.gov/Bids.aspx?offset=2",
            "https://example.gov/Bids.aspx?bidID=99",
            "https://other.gov/Bids.aspx?page=2",
            "http://example.gov/Bids.aspx?page=2",
            "https://example.gov/Bids.aspx?page=2%0a",
        ):
            with self.subTest(final=final):
                self.assertFalse(pages.valid_pagination_redirect(requested, final))
        self.assertTrue(pages.valid_pagination_redirect(
            requested, "https://example.gov/Bids.aspx?page=2"))

    def test_redirected_login_or_changed_cursor_cannot_supply_notice(self):
        # Synthetic publisher responses; not a live Owego/Erie solicitation.
        requested = "https://example.gov/Bids.aspx?page=2"
        for redirected in (
            "https://example.gov/Login.aspx?page=2",
            "https://example.gov/Bids.aspx?page=1",
        ):
            fetched = []
            def fake(url, binary=False):
                fetched.append(url)
                if url == SOURCE["url"]:
                    return '<a href="?page=2">Next</a>', "text/html", url
                if url == requested:
                    return ('<a href="/bid/999">Tree removal bid</a>',
                            "text/html", redirected)
                raise AssertionError("redirected content must not be followed")
            with self.subTest(redirected=redirected), patch.object(
                    scan, "fetch", side_effect=fake):
                leads, status = scan.scan_direct(SOURCE)
            self.assertEqual(leads, [])
            self.assertEqual(fetched, [SOURCE["url"], requested])
            self.assertIn("pagination redirect changed listing or cursor", status)

    def test_invalid_pager_does_not_consume_detail_budget(self):
        detail = "https://example.gov/bid/104"
        listing = ('<a href="?page=2&bidID=999">Next</a>'
                   '<a href="/bid/104">Tree trimming bid</a>')
        fetched = []
        def fake(url, binary=False):
            fetched.append(url)
            body = listing if url == SOURCE["url"] else "<h1>Tree trimming bid due 11/19/2026</h1>"
            return (body.encode() if binary else body, "text/html", url)
        with patch.object(scan, "fetch", side_effect=fake):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(fetched, [SOURCE["url"], detail])
        self.assertEqual([lead["url"] for lead in leads], [detail])
        self.assertIn("1 details checked", status)

if __name__ == "__main__":
    unittest.main()
