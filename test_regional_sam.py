import datetime as dt
import io
import json
import unittest
from regional_sam import fetch_notices, parse_notice

class SamTests(unittest.TestCase):
    def test_matching_notice(self):
        x=parse_notice({"title":"Emergency tree removal and debris hauling","noticeId":"123","placeOfPerformance":{"state":{"name":"Pennsylvania"}}})
        self.assertIn("sam.gov/opp/123/view",x["url"])
        self.assertFalse(x["travel_verified"])
    def test_unrelated_notice(self):
        self.assertIsNone(parse_notice({"title":"Office furniture","noticeId":"123"}))
    def test_api_response(self):
        class Reply(io.BytesIO):
            def __enter__(self): return self
            def __exit__(self,*args): self.close()
        def opener(req, timeout):
            self.assertIn("postedFrom=",req.full_url)
            return Reply(json.dumps({"opportunitiesData":[{"title":"Vegetation management contract","noticeId":"abc"}]}).encode())
        result=fetch_notices("test",opener=opener,today=dt.date(2026,10,28))
        self.assertEqual(len(result),1)
if __name__=="__main__": unittest.main()
