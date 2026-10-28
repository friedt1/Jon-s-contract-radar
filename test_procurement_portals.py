import json
import unittest
from pathlib import Path

class RequestedPortalCatalogTests(unittest.TestCase):
    def test_all_requested_portals_registered_without_claiming_live_access(self):
        data=json.loads((Path(__file__).parent/"procurement_portals.json").read_text())
        names={x["name"] for x in data}
        self.assertEqual(len(data),9)
        for name in ("PlanHub","MyGovWatch","The Bid Lab","CLEATUS","DemandStar","BidNet Direct — Empire State Purchasing Group","Public Purchase","Find RFP","NYS Contract Reporter (NYSCR)"):
            self.assertIn(name,names)
        self.assertTrue(all(x["ingestion_status"]=="not_connected" and x["publish_automatically"] is False for x in data))
        self.assertEqual(len({x["url"] for x in data}),len(data))

if __name__=="__main__":
    unittest.main()
