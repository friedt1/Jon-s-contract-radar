"""PA official entrypoints are staged only, not counted as monitored or live."""
import json
from pathlib import Path
import unittest

import civicplus_bids
import source_health


class PaStagingTests(unittest.TestCase):
    def test_official_pa_pages_remain_pending_until_live_proof(self):
        sources = json.loads((Path(__file__).parent / "sources.json").read_text())
        self.assertEqual(len(sources), 102)
        rows = {x["name"]: x for x in sources}
        for name, host in (
            ("Bradford County PA", "www.bradfordcountypa.gov"),
            ("Susquehanna County", "www.susqco.com"),
        ):
            source = rows[name]
            self.assertEqual(source["mode"], "discovery_pending")
            self.assertFalse(source["verified_url"])
            self.assertFalse(source["url"])
            self.assertIn(host, source["candidate_official_url"])
            self.assertTrue(source["activation_gate"])
            self.assertEqual(source_health.classify(source, "")["direct_state"],
                             "staged_official_url")
        self.assertIn("Bradford County PA", civicplus_bids.SOURCES)
        self.assertNotIn("Susquehanna County", civicplus_bids.SOURCES)
        self.assertEqual(sum(x["mode"] == "direct_page" for x in sources), 18)
        self.assertEqual(sum(bool(x.get("candidate_official_url")) for x in sources), 9)


if __name__ == "__main__":
    unittest.main()
