import datetime as dt
import unittest
from unittest.mock import patch
from xml.sax.saxutils import escape
import local_bid_rss
import scan

NOW = dt.datetime(2026,10,28,18,tzinfo=dt.timezone.utc)
RECENT = "Tue, 27 Oct 2026 12:00:00 GMT"
OLD = "Tue, 27 Oct 2020 12:00:00 GMT"

def feed(*entries):
    return "<rss version='2.0'><channel>" + "".join(
        "<item><title>"+escape(title)+"</title><link>"+escape(url)+"</link><description>"+escape(description)+"</description><pubDate>"+published+"</pubDate></item>"
        for title,url,description,published in entries
    )+"</channel></rss>"

class LocalBidRSSTests(unittest.TestCase):
    def test_mixed_and_duplicate_bids(self):
        xml=feed(
            ("Chemung tree removal bid","https://example.gov/bid/1","due 11/19/2026",RECENT),
            ("Computer equipment","https://example.gov/bid/2","equipment",RECENT),
            ("Duplicate","https://example.gov/bid/1","same ID",RECENT),
            ("Old tree removal bid","https://example.gov/old","due 11/19/2026",OLD),
            ("Insecure","http://example.gov/bid/3","tree trimming",RECENT)
        )
        rows=local_bid_rss.parse(xml,now=NOW)
        self.assertEqual(len(rows),2)
        self.assertTrue(all(x["status"]=="unverified" for x in rows))
        self.assertTrue(all(not x["original_notice_confirmed"] for x in rows))

    def test_rejects_wrong_feed_type(self):
        with self.assertRaises(ValueError):
            local_bid_rss.parse("<html></html>",now=NOW)

    def test_scanner_integration_preserves_unverified_label_and_dates(self):
        source={"name":"Elmira Next local bids","url":"https://elmiranext.com/bids","mode":"direct_page"}
        xml=feed(("Elmira tree removal bid","https://example.gov/tree/1","due 11/19/2026",RECENT))
        def fake(url,binary=False):
            if url == local_bid_rss.FEED_URL:
                return xml,"application/rss+xml",url
            return "<html></html>","text/html",url
        with patch.object(scan,"fetch",side_effect=fake), patch.object(scan,"NOW",NOW), patch.object(scan,"scan_news",return_value=[]):
            name,status,leads=scan.run(source)
        self.assertEqual(len(leads),1)
        self.assertEqual(leads[0]["status"],"unverified")
        self.assertEqual(leads[0]["published"],"2026-10-27")
        self.assertIn("local bid RSS fetched",status)

    def test_bad_feed_never_claims_success(self):
        with patch.object(scan,"fetch",side_effect=lambda url,binary=False: ("broken","application/xml",url)), patch.object(scan,"scan_news",return_value=[]):
            _,status,leads=scan.run({"name":"Elmira Next local bids","url":"","mode":"discovery_pending"})
        self.assertIn("local bid RSS error",status)
        self.assertEqual(leads,[])


    def test_tracking_variants_are_one_unverified_notice(self):
        xml = feed(
            ("Tree trimming", "https://COUNTY.example/bids?bidID=42&utm_source=mail",
             "due 11/19/2026", RECENT),
            ("Same bid", "https://county.example/bids?bidID=42#details",
             "same notice", RECENT),
        )
        rows = local_bid_rss.parse(xml, now=NOW)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["url"], "https://county.example/bids?bidID=42")
        self.assertEqual(rows[0]["status"], "unverified")
        self.assertFalse(rows[0]["original_notice_confirmed"])

    def test_stale_tracking_duplicate_does_not_hide_fresh_bid(self):
        xml = feed(
            ("Old copy", "https://county.example/bids?bidID=42&utm_source=old",
             "old", OLD),
            ("Current copy", "https://county.example/bids?bidID=42",
             "current", RECENT),
        )
        rows = local_bid_rss.parse(xml, now=NOW)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Current copy")
        self.assertEqual(rows[0]["published"], "2026-10-27")

    def test_unsafe_links_do_not_discard_valid_notices(self):
        unsafe = (
            "https://[broken/bid", "https://user:pass@county.example/bid",
            "https://127.0.0.1/bid", "https://0x7f.0.0.1/bid",
            "https://county.local/bid", "https://county.example:8443/bid",
            "https://county.example/bid%0aInjected", "http://county.example/bid",
        )
        entries = [(f"Bad {i}", url, "tree removal", RECENT)
                   for i, url in enumerate(unsafe)]
        entries.append(("Valid bid", "https://county.example/bids?bidID=44",
                        "tree removal", RECENT))
        rows = local_bid_rss.parse(feed(*entries), now=NOW)
        self.assertEqual([row["title"] for row in rows], ["Valid bid"])

    def test_distinct_bid_ids_and_signed_links_remain_distinct(self):
        signed = ("https://county.example/bids?X-Amz-Signature=abc"
                  "&bidID=44&utm_source=mail")
        xml = feed(
            ("Bid 43", "https://county.example/bids?bidID=43",
             "tree removal", RECENT),
            ("Bid 44", "https://county.example/bids?bidID=44",
             "tree removal", RECENT),
            ("Signed bid 44", signed, "tree removal", RECENT),
        )
        rows = local_bid_rss.parse(xml, now=NOW)
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[-1]["url"], signed)
        self.assertTrue(all(row["status"] == "unverified" for row in rows))

if __name__=="__main__":
    unittest.main()
