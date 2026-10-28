import unittest
from source_audit import audit

class SourceAuditTests(unittest.TestCase):
    def test_distinct_hosts_and_pending(self):
        rows=[
            {"name":"PennBid platform","type":"platform","mode":"direct_page","url":"https://pennbid.bonfirehub.com"},
            {"name":"Another PennBid path","mode":"direct_page","url":"https://pennbid.bonfirehub.com/portal"},
            {"name":"County","mode":"discovery_pending","url":""},
        ]
        result=audit(rows)
        self.assertEqual(result["total_targets"],3)
        self.assertEqual(result["direct_page_targets"],2)
        self.assertEqual(result["unique_direct_page_hosts"],1)
        self.assertEqual(result["pending_discovery_targets"],1)
        self.assertIn("PennBid platform",result["platforms_configured_not_proven_ingested"])

if __name__ == "__main__":
    unittest.main()
