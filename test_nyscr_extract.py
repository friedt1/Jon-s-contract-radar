import unittest
import datetime as dt
from nyscr_extract import extract, promotable

SAMPLE = """Contracting Opportunities
Tree removal and stump grinding in Chemung County
CR#:
2149991
Agency:
Example County
Issue date:
10/28/2026
Due date:
11/19/2026
Location:
Elmira NY
Category:
Agriculture, Forestry, Gardening
Ad type:
General
Purchase of printers
CR#:
2149992
Agency:
Example Office
Due date:
11/20/2026
Location:
Albany NY
Tree pruning and roadside clearing
CR#:
2149993
Agency:
Example Transportation Agency
Due date:
11/25/2026
Location:
Ithaca NY
"""

class NYSCRExtractTests(unittest.TestCase):
    def test_individual_records_skip_unrelated(self):
        rows = extract(SAMPLE)
        self.assertEqual([r["cr_number"] for r in rows], ["2149991", "2149993"])
        self.assertEqual(rows[0]["title"], "Tree removal and stump grinding in Chemung County")
        self.assertEqual(rows[0]["deadline"], "2026-11-19")
        self.assertEqual(rows[1]["location"], "Ithaca NY")

    def test_missing_deadline_is_unverified(self):
        rows = extract("Brush clearing contract\nCR#:\n2149994\nAgency:\nExample Agency")
        self.assertEqual(rows[0]["deadline"], "")
        self.assertFalse(promotable(rows[0], today=dt.date(2026, 10, 28)))

    def test_no_invented_links_or_verified_status(self):
        for row in extract(SAMPLE):
            self.assertIsNone(row["detail_url"])
            self.assertEqual(row["status"], "research_only")
            self.assertFalse(promotable(row, today=dt.date(2026, 10, 28)))

    def test_requires_independent_checks(self):
        row = extract(SAMPLE)[0] | {
            "status": "verified_open", "detail_url": "https://www.nyscr.ny.gov/Ads/View/2149991",
            "authorized_access": True, "open_status_confirmed": True, "location_confirmed": True
        }
        day = dt.date(2026, 10, 28)
        self.assertTrue(promotable(row, today=day))
        self.assertFalse(promotable(row | {"authorized_access": False}, today=day))
        self.assertFalse(promotable(row | {"detail_url": "javascript:alert(1)"}, today=day))

    def test_export_fields_are_explicitly_unverified(self):
        row = extract(SAMPLE)[0]
        self.assertEqual(row["open_status"], "unknown")
        self.assertEqual(row["scope"], row["title"])
        self.assertEqual(row["deadline_time"], "")
        self.assertEqual(row["deadline_timezone"], "unverified")
        self.assertFalse(row["location_verified"])

    def test_authorized_export_captures_explicit_official_link_and_scope(self):
        text = """Roadway maintenance project
CR#:
2149995
Agency: Example Transportation Department
Due date: 11/20/2026
Location: Elmira, NY
Description: Removal of hazardous trees and roadside brush along state routes.
Detail URL: https://www.nyscr.ny.gov/Ads/View/2149995
"""
        rows = extract(text)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "Roadway maintenance project")
        self.assertIn("hazardous trees", rows[0]["scope"])
        self.assertEqual(rows[0]["agency"], "Example Transportation Department")
        self.assertEqual(rows[0]["deadline"], "2026-11-20")
        self.assertEqual(rows[0]["detail_url"], "https://www.nyscr.ny.gov/Ads/View/2149995")
        self.assertEqual(rows[0]["open_status"], "unknown")
        self.assertEqual(rows[0]["status"], "research_only")
        self.assertFalse(promotable(rows[0], today=dt.date(2026, 10, 28)))

    def test_wrapped_description_finds_tree_scope_and_stops_at_next_notice(self):
        text = """Highway maintenance contract
CR#:
2149997
Agency: Example Highway Agency
Description:
Annual maintenance and hazard response including
removal of hazardous trees along county roads.
Due date: 11/20/2026
Location: Elmira NY
Detail URL: https://www.nyscr.ny.gov/Ads/View/2149997
Office equipment
CR#:
2149998
Agency: Example Office
Description: Paper and printer supplies
Due date: 11/21/2026
"""
        rows = extract(text)
        self.assertEqual([r["cr_number"] for r in rows], ["2149997"])
        self.assertIn("removal of hazardous trees", rows[0]["scope"])
        self.assertNotIn("Office equipment", rows[0]["scope"])
        self.assertEqual(rows[0]["deadline"], "2026-11-20")
        self.assertEqual(rows[0]["detail_url"], "https://www.nyscr.ny.gov/Ads/View/2149997")
        self.assertEqual(rows[0]["status"], "research_only")
        self.assertFalse(promotable(rows[0], today=dt.date(2026, 10, 28)))

    def test_authorized_export_rejects_spoofed_or_mismatched_links(self):
        for url in ("https://www.nyscr.ny.gov.evil.example/Ads/View/2149995",
                    "https://www.nyscr.ny.gov/Ads/View/2149996",
                    "http://www.nyscr.ny.gov/Ads/View/2149995",
                    "https://www.nyscr.ny.gov/"):
            with self.subTest(url=url):
                text = ("Tree removal bid\nCR#:\n2149995\nAgency: Example\n"
                        "Due date: 11/20/2026\nDetail URL: " + url)
                rows = extract(text)
                self.assertEqual(len(rows), 1)
                self.assertIsNone(rows[0]["detail_url"])

    def test_adjacent_notices_do_not_share_description_or_url(self):
        text = """Tree trimming bid
CR#:
2149995
Agency: First Agency
Detail URL: https://www.nyscr.ny.gov/Ads/View/2149995
Due date: 11/20/2026
Road maintenance contract
CR#:
2149996
Agency: Second Agency
Description: Stump grinding and vegetation management.
Due date: 11/21/2026
"""
        rows = extract(text)
        self.assertEqual([r["cr_number"] for r in rows], ["2149995", "2149996"])
        self.assertEqual(rows[0]["detail_url"], "https://www.nyscr.ny.gov/Ads/View/2149995")
        self.assertIsNone(rows[1]["detail_url"])
        self.assertEqual(rows[1]["agency"], "Second Agency")
        self.assertIn("Stump grinding", rows[1]["scope"])

    def test_reject_expired_and_invalid_deadlines(self):
        row = extract(SAMPLE)[0] | {
            "status": "verified_open",
            "detail_url": "https://www.nyscr.ny.gov/Ads/View/2149991",
            "authorized_access": True, "open_status_confirmed": True, "location_confirmed": True
        }
        self.assertFalse(promotable(row, today=dt.date(2026, 11, 20)))
        self.assertFalse(promotable(row | {"deadline": "not-a-date"}, today=dt.date(2026, 10, 28)))
        self.assertFalse(promotable(row | {"deadline": ""}, today=dt.date(2026, 10, 28)))

    def test_reject_unrelated_or_mismatched_solicitation_links(self):
        row = extract(SAMPLE)[0] | {
            "status": "verified_open",
            "authorized_access": True, "open_status_confirmed": True, "location_confirmed": True
        }
        day = dt.date(2026, 10, 28)
        for link in ("https://example.com/Ads/View/2149991",
                     "https://www.nyscr.ny.gov/",
                     "https://www.nyscr.ny.gov/Ads/View/2149992",
                     "http://www.nyscr.ny.gov/Ads/View/2149991",
                     "https://www.nyscr.ny.gov.evil.example/Ads/View/2149991"):
            with self.subTest(link=link):
                self.assertFalse(promotable(row | {"detail_url": link}, today=day))

    def test_reject_unconfirmed_scope_or_worksite(self):
        row = extract(SAMPLE)[0] | {
            "status": "verified_open",
            "detail_url": "https://www.nyscr.ny.gov/Ads/View/2149991",
            "authorized_access": True, "open_status_confirmed": True, "location_confirmed": True
        }
        day = dt.date(2026, 10, 28)
        self.assertFalse(promotable(row | {"scope": "Printer supplies"}, today=day))
        self.assertFalse(promotable(row | {"location_confirmed": False}, today=day))
        self.assertFalse(promotable(row | {"agency": ""}, today=day))

if __name__ == "__main__":
    unittest.main()
