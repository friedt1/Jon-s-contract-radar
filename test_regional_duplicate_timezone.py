"""Synthetic regional duplicate timezone regressions; never production bids."""
import datetime as dt
import unittest

from regional_rank import build


class RegionalDuplicateTimezoneTests(unittest.TestCase):
    def setUp(self):
        self.today = dt.date(2026, 10, 29)
        self.eastern = {
            "title": "Tree and stump removal",
            "url": "https://county.example/Bids.aspx?bidID=301",
            "deadline": "2026-11-20",
            "deadline_time": "9:00 AM",
            "deadline_timezone": "America/New_York",
            "estimated_value_usd": 250000,
        }
        self.pacific = dict(
            self.eastern,
            url=self.eastern["url"] + "&utm_source=mail",
            deadline_timezone="America/Los_Angeles",
            estimated_value_usd=0,
        )

    def test_mixed_explicit_timezones_withhold_unverified_cutoff(self):
        for notices in ([self.eastern, self.pacific],
                        [self.pacific, self.eastern]):
            with self.subTest(first=notices[0]["deadline_timezone"]):
                result = build(notices, today=self.today)["opportunities"]
                self.assertEqual(len(result), 1)
                item = result[0]
                self.assertEqual(item["deadline"], "2026-11-20")
                self.assertEqual(item["deadline_time"], "")
                self.assertEqual(item["deadline_timezone"], "")
                self.assertEqual(item["deadline_status"], "conflicting_unverified")
                self.assertEqual(item["deadline_conflict"],
                                 ["9:00 am", "explicit non-Eastern timezone"])
                self.assertEqual(item["status"], "review required")

    def test_distinct_bid_ids_do_not_share_timezone_conflict(self):
        distinct = dict(self.pacific, url="https://county.example/Bids.aspx?bidID=302")
        result = build([self.eastern, distinct], today=self.today)["opportunities"]
        self.assertEqual(len(result), 2)
        self.assertTrue(all("deadline_conflict" not in item for item in result))
        self.assertEqual(next(x for x in result if "bidID=301" in x["url"])["deadline_time"],
                         "9:00 AM")

    def test_non_eastern_only_never_certifies_eastern_cutoff(self):
        result = build([self.pacific], today=self.today)["opportunities"]
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["deadline_status"], "stated_unverified")
        self.assertEqual(result[0]["deadline_timezone"], "America/Los_Angeles")

    def test_unrelated_owego_demolition_not_included(self):
        owego = {"title": "Owego demolition rebid",
                 "url": "https://county.example/Bids.aspx?bidID=303",
                 "deadline": "2026-11-13"}
        self.assertEqual(build([owego], today=self.today)["opportunities"], [])


if __name__ == "__main__":
    unittest.main()
