"""Offline tests: official Waverly contractor RFQ is not an active tree bid."""
import datetime as dt
import json
import unittest

import probe_staged_sources as staged
import scan


NOW = dt.datetime(2026, 10, 29, 17, 30, tzinfo=dt.timezone.utc)
OFFICIAL = "https://villageofwaverly.gov/"
HISTORICAL_RFQ = (
    "<h1>Seeking RFQ for Contractors for NYF Grant</h1>"
    "<p>Request for Qualifications for Building Contractors for Small Project Fund</p>"
    "<p>Typical trades: roofing, electrical, plumbing, HVAC, masonry and painting.</p>"
    "<p>Applications should be returned by September 15, 2026.</p>"
)


class WaverlyStagingTests(unittest.TestCase):
    def test_official_homepage_is_staged_not_directly_monitored(self):
        sources = json.loads(staged.SOURCES.read_text(encoding="utf-8"))
        self.assertEqual(len(sources), 102)
        self.assertEqual(len({s["name"] for s in sources}), 102)
        row = next(s for s in sources if s["name"] == "Village of Waverly")
        self.assertEqual(row["mode"], "discovery_pending")
        self.assertFalse(row["verified_url"])
        self.assertFalse(row["url"])
        self.assertEqual(row["candidate_official_url"], OFFICIAL)
        self.assertIn("September 15, 2026", row["activation_gate"])

    def test_visible_historical_rfq_never_activates_monitoring(self):
        row = {"name": "Village of Waverly", "mode": "discovery_pending",
               "candidate_official_url": OFFICIAL, "activation_gate": "Review terms"}
        calls = []
        def fake_fetch(url, binary=False):
            calls.append((url, binary))
            return HISTORICAL_RFQ, "text/html", url
        result = staged.probe(row, fetch=fake_fetch, now=NOW)
        self.assertEqual(result["state"], "listing_reachable_adapter_required")
        self.assertTrue(result["listing_retrieved"])
        self.assertEqual(result["individual_records_discovered"], 0)
        self.assertFalse(result["individual_notice_retrieved"])
        self.assertFalse(result["direct_monitoring_activated"])
        self.assertEqual(calls, [(OFFICIAL, False)])
        self.assertNotIn("opportunities", result)

    def test_unrelated_rfqs_and_owego_demolition_do_not_become_tree_bids(self):
        self.assertIsNone(scan.category(HISTORICAL_RFQ))
        found = {}
        scan.add_lead(found, "Village of Waverly", "NYF Building Contractors RFQ",
                      "https://villageofwaverly.gov/post.php?pid=48",
                      HISTORICAL_RFQ, "direct detail candidate")
        scan.add_lead(found, "Tioga County NY", "67 Central Avenue Demolition Rebid",
                      "https://example.org/owego-demolition",
                      "Demolition and site restoration. Bids due November 13, 2026.",
                      "direct detail candidate")
        self.assertEqual(found, {})

    def test_generic_official_homepage_is_not_called_bid_listing(self):
        row = {"name": "Village of Waverly", "mode": "discovery_pending",
               "candidate_official_url": OFFICIAL}
        result = staged.probe(row, fetch=lambda url, binary=False:
                              ("<h1>Welcome to the village</h1>", "text/html", url),
                              now=NOW)
        self.assertEqual(result["state"],
                         "official_page_reachable_no_procurement_evidence")
        self.assertFalse(result["direct_monitoring_activated"])
        self.assertFalse(result["individual_notice_retrieved"])


if __name__ == "__main__":
    unittest.main()
