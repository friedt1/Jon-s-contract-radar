"""Offline source-health tests: synthetic statuses never represent real contracts."""
import unittest

import source_health


class SourceHealthTests(unittest.TestCase):
    def test_fetched_homepage_is_not_verified_bid_extraction(self):
        src = {"name": "County", "mode": "direct_page", "url": "https://county.example/Bids.aspx",
               "verified_url": True}
        row = source_health.classify(src, "direct fetched; 1 listing pages; 4 individual bid records; "
                                    "3 relevant details checked; 2 individual bid details fetched; "
                                    "0 unverified candidates; "
                                    "indirect RSS error: RobotsDenied")
        self.assertEqual(row["direct_state"], "fetched_unverified")
        self.assertEqual(row["individual_bid_records_found"], 4)
        self.assertEqual(row["detail_fetches_attempted"], 3)
        self.assertEqual(row["individual_bid_details_fetched"], 2)
        self.assertEqual(row["unverified_candidates"], 0)
        self.assertEqual(row["indirect_state"], "robots_blocked")

    def test_staged_official_url_does_not_count_as_direct(self):
        src = {"name": "Yates County", "mode": "discovery_pending", "url": "",
               "verified_url": False, "candidate_official_url": "https://www.yatescountyny.gov/bids.aspx"}
        summary = source_health.summarize([src], {"Yates County": "indirect RSS error: RobotsDenied"})
        self.assertEqual(summary["counts"]["configured_direct"], 0)
        self.assertEqual(summary["counts"]["staged_official_url"], 1)
        self.assertEqual(summary["counts"]["indirect_robots_blocked"], 1)

    def test_blocked_and_login_only_are_not_successful(self):
        sources = [
            {"name": "PennBid", "mode": "direct_page", "url": "https://pennbid.example", "verified_url": True},
            {"name": "BidNet", "mode": "direct_page", "url": "https://bidnet.example", "verified_url": True},
            {"name": "Other", "mode": "discovery_pending", "url": "", "verified_url": False},
        ]
        status = {
            "PennBid": "direct blocked by robots policy: disallowed",
            "BidNet": "direct fetched; 1 listing pages; 0 candidates; "
                      "individual listing ingestion not connected",
            "Other": "indirect RSS error: RobotsDenied",
        }
        summary = source_health.summarize(sources, status)
        self.assertEqual(summary["counts"]["configured_direct"], 2)
        self.assertEqual(summary["counts"]["configured_access_required"], 1)
        self.assertEqual(summary["counts"]["configured_fetch_targets"], 1)
        self.assertEqual(summary["counts"]["fetched_unverified"], 0)
        self.assertEqual(summary["counts"]["robots_blocked"], 1)
        self.assertEqual(summary["counts"]["access_required"], 1)
        self.assertEqual(summary["counts"]["not_configured"], 1)
        self.assertEqual(summary["counts"]["individual_bid_details_fetched"], 0)

    def test_failed_fetch_and_missing_status_are_visible(self):
        src = {"name": "County", "mode": "direct_page", "url": "https://county.example/bids",
               "verified_url": True}
        self.assertEqual(source_health.classify(src, "direct error: TimeoutError")["direct_state"], "fetch_error")
        self.assertEqual(source_health.classify(src, "")["direct_state"], "not_fetched")

    def test_official_feed_and_authorized_api_are_direct_modes(self):
        sources = [
            {"name": "Feed", "mode": "official_feed", "url": "https://county.example/feed.xml",
             "verified_url": True},
            {"name": "API", "mode": "authorized_api", "url": "https://county.example/api/bids",
             "verified_url": True},
        ]
        summary = source_health.summarize(sources, {
            "Feed": "direct fetched; 1 listing pages; 0 individual bid details fetched",
            "API": "direct error: TimeoutError",
        })
        self.assertEqual(summary["counts"]["configured_direct"], 2)
        self.assertEqual(summary["counts"]["fetched_unverified"], 1)
        self.assertEqual(summary["counts"]["fetch_error"], 1)
        self.assertEqual(summary["counts"]["not_configured"], 0)


if __name__ == "__main__":
    unittest.main()
