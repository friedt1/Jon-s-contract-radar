"""Synthetic URL fixtures only; no real procurement notices are invented."""
import unittest
from unittest.mock import patch

import notice_identity
import scan


class NoticeIdentityTests(unittest.TestCase):
    def setUp(self):
        clock = patch.object(
            scan, "NOW", scan.dt.datetime(2026, 10, 28, 16,
                                         tzinfo=scan.dt.timezone.utc)
        )
        clock.start()
        self.addCleanup(clock.stop)

    def test_tracking_and_fragment_variants_are_one_notice(self):
        original = "https://County.Example/Bids.aspx?bidID=416"
        variants = (
            original,
            original + "#details",
            original + "&utm_source=email&fbclid=xyz",
            "https://county.example:443/Bids.aspx?bidID=416&utm_campaign=notice",
        )
        self.assertEqual(len({notice_identity.notice_id(x) for x in variants}), 1)
        self.assertEqual(notice_identity.canonical_url(variants[2]),
                         "https://county.example/Bids.aspx?bidID=416")

    def test_bid_identifiers_and_unknown_parameters_are_preserved(self):
        a = "https://county.example/Bids.aspx?bidID=416&ref=vendor"
        b = "https://county.example/Bids.aspx?bidID=417&ref=vendor"
        c = "https://county.example/Bids.aspx?bidID=416&ref=other"
        self.assertEqual(len({notice_identity.notice_id(x) for x in (a, b, c)}), 3)
        self.assertIn("ref=vendor", notice_identity.canonical_url(a))

    def test_distinct_query_key_order_deduplicates_same_bid(self):
        first = "https://county.example/Bids.aspx?bidID=416&ref=vendor"
        second = "https://COUNTY.example/Bids.aspx?ref=vendor&utm_source=mail&bidID=416"
        self.assertEqual(notice_identity.notice_id(first),
                         notice_identity.notice_id(second))
        self.assertEqual(notice_identity.canonical_url(second),
                         "https://county.example/Bids.aspx?bidID=416&ref=vendor")

    def test_repeated_query_keys_preserve_order_and_bid_identity(self):
        first = "https://county.example/bids?bidID=12&bidID=13"
        second = "https://county.example/bids?bidID=13&bidID=12"
        self.assertNotEqual(notice_identity.notice_id(first),
                            notice_identity.notice_id(second))
        self.assertEqual(notice_identity.canonical_url(first), first)
        self.assertEqual(notice_identity.canonical_url(second), second)

    def test_signed_notice_urls_are_not_rewritten(self):
        signed = ("https://county.example/bid?z=1&X-Amz-Signature=abc"
                  "&bidID=12&utm_source=mail")
        self.assertEqual(notice_identity.canonical_url(signed), signed)

    def test_rejects_malformed_or_credentialed_urls(self):
        for url in ("", "https://user:pass@county.example/bid",
                    "javascript:alert(1)", "https://[bad/bid",
                    "https://county.example/bid\n", "https://county.example/bid\\bad"):
            with self.subTest(url=url):
                self.assertEqual(notice_identity.canonical_url(url), "")
                self.assertEqual(notice_identity.notice_id(url), "")

    def test_add_lead_deduplicates_tracking_variants(self):
        out = {}
        scan.add_lead(out, "County", "Tree removal bid",
                      "https://county.example/bid?bidID=123&utm_source=mail",
                      "Tree removal contract")
        scan.add_lead(out, "County", "Tree removal bid",
                      "https://county.example/bid?bidID=123#details",
                      "Tree removal contract with a longer scope")
        self.assertEqual(len(out), 1)
        lead = next(iter(out.values()))
        self.assertEqual(lead["url"], "https://county.example/bid?bidID=123")
        self.assertEqual(lead["id"], notice_identity.notice_id(lead["url"]))
        self.assertIn("longer scope", lead["summary"])
        self.assertEqual(lead["status"], "unverified")

    def test_news_published_date_survives_canonicalization(self):
        xml = ('<rss><channel><item>'
               '<title>Tree removal bid</title><description>Tree removal contract</description>'
               '<link>https://county.example/bid?bidID=123&amp;utm_source=mail</link>'
               '<pubDate>Tue, 27 Oct 2026 12:00:00 GMT</pubDate>'
               '</item></channel></rss>')
        with patch.object(scan, "fetch",
                          return_value=(xml, "application/rss+xml", "https://news.example/rss")):
            leads = scan.scan_news({"name": "County"})
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["url"], "https://county.example/bid?bidID=123")
        self.assertEqual(leads[0]["published"], "2026-10-27")


if __name__ == "__main__":
    unittest.main()
