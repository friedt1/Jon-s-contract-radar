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
    def test_no_invented_notices(self):
        self.assertEqual(build([])["opportunities"],[])
if __name__ == "__main__": unittest.main()
