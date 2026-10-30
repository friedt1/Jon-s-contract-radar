"""Offline source-staging checks; no live bids, CDN fetches, or activation."""
import json
import unittest

import civicplus_bids
import probe_staged_sources as staged


GENEVA = "https://cityofgenevany.gov/Bids.aspx"
HORNELL = "https://www.cityofhornell.gov/upcoming-bid-projects"
CDN = "https://irp.cdn-website.com/ee6ee291/files/uploaded/Bid%2BDocs%2B2027.pdf"


def source(name):
    entries = json.loads(staged.SOURCES.read_text(encoding="utf-8"))
    return next(item for item in entries if item["name"] == name)


class CityOfficialStagingTests(unittest.TestCase):
    def test_inventory_preserved_and_neither_source_activated(self):
        entries = json.loads(staged.SOURCES.read_text(encoding="utf-8"))
        self.assertEqual(len(entries), 102)
        self.assertEqual(len({x["name"] for x in entries}), 102)
        for name, url in (("City of Geneva", GENEVA), ("City of Hornell", HORNELL)):
            with self.subTest(name=name):
                item = source(name)
                self.assertEqual(item["candidate_official_url"], url)
                self.assertEqual(item["mode"], "discovery_pending")
                self.assertEqual(item["url"], "")
                self.assertFalse(item["verified_url"])
                self.assertTrue(item["activation_gate"])
        self.assertIn("City of Geneva", civicplus_bids.SOURCES)
        self.assertNotIn("City of Hornell", civicplus_bids.SOURCES)

    def test_geneva_no_open_postings_is_not_a_verified_contract(self):
        calls = []
        def fetch(url, binary=False):
            calls.append((url, binary))
            return ('<h1>Bid Postings</h1>'
                    '<p>There are no open bid postings at this time.</p>',
                    "text/html", url)
        row = staged.probe(source("City of Geneva"), fetch=fetch)
        self.assertEqual(row["state"], "listing_reachable_no_open_bids")
        self.assertTrue(row["listing_retrieved"])
        self.assertEqual(row["individual_records_discovered"], 0)
        self.assertFalse(row["individual_notice_retrieved"])
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertEqual(calls, [(GENEVA, False)])
        self.assertNotIn("opportunities", row)

    def test_hornell_off_host_bid_documents_are_not_fetched(self):
        calls = []
        def fetch(url, binary=False):
            calls.append((url, binary))
            return ('<h1>Upcoming Bid Projects</h1>'
                    '<a href="' + CDN + '">2027 Dodge Durango bid documents</a>'
                    '<a href="/past-bid-projects">Past Bid Projects</a>',
                    "text/html", url)
        row = staged.probe(source("City of Hornell"), fetch=fetch)
        self.assertEqual(row["state"],
                         "listing_reachable_off_host_documents_review_required")
        self.assertEqual(row["off_host_pdf_hosts_unverified"],
                         ["irp.cdn-website.com"])
        self.assertTrue(row["listing_retrieved"])
        self.assertFalse(row["individual_notice_retrieved"])
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertEqual(calls, [(HORNELL, False)])
        self.assertNotIn("opportunities", row)

    def test_unrelated_off_host_pdf_does_not_imply_procurement(self):
        def fetch(url, binary=False):
            return ('<h1>Town information</h1>'
                    '<a href="' + CDN + '">Annual report</a>',
                    "text/html", url)
        row = staged.probe(source("City of Hornell"), fetch=fetch)
        self.assertEqual(row["state"],
                         "official_page_reachable_no_procurement_evidence")
        self.assertNotIn("off_host_pdf_hosts_unverified", row)
        self.assertFalse(row["direct_monitoring_activated"])

    def test_external_provider_remains_higher_priority_than_pdf_links(self):
        def fetch(url, binary=False):
            return ('<h1>Upcoming Bid Projects</h1>'
                    '<p>Use BidNet Direct for bids.</p>'
                    '<a href="' + CDN + '">Old bid packet</a>',
                    "text/html", url)
        row = staged.probe(source("City of Hornell"), fetch=fetch)
        self.assertEqual(row["state"],
                         "listing_reachable_external_provider_access_required")
        self.assertFalse(row["direct_monitoring_activated"])


if __name__ == "__main__":
    unittest.main()
