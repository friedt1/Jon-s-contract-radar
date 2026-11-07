import datetime as dt
import unittest
from regional_dot import extract_nysdot_letting_ids
class LettingIndexTests(unittest.TestCase):
 def test_only_upcoming_and_deduplicated(self):
  html="<p>October 15, 2026 D265834</p><p>October 29, 2026 D265835, D265835</p>"
  rows=extract_nysdot_letting_ids(html,today=dt.date(2026,10,28))
  self.assertEqual([r["contract_id"] for r in rows],["D265835"])
  self.assertFalse(rows[0]["is_qualified_lead"])
 def test_no_fake_opportunities(self):
  self.assertEqual(extract_nysdot_letting_ids("<p>no bids</p>"),[])
if __name__=="__main__": unittest.main()
