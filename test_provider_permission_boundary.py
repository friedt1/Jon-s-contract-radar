"""Offline permission-boundary tests; no portal requests or live bid claims."""
import datetime as dt
import unittest
from unittest.mock import patch

import scan
import source_health


SOURCE = {
    "name": "Test County",
    "url": "https://example.gov/bids",
    "mode": "direct_page",
    "verified_url": True,
}


class ExternalProviderBoundaryTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(
            scan, "NOW", dt.datetime(2026, 10, 28, 18, tzinfo=dt.timezone.utc)
        )
        clock.start()
        self.addCleanup(clock.stop)

    def test_external_platform_links_are_not_authorized_by_county_listing(self):
        external = (
            "https://pennbid.bonfirehub.com/opportunities/12",
            "https://www.bidnetdirect.com/new-york/solicitations/42",
            "https://www.pennbid.net/bid/21",
            "https://publicpurchase.com/bids/23",
            "https://procurement.opengov.com/portal/example/projects/88",
        )
        for url in external:
            with self.subTest(url=url):
                self.assertFalse(scan.safe_detail_url(SOURCE["url"], url))
                self.assertTrue(scan.provider_link(url))
        self.assertFalse(scan.safe_detail_url(
            SOURCE["url"], "https://other-county.gov/bid/55"
        ))
        self.assertEqual(
            scan.safe_detail_url(SOURCE["url"], "/bid/55"),
            "https://example.gov/bid/55",
        )

    def test_external_platforms_not_fetched_but_same_host_bid_still_checked(self):
        external = (
            "https://pennbid.bonfirehub.com/opportunities/12",
            "https://www.bidnetdirect.com/new-york/solicitations/42",
        )
        listing = "".join(
            f'<a href="{url}">Tree removal bid due 11/19/2026</a>'
            for url in external
        ) + '<a href="/bid/55">Tree removal bid due 11/19/2026</a>'
        requests = []

        def fake_fetch(url, binary=False):
            requests.append(url)
            if url == SOURCE["url"]:
                body = listing
            elif url == "https://example.gov/bid/55":
                body = "<h1>Tree removal bid due 11/19/2026</h1>"
            else:
                raise AssertionError("Unapproved provider was fetched: " + url)
            return (body.encode() if binary else body, "text/html", url)

        with patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, status = scan.scan_direct(SOURCE)
        self.assertEqual(
            requests, [SOURCE["url"], "https://example.gov/bid/55"]
        )
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("2 external provider links skipped (access required)", status)
        health = source_health.classify(SOURCE, status)
        self.assertEqual(health["external_provider_links_skipped"], 2)

    def test_nested_agency_page_reports_opengov_without_fetching_provider(self):
        # A county may link to its purchasing page first, then to a hosted
        # portal. That nested provider must be reported, not crawled.
        portal = "https://procurement.opengov.com/portal/example/projects/88"
        calls = []

        def fake_fetch(url, binary=False):
            calls.append(url)
            if url == SOURCE["url"]:
                body = '<a href="/procurement">Current bids</a>'
            elif url == "https://example.gov/procurement":
                body = ('<a href="' + portal + '">View Bids</a>'
                        '<a href="/bid/55">Tree removal bid due 11/19/2026</a>')
            elif url == "https://example.gov/bid/55":
                body = '<h1>Tree removal bid due 11/19/2026</h1>'
            else:
                raise AssertionError("Unapproved provider was fetched: " + url)
            return (body.encode() if binary else body, "text/html", url)

        with patch.object(scan, "fetch", side_effect=fake_fetch):
            leads, status = scan.scan_direct(SOURCE)
        self.assertNotIn(portal, calls)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["status"], "unverified")
        self.assertIn("1 external provider links skipped (access required)", status)
        self.assertEqual(source_health.classify(SOURCE, status)["external_provider_links_skipped"], 1)

    def test_opengov_lookalike_is_not_treated_as_provider(self):
        self.assertTrue(scan.provider_link("https://procurement.opengov.com/portal/agency"))
        self.assertFalse(scan.provider_link("https://opengov.com.evil.example/bids"))

    def test_unconnected_portals_never_enter_direct_scan(self):
        for name in scan.UNCONNECTED_PLATFORMS:
            with self.subTest(name=name):
                src = {
                    "name": name,
                    "url": "https://example.gov/portal",
                    "mode": "direct_page",
                    "verified_url": True,
                }
                with patch.object(
                    scan, "scan_direct", side_effect=AssertionError(
                        "Unconnected provider direct scan must not run"
                    )
                ), patch.object(scan, "scan_news", return_value=[]):
                    _, status, leads = scan.run(src)
                self.assertEqual(leads, [])
                self.assertIn("direct access required:", status)
                self.assertNotIn("direct fetched;", status)
                self.assertEqual(
                    source_health.classify(src, status)["direct_state"],
                    "access_required",
                )


if __name__ == "__main__":
    unittest.main()
