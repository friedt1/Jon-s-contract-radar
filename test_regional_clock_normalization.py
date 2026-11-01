"""Synthetic deadline-identity regressions; no real notices or live bids."""
import datetime as dt
import unittest

from regional_rank import build


TODAY = dt.date(2026, 11, 1)
BEFORE = dt.datetime(2026, 11, 1, 12, tzinfo=dt.timezone.utc)
URL = "https://county.example/Bids.aspx?bidID=415"


def notice(clock, **extra):
    return {
        "title": "Tree and stump removal",
        "url": URL,
        "deadline": TODAY.isoformat(),
        "deadline_time": clock,
        **extra,
    }


class RegionalClockNormalizationTests(unittest.TestCase):
    def test_same_cutoff_different_formats_are_not_conflicting(self):
        for clocks in (("9:00 AM", "09:00 am"), ("2:00 PM", "02:00 pm"),
                       ("2 PM", "2:00 PM"), ("9 A.M.", "09:00 AM")):
            with self.subTest(clocks=clocks):
                a = notice(clocks[0])
                b = notice(clocks[1], url=URL + "&utm_source=email")
                result = build([a, b], today=TODAY, now=BEFORE)["opportunities"]
                self.assertEqual(len(result), 1)
                self.assertNotIn("deadline_conflict", result[0])
                self.assertEqual(result[0]["deadline_status"], "stated_unverified")

    def test_future_date_equivalent_clocks_are_not_conflicting(self):
        a = notice("2 PM", deadline="2026-11-19")
        b = notice("02:00 pm", deadline="2026-11-19")
        result = build([a, b], today=TODAY, now=BEFORE)["opportunities"]
        self.assertEqual(len(result), 1)
        self.assertNotIn("deadline_conflict", result[0])

    def test_different_valid_cutoffs_remain_conflicting(self):
        a = notice("9:00 AM")
        b = notice("2:00 PM")
        result = build([a, b], today=TODAY, now=BEFORE)["opportunities"]
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["deadline_status"], "conflicting_unverified")
        self.assertEqual(result[0]["deadline_conflict"], ["2:00 pm", "9:00 am"])

    def test_invalid_clock_does_not_invent_conflict(self):
        a = notice("2:00 PM")
        b = notice("pending")
        result = build([a, b], today=TODAY, now=BEFORE)["opportunities"]
        self.assertEqual(len(result), 1)
        self.assertNotIn("deadline_conflict", result[0])
        self.assertEqual(result[0]["deadline_status"], "stated_unverified")

    def test_elapsed_cutoff_still_withholds_later_duplicate(self):
        after = dt.datetime(2026, 11, 1, 16, tzinfo=dt.timezone.utc)
        a = notice("09:00 am")
        b = notice("2 PM", url=URL + "&utm_source=mail")
        result = build([a, b], today=TODAY, now=after)["opportunities"]
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["deadline_status"], "conflicting_unverified")
        self.assertEqual(result[0]["deadline"], TODAY.isoformat())
        self.assertEqual(result[0]["deadline_time"], "")
        self.assertEqual(result[0]["deadline_conflict"], ["2:00 pm", "9:00 am"])

    def test_erie_expired_and_owego_demolition_still_excluded(self):
        erie = notice("9:00 AM", deadline="2026-10-28")
        owego = {"title": "Owego demolition; tree removal by others",
                 "url": "https://county.example/Bids.aspx?bidID=416",
                 "deadline": "2026-11-19"}
        self.assertEqual(build([erie, owego], today=TODAY)["opportunities"], [])


if __name__ == "__main__":
    unittest.main()
