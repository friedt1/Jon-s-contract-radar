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

    def test_no_invented_notices(self):
        self.assertEqual(build([])["opportunities"],[])
if __name__ == "__main__": unittest.main()
