"""Synthetic shared-listing regional identity regressions; never live bids."""
import datetime as dt
import unittest

from regional_rank import build


TODAY = dt.date(2026, 11, 1)
SHARED = "https://county.example/departments/public-works/bids"


def tree(number, **extra):
    return {
        "title": "Tree removal and stump grinding",
        "bid_number": number,
        "url": SHARED,
        "deadline": "2026-11-19",
        **extra,
    }


class RegionalSharedListingIdentityTests(unittest.TestCase):
    def test_two_numbered_bids_same_official_page_remain_distinct(self):
        a = tree("TR-2026-01", deadline="2026-11-19")
        b = tree("TR-2026-02", deadline="2026-11-27")
        for notices in ([a, b], [b, a]):
            with self.subTest(first=notices[0]["bid_number"]):
                items = build(notices, today=TODAY)["opportunities"]
                self.assertEqual(len(items), 2)
                self.assertEqual({x["bid_number"] for x in items},
                                 {"TR-2026-01", "TR-2026-02"})
                self.assertEqual({x["deadline"] for x in items},
                                 {"2026-11-19", "2026-11-27"})
                self.assertTrue(all("deadline_conflict" not in x for x in items))
                self.assertTrue(all(x["status"] == "review required" for x in items))

    def test_tracking_variants_of_same_number_still_deduplicate(self):
        a = tree("TR-2026-01")
        duplicate = tree(" tr-2026-01  ", url=SHARED + "?utm_source=mail",
                         estimated_value_usd=300000)
        other = tree("TR-2026-02", deadline="2026-11-27")
        items = build([a, duplicate, other], today=TODAY)["opportunities"]
        self.assertEqual(len(items), 2)
        first = next(x for x in items if x["bid_number"].strip().lower() == "tr-2026-01")
        self.assertEqual(first["priority_score"], 3)

    def test_closed_numbered_bid_does_not_suppress_distinct_number(self):
        closed = tree("TR-2026-01", status="Awarded")
        open_candidate = tree("TR-2026-02", deadline="2026-11-27")
        items = build([closed, open_candidate], today=TODAY)["opportunities"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["bid_number"], "TR-2026-02")
        self.assertEqual(items[0]["status"], "review required")

    def test_generic_listing_closed_status_suppresses_ambiguous_numbered_items(self):
        a = tree("TR-2026-01")
        b = tree("TR-2026-02")
        generic_closed = {
            "title": "Procurement listing",
            "url": SHARED,
            "status": "Closed",
        }
        self.assertEqual(build([a, b, generic_closed], today=TODAY)["opportunities"], [])

    def test_single_number_and_unnumbered_copy_stay_conservatively_deduplicated(self):
        a = tree("TR-2026-01", deadline="2026-11-19")
        no_number = dict(a, bid_number="", deadline="2026-11-27")
        items = build([a, no_number], today=TODAY)["opportunities"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["deadline_status"], "conflicting_unverified")
        self.assertEqual(items[0]["deadline"], "")

    def test_unrelated_bid_number_does_not_force_split(self):
        a = tree("TR-2026-01", deadline="2026-11-19")
        unrelated = {"title": "Owego building demolition only",
                     "bid_number": "DEMO-2026-02", "url": SHARED,
                     "deadline": "2026-11-27"}
        items = build([a, unrelated], today=TODAY)["opportunities"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["bid_number"], "TR-2026-01")

    def test_historical_erie_expired_and_owego_demolition_never_live(self):
        erie = tree("ERIE-6565-26", deadline="2026-10-28")
        owego = {"title": "Owego demolition and site restoration",
                 "bid_number": "DEMO-2026-02", "url": SHARED,
                 "deadline": "2026-11-13"}
        self.assertEqual(build([erie, owego], today=TODAY)["opportunities"], [])


if __name__ == "__main__":
    unittest.main()
