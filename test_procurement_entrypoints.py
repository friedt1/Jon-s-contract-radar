import json
import unittest
from pathlib import Path
from source_audit import audit

class ProcurementEntryPointTests(unittest.TestCase):
    def test_verified_entry_points_not_misrepresented_as_bids(self):
        sources=json.loads((Path(__file__).parent/"sources.json").read_text())
        by_name={s["name"]:s for s in sources}
        self.assertEqual(len(sources),102)
        for name,host in [
            ("New York State DOT Region 6","www.dot.ny.gov"),
            ("PennDOT District 3","www.ecmssyst.penndot.pa.gov"),
        ]:
            source=by_name[name]
            self.assertEqual(source["mode"],"direct_page")
            self.assertIn(host,source["url"])
            self.assertTrue(source["require_local_evidence"])
        self.assertIn("PennBid platform",audit(sources)["platforms_configured_not_proven_ingested"])

if __name__=="__main__":
    unittest.main()
