import unittest
from regional_rank import classify, build
class RegionalRankTests(unittest.TestCase):
    def test_excludes_unrelated(self):
        self.assertIsNone(classify({"title":"Office chairs","url":"https://example.gov/notice"}))
    def test_excludes_over_twelve_hours(self):
        self.assertIsNone(classify({"title":"Disaster debris removal","url":"https://example.gov/notice","drive_hours":13}))
    def test_missing_travel_not_verified(self):
        x=classify({"title":"State DOT vegetation management","url":"https://example.gov/notice","travel_verified":True})
        self.assertFalse(x["travel_verified"])
    def test_high_priority_large_disaster(self):
        x=classify({"title":"Disaster debris removal","url":"https://example.gov/notice","drive_hours":8,"travel_verified":True,"estimated_value_usd":500000,"estimated_duration_days":30})
        self.assertEqual(x["priority"],"high")
        self.assertTrue(x["travel_verified"])
    def test_nonfinite_or_boolean_drive_times_cannot_be_verified(self):
        for value in ("nan", "NaN", float("nan"), "inf", "-inf", True, False, "unknown"):
            with self.subTest(value=repr(value)):
                x = classify({"title": "Tree removal", "url": "https://example.gov/bid",
                              "drive_hours": value, "travel_verified": True})
                self.assertIsNotNone(x)
                self.assertIsNone(x["drive_hours"])
                self.assertFalse(x["travel_verified"])
                self.assertEqual(x["distance_status"], "unverified")

    def test_truthy_string_is_not_routing_verification(self):
        for flag in ("false", "true", "yes", 1, [], None):
            with self.subTest(flag=flag):
                x = classify({"title": "Vegetation management",
                              "url": "https://example.gov/bid",
                              "drive_hours": 2, "travel_verified": flag})
                self.assertFalse(x["travel_verified"])
                self.assertEqual(x["distance_status"], "unverified")

    def test_finite_route_boundaries_and_negative_hours(self):
        base = {"title": "Storm cleanup", "url": "https://example.gov/bid",
                "travel_verified": True}
        self.assertTrue(classify(dict(base, drive_hours=12))["travel_verified"])
        self.assertIsNone(classify(dict(base, drive_hours=12.01)))
        self.assertIsNone(classify(dict(base, drive_hours=-1)))

    def test_nonfinite_values_cannot_inflate_priority(self):
        base = {"title": "Tree removal", "url": "https://example.gov/bid"}
        for bad in ("inf", float("nan"), True, -100):
            with self.subTest(bad=repr(bad)):
                x = classify(dict(base, estimated_value_usd=bad,
                                  estimated_duration_days=bad))
                self.assertEqual(x["priority_score"], 0)
                self.assertEqual(x["priority"], "review")

    def test_past_deadline_and_closed_publisher_states_are_excluded(self):
        base = {"title": "Tree removal", "url": "https://county.example/bids?bidID=12"}
        today = __import__("datetime").date(2026, 10, 29)
        self.assertIsNone(classify(dict(base, deadline="2026-10-28"), today=today))
        self.assertIsNone(classify(dict(base, deadline="2026-11-30",
                                        open_status="detail_listed_awarded"), today=today))
        self.assertIsNone(classify(dict(base, status="Cancelled"), today=today))
        self.assertIsNone(classify(dict(base, open_status="listing_closed"), today=today))
        # Historical Erie tree/stump example: never treat its expired cutoff as live.
        erie = dict(base, title="Tree & Stump Removal", deadline="2026-10-28")
        self.assertEqual(build([erie], today=today)["opportunities"], [])

    def test_same_day_and_unknown_deadline_are_review_only(self):
        today = __import__("datetime").date(2026, 10, 29)
        base = {"title": "Vegetation management", "url": "https://county.example/bid"}
        same_day = classify(dict(base, deadline="2026-10-29"), today=today)
        self.assertEqual(same_day["deadline_status"], "stated_unverified")
        self.assertEqual(same_day["status"], "review required")
        unknown = classify(base, today=today)
        self.assertEqual(unknown["deadline_status"], "unknown")
        invalid = classify(dict(base, deadline="tomorrow"), today=today)
        self.assertEqual(invalid["deadline_status"], "invalid")
        self.assertEqual(invalid["status"], "review required")

    def test_unrelated_owego_demolition_never_enters_regional_tree_feed(self):
        today = __import__("datetime").date(2026, 10, 29)
        notice = {"title": "67 Central Avenue Demolition Rebid",
                  "summary": "Building demolition and site restoration in Owego",
                  "deadline": "2026-11-13", "url": "https://county.example/bid"}
        self.assertEqual(build([notice], today=today)["opportunities"], [])

    def test_rejects_credentialed_or_malformed_https_urls(self):
        for url in ("https://user:pass@county.example/bid",
                    "https://county.example/bid\\n",
                    "https://[bad/bid", "https://county.example/bid\\\\bad"):
            with self.subTest(url=url):
                self.assertIsNone(classify({"title": "Tree removal", "url": url}))

    def test_tracking_duplicates_collapse_but_distinct_bid_ids_remain(self):
        today = __import__("datetime").date(2026, 10, 29)
        base = {"title": "Storm cleanup", "url": "https://COUNTY.example/bids?bidID=12",
                "summary": "Short description"}
        variant = dict(base, url="https://county.example:443/bids?bidID=12&utm_source=mail",
                       estimated_value_usd=500000)
        distinct = dict(base, url="https://county.example/bids?bidID=13")
        result = build([base, variant, distinct], today=today)["opportunities"]
        self.assertEqual(len(result), 2)
        self.assertEqual(len({x["url"] for x in result}), 2)
        self.assertEqual(next(x for x in result if "bidID=12" in x["url"])["priority_score"], 3)
        self.assertTrue(all(x["status"] == "review required" for x in result))

    def test_no_invented_notices(self):
        self.assertEqual(build([])["opportunities"],[])
if __name__ == "__main__": unittest.main()
