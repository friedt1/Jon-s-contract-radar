"""District business-office contact is not an operational bid feed."""
import json
from pathlib import Path
import unittest

import audit_source_coverage
import source_health
import scan


class CorningDistrictBidStagingTests(unittest.TestCase):
    def test_official_business_services_contact_staged_not_activated(self):
        sources = json.loads((Path(__file__).parent / "sources.json").read_text())
        self.assertEqual(len(sources), 102)
        source = next(row for row in sources if
                      row["name"] == "Corning-Painted Post Area School District")
        self.assertEqual(
            source["candidate_official_url"],
            "https://www.corningareaschools.com/page/business-services")
        self.assertEqual(source["mode"], "discovery_pending")
        self.assertFalse(source["url"])
        self.assertFalse(source["verified_url"])
        self.assertIn("request", source["activation_gate"].lower())
        self.assertIn("No public per-notice index", source["activation_gate"])
        self.assertEqual(source_health.classify(source, "")["direct_state"],
                         "staged_official_url")
        audit = audit_source_coverage.audit(sources)
        row = next(row for row in audit["sources"] if row["source"] == source["name"])
        self.assertTrue(row["official_url_staged"])
        self.assertFalse(row["direct_fetch_target"])
        self.assertFalse(row["direct_configured"])

    def test_business_contact_page_cannot_create_tree_opportunity(self):
        # Synthetic fixture describes the publisher's document-request
        # workflow, not an individual tree-service solicitation.
        sample = ("Business Services: Request for Bid and/or RFP Documents. "
                  "For copies of current advertised bid or RFP documents, "
                  "contact the district business office.")
        self.assertIsNone(scan.category(sample))
        self.assertFalse(scan.eligible(
            sample, "Corning-Painted Post Area School District"))


if __name__ == "__main__":
    unittest.main()
