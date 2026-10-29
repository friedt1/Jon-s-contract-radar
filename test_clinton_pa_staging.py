"""Clinton PA staging tests use configuration only; never claim live access."""
import json
from pathlib import Path
import unittest

import source_health


class ClintonPAStagingTests(unittest.TestCase):
    def test_official_rfp_index_is_staged_not_activated(self):
        sources = json.loads((Path(__file__).parent / "sources.json").read_text())
        self.assertEqual(len(sources), 102)
        src = next(s for s in sources if s["name"] == "Clinton County PA")
        self.assertEqual(src["mode"], "discovery_pending")
        self.assertFalse(src["verified_url"])
        self.assertEqual(src["url"], "")
        self.assertEqual(src["candidate_official_url"],
                         "https://www.clintoncountypa.gov/about-us/rfps")
        self.assertIn("component-list/detail adapter", src["activation_gate"])
        result = source_health.classify(src, "indirect RSS error: RobotsDenied")
        self.assertEqual(result["direct_state"], "staged_official_url")
        self.assertEqual(result["indirect_state"], "robots_blocked")
        self.assertEqual(result["direct_url"], "")


if __name__ == "__main__":
    unittest.main()
