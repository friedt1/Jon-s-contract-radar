"""Offline regional scope regressions; no real notices or live-bid seeding."""
import datetime as dt
import unittest

from regional_rank import build, classify


TODAY = dt.date(2026, 11, 2)
URL = "https://county.example/bids?bidID=401"


class RegionalDescriptionPrecedenceTests(unittest.TestCase):
    def test_specific_description_overrides_misleading_tree_title(self):
        for summary in (
            "Tree removal by others; contractor demolishes the building.",
            "Purchase office furniture and replacement chairs.",
            "Tree removal is excluded from the scope of this contract.",
        ):
            with self.subTest(summary=summary):
                notice = {
                    "title": "Hazardous tree removal RFP",
                    "summary": summary,
                    "url": URL,
                    "deadline": "2026-11-20",
                }
                self.assertIsNone(classify(notice, today=TODAY))
                self.assertEqual(build([notice], today=TODAY)["opportunities"], [])

    def test_description_can_reveal_actual_tree_work(self):
        notice = {
            "title": "County maintenance services",
            "summary": "Vegetation management and brush clearing required.",
            "url": URL,
            "deadline": "2026-11-20",
        }
        item = classify(notice, today=TODAY)
        self.assertIsNotNone(item)
        self.assertEqual(item["status"], "review required")
        self.assertEqual(item["deadline_status"], "stated_unverified")

    def test_attachment_only_description_falls_back_to_notice_title(self):
        for summary in ("See attached specifications.", "Please review the bid documents"):
            with self.subTest(summary=summary):
                notice = {
                    "title": "Tree and stump removal",
                    "summary": summary,
                    "url": URL,
                    "deadline": "2026-11-20",
                }
                self.assertIsNotNone(classify(notice, today=TODAY))

    def test_positive_brush_work_survives_excluded_tree_work(self):
        notice = {
            "title": "Tree removal and site work",
            "summary": "Tree removal by others; brush clearing required by contractor.",
            "url": URL,
            "deadline": "2026-11-20",
        }
        self.assertIsNotNone(classify(notice, today=TODAY))

    def test_excluded_duplicate_cannot_poison_deadline_evidence(self):
        positive = {
            "title": "Tree removal contract",
            "summary": "Hazardous tree removal is required.",
            "url": URL,
            "deadline": "2026-11-20",
        }
        misleading = {
            "title": "Tree removal contract",
            "summary": "Tree removal by others; purchase office supplies.",
            "url": URL + "&utm_source=county",
            "deadline": "2026-11-05",
        }
        for notices in ([positive, misleading], [misleading, positive]):
            with self.subTest(first=notices[0]["summary"]):
                items = build(notices, today=TODAY)["opportunities"]
                self.assertEqual(len(items), 1)
                self.assertEqual(items[0]["deadline"], "2026-11-20")
                self.assertNotIn("deadline_conflict", items[0])

    def test_excluded_bid_number_does_not_split_shared_listing_identity(self):
        positive = {
            "title": "Tree removal contract",
            "summary": "Tree removal required.",
            "bid_number": "RFP-401",
            "url": "https://county.example/bids",
            "deadline": "2026-11-20",
        }
        excluded = {
            "title": "Tree removal contract",
            "summary": "Tree removal by others; office furniture only.",
            "bid_number": "RFP-402",
            "url": "https://county.example/bids",
            "deadline": "2026-11-05",
        }
        items = build([positive, excluded], today=TODAY)["opportunities"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["deadline"], "2026-11-20")
        self.assertNotIn("deadline_conflict", items[0])

    def test_historical_erie_and_unrelated_owego_remain_excluded(self):
        erie = {
            "title": "Erie tree and stump removal",
            "summary": "Tree removal and stump grinding.",
            "url": "https://county.example/bids?bidID=403",
            "deadline": "2026-10-28",
        }
        owego = {
            "title": "Owego demolition rebid",
            "summary": "Building demolition; tree removal by others.",
            "url": "https://county.example/bids?bidID=404",
            "deadline": "2026-11-13",
        }
        self.assertEqual(build([erie, owego], today=TODAY)["opportunities"], [])


if __name__ == "__main__":
    unittest.main()
