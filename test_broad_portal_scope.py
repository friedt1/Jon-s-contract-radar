import unittest
import scan

class BroadPortalScopeTests(unittest.TestCase):
    def test_statewide_sources_require_local_place_evidence(self):
        for source in ("New York State DOT Region 6", "PennDOT District 3"):
            with self.subTest(source=source):
                self.assertFalse(scan.eligible("Tree removal bid due 2026-12-01 in Albany", source))
                self.assertTrue(scan.eligible("Tree removal bid due 2026-12-01 in Elmira", source))

if __name__ == "__main__":
    unittest.main()
