import io
import unittest
from regional_dot import check_source, SOURCES
class DotTests(unittest.TestCase):
 def test_sources_are_https(self):
  self.assertTrue(all(s["url"].startswith("https://") for s in SOURCES))
 def test_reachable_does_not_claim_bids(self):
  class Response(io.BytesIO):
   status=200
   def __enter__(self): return self
   def __exit__(self,*args): self.close()
  row=check_source(SOURCES[0],opener=lambda req,timeout:Response(b"ok"))
  self.assertEqual(row["status"],"reachable")
  self.assertIsNone(row["contract_count"])
  self.assertFalse(row["drive_time_verified"])
if __name__=="__main__": unittest.main()
