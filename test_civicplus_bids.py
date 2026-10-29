"""Synthetic public CivicPlus HTML fixtures; never mistaken for live solicitations."""
import unittest
from unittest.mock import patch

import civicplus_bids as civic
import scan

BASE = "https://example.gov/Bids.aspx"
SOURCE = {"name": "Chemung County bids", "url": BASE, "mode": "direct_page"}


def card(number, title, status="Open", due="11/19/2026 1:45 PM", repeat=False):
    return ('<article><a href="/Bids.aspx?bidID=' + str(number) + '">' + title + '</a>'
            '<p>Bid No. RFB-' + str(number) + '</p>'
            '<p>Status:</p><p>Closes:</p><p>' + status + '</p><p>' + due + '</p>'
            + ('<a href="/Bids.aspx?bidID=' + str(number) + '">Read on</a>' if repeat else '')
            + '</article>')


class CivicPlusTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(scan, "NOW", scan.dt.datetime(2026, 10, 28, 19, tzinfo=scan.dt.timezone.utc))
        clock.start()
        self.addCleanup(clock.stop)

    def test_separate_bid_records_and_deduplication(self):
        html = ('<p>Show Closed/Awarded/Cancelled Bids</p>'
                + card(10, "Tree removal bid", "Closed", "10/22/2026")
                + card(11, "Tree trimming bid", "Open", "11/19/2026 1:45 PM", repeat=True)
                + card(12, "Computer purchasing bid", "Open", "11/25/2026"))
        records = civic.listing_records(scan.parse_html(html), BASE)
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0]["open_status"], "closed")
        self.assertEqual(records[1]["open_status"], "open")
        self.assertEqual(records[1]["deadline"], "2026-11-19")
        self.assertEqual(records[1]["deadline_time"], "1:45 PM")
        self.assertNotIn("Closed/Awarded/Cancelled", records[1]["description"])

    def test_live_scan_shape_excludes_closed_and_unrelated(self):
        html = (card(10, "Tree removal bid", "Closed", "11/20/2026")
                + card(11, "Tree trimming bid", "Open", "11/19/2026", repeat=True)
                + card(12, "Printer bid", "Open", "11/20/2026"))
        detail = BASE + "?bidID=11"
        def fake(url, binary=False):
            body = "<h1>Tree trimming bid</h1><p>Status: Open</p>" if url == detail else html
            return (body.encode() if binary else body, "text/html", url)
        with patch.object(scan, "fetch", side_effect=fake):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["url"], detail)
        self.assertEqual(leads[0]["deadline"], "2026-11-19")
        self.assertEqual(leads[0]["open_status"], "detail_listed_open")
        self.assertEqual(leads[0]["agency"], "Chemung County (issuing authority)")
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertFalse(leads[0]["travel_verified"])
        self.assertIn("3 individual bid records", status)
        self.assertIn("2 relevant details checked", status)

    def test_detail_closed_overrides_open_listing(self):
        html = card(13, "Tree removal bid", "Open", "11/19/2026")
        def fake(url, binary=False):
            body = "<h1>Tree removal</h1><p>Status: Closed</p>" if binary else html
            return (body.encode() if binary else body, "text/html", url)
        with patch.object(scan, "fetch", side_effect=fake):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(leads, [])
        self.assertIn("1 closed", status)

    def test_missing_deadline_stays_unverified(self):
        html = card(14, "Tree pruning bid", "Open", "")
        def fake(url, binary=False):
            body = "<p>Status: Open</p>" if binary else html
            return (body.encode() if binary else body, "text/html", url)
        with patch.object(scan, "fetch", side_effect=fake):
            leads, _ = scan.scan_direct(SOURCE)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["deadline"], "")
        self.assertEqual(leads[0]["status"], "unverified")

    def test_expired_and_off_host_urls_rejected(self):
        html = card(15, "Tree removal bid", "Open", "10/21/2026")
        html += '<a href="https://other.example/Bids.aspx?bidID=99">Tree removal bid</a>'
        self.assertEqual(len(civic.listing_records(scan.parse_html(html), BASE)), 1)
        def fake(url, binary=False):
            return (html.encode() if binary else html, "text/html", url)
        with patch.object(scan, "fetch", side_effect=fake):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(leads, [])
        self.assertIn("1 expired", status)

    def test_generic_title_uses_individual_notice_scope(self):
        html = (card(21, "General roadside maintenance", "Open", "11/19/2026")
                + card(22, "Office supplies bid", "Open", "11/20/2026"))
        def fake(url, binary=False):
            if not binary:
                return html, "text/html", url
            if "bidID=21" in url:
                body = ("<p>Status: Open</p><p>Description: Removal of hazardous trees "
                        "along local roads.</p><p>Closing Date/Time: 11/19/2026 1:45 PM</p>")
            else:
                body = ("<p>Status: Open</p><p>Description: Office supplies and printers."
                        "</p><p>Closing Date/Time: 11/20/2026</p>")
            return body.encode(), "text/html", url
        with patch.object(scan, "fetch", side_effect=fake):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["url"], BASE + "?bidID=21")
        self.assertIn("hazardous trees", leads[0]["scope"])
        self.assertEqual(leads[0]["deadline"], "2026-11-19")
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("2 relevant details checked", status)

    def test_relevant_listing_prioritized_before_generic_detail_cap(self):
        html = ("".join(card(i, "General services", "Open", "11/19/2026")
                        for i in range(100, 140))
                + card(999, "Tree removal bid", "Open", "11/19/2026"))
        checked = []
        def fake(url, binary=False):
            if not binary:
                return html, "text/html", url
            checked.append(url)
            scope = "Tree removal near Elmira" if "bidID=999" in url else "Office supplies"
            body = "<p>Status: Open</p><p>Description: " + scope + "</p>"
            return body.encode(), "text/html", url
        with patch.object(scan, "fetch", side_effect=fake):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(len(checked), civic.MAX_DETAILS)
        self.assertEqual(checked[0], BASE + "?bidID=999")
        self.assertEqual([r["url"] for r in leads], [BASE + "?bidID=999"])
        self.assertIn("36 relevant details checked", status)

    def test_more_than_eighteen_individual_bid_cards(self):
        html = "".join(card(i, "Tree removal bid", "Open", "11/19/2026")
                       for i in range(100, 125))
        def fake(url, binary=False):
            body = "<p>Status: Open</p>" if binary else html
            return (body.encode() if binary else body, "text/html", url)
        with patch.object(scan, "fetch", side_effect=fake):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(len(leads), 25)
        self.assertIn("25 relevant details checked", status)

    def test_detail_network_failure_never_publishes_listing_candidate(self):
        html = card(31, "Tree removal bid", "Open", "11/19/2026")
        def fake(url, binary=False):
            if binary:
                raise OSError("temporary network failure")
            return html, "text/html", url
        with patch.object(scan, "fetch", side_effect=fake):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(leads, [])
        self.assertIn("1 detail errors: OSError", status)

    def test_redirected_bid_detail_cannot_validate_original_notice(self):
        html = card(32, "Tree trimming bid", "Open", "11/19/2026")
        for destination in (BASE, BASE + "?bidID=999", "https://other.example/Bids.aspx?bidID=32"):
            with self.subTest(destination=destination):
                def fake(url, binary=False):
                    if binary:
                        return b"<p>Status: Open</p><p>Description: Tree trimming</p>", "text/html", destination
                    return html, "text/html", url
                with patch.object(scan, "fetch", side_effect=fake):
                    leads, status = scan.scan_direct(SOURCE)
                self.assertEqual(leads, [])
                self.assertIn("detail redirected away from original bid", status)

    def test_staged_counties_reject_stale_open_badges(self):
        # Synthetic fixtures resemble a common source inconsistency: a listing
        # still says Open even though its closing date has passed.
        for name, url, due in (
            ("Cortland County", "https://www.cortlandcountyny.gov/Bids.aspx", "10/22/2026"),
            ("Yates County", "https://www.yatescountyny.gov/bids.aspx", "10/26/2026"),
        ):
            with self.subTest(name=name):
                self.assertIn(name, civic.SOURCES)
                html = card(77, "Tree removal bid", "Open", due)
                def fake(target, binary=False):
                    return (html.encode() if binary else html, "text/html", target)
                with patch.object(scan, "fetch", side_effect=fake):
                    leads, status = scan.scan_direct({"name": name, "url": url, "mode": "direct_page"})
                self.assertEqual(leads, [])
                self.assertIn("1 expired", status)

    def test_non_html_and_empty_individual_details_are_not_candidates(self):
        html = card(33, "Tree removal bid", "Open", "11/19/2026")
        for payload, kind, error in ((b"%PDF-1.4", "application/pdf", "unsupported detail content"),
                                     (b"<html></html>", "text/html", "empty detail content")):
            with self.subTest(kind=kind):
                def fake(url, binary=False):
                    if binary:
                        return payload, kind, url
                    return html, "text/html", url
                with patch.object(scan, "fetch", side_effect=fake):
                    leads, status = scan.scan_direct(SOURCE)
                self.assertEqual(leads, [])
                self.assertIn(error, status)

    def test_status_and_date_are_not_inferred_from_unrelated_posted_date(self):
        page = scan.parse_html('<a href="/Bids.aspx?bidID=17">Tree removal bid</a>'
                               '<p>Publication Date/Time: 10/29/2026</p>')
        rows = civic.listing_records(page, BASE)
        self.assertEqual(rows[0]["open_status"], "unknown")
        self.assertEqual(rows[0]["deadline"], "")


if __name__ == "__main__":
    unittest.main()
