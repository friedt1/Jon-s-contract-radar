import unittest
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
        self.assertFalse(promotable(rows[0]))

    def test_no_invented_links_or_verified_status(self):
        for row in extract(SAMPLE):
            self.assertIsNone(row["detail_url"])
            self.assertEqual(row["status"], "research_only")
            self.assertFalse(promotable(row))

    def test_requires_independent_checks(self):
        row = extract(SAMPLE)[0] | {
            "status": "verified_open", "detail_url": "https://www.nyscr.ny.gov/Ads/View/2149991",
            "authorized_access": True, "open_status_confirmed": True, "location_confirmed": True
        }
        self.assertTrue(promotable(row))
        self.assertFalse(promotable(row | {"authorized_access": False}))
        self.assertFalse(promotable(row | {"detail_url": "javascript:alert(1)"}))

if __name__ == "__main__":
    unittest.main()
