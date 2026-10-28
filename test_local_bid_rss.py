import datetime as dt
import unittest
from unittest.mock import patch
import local_bid_rss
import scan

NOW = dt.datetime(2026,10,28,18,tzinfo=dt.timezone.utc)
RECENT = "Tue, 27 Oct 2026 12:00:00 GMT"
OLD = "Tue, 27 Oct 2020 12:00:00 GMT"

def feed(*entries):
    return "<rss version='2.0'><channel>" + "".join(
        "<item><title>"+title+"</title><link>"+url+"</link><description>"+description+"</description><pubDate>"+published+"</pubDate></item>"
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

if __name__=="__main__":
    unittest.main()
