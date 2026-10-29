import unittest
import scan

class BroadPortalScopeTests(unittest.TestCase):
    def test_statewide_sources_require_local_place_evidence(self):
        for source in ("New York State DOT Region 6", "PennDOT District 3"):
            with self.subTest(source=source):
                self.assertFalse(scan.eligible("Tree removal bid due 2026-12-01 in Albany", source))
                self.assertTrue(scan.eligible("Tree removal bid due 2026-12-01 in Elmira", source))
                # Syracuse city is near the two-hour boundary, but this is
                # only text-based discovery evidence, never route verification.
                self.assertTrue(scan.eligible("Tree removal bid due 2026-12-01 in Syracuse", source))
                self.assertFalse(scan.eligible("Demolition bid due 2026-12-01 in Syracuse", source))

    def test_syracuse_candidate_never_claims_verified_travel_or_open_bid(self):
        found = {}
        scan.add_lead(found, "New York State DOT Region 6",
                      "Tree removal bid Syracuse", "https://example.gov/bids/12",
                      "Submission deadline 2026-12-01")
        self.assertEqual(len(found), 1)
        candidate = next(iter(found.values()))
        self.assertEqual(candidate["status"], "unverified")
        self.assertIn("driving time from Elmira unverified", candidate["location"])


if __name__ == "__main__":
    unittest.main()
