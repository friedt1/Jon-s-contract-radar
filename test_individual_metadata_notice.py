"""Synthetic individual metadata table regression cases; never published as live bids."""
import unittest
from unittest.mock import patch
import scan

SOURCE = {'name': 'Test County', 'url': 'https://example.gov/bids', 'mode': 'direct_page'}
NOTICE = 'https://example.gov/bid/123'
TABLE_NOTICE = ('<h1>County bid detail</h1><table>'
 '<tr><th>Bid Number:</th><td>123</td></tr>'
 '<tr><th>Description:</th><td>Hazardous tree removal along county roads</td></tr>'
 '<tr><th>Closing Date/Time:</th><td>11/19/2026 10:00 AM</td></tr>'
 '<tr><th>Status:</th><td>Open</td></tr></table>')

class IndividualMetadataTests(unittest.TestCase):
 def setUp(self):
  clock=patch.object(scan,'NOW',scan.dt.datetime(2026,10,28,18,tzinfo=scan.dt.timezone.utc))
  clock.start();self.addCleanup(clock.stop)

 def scan_fixture(self, detail):
  def fake(url,binary=False):
   if url==SOURCE['url']:
    body='<a href="/bid/123">County solicitation details</a>'
   elif url==NOTICE:
    body=detail
   else:
    raise OSError('detail inaccessible')
   return (body.encode() if binary else body,'text/html',url)
  with patch.object(scan,'fetch',side_effect=fake):
   return scan.scan_direct(SOURCE)

 def test_metadata_table_is_one_unverified_individual_bid(self):
  leads,status=self.scan_fixture(TABLE_NOTICE)
  body='County bid detail Bid Number: 123 Description: Hazardous tree removal along county roads Closing Date/Time: 11/19/2026 10:00 AM Status: Open'
  self.assertTrue(scan.individual_metadata_notice(body,NOTICE))
  self.assertIn('tree removal',scan.metadata_description(body))
  scope=scan.metadata_description(body)
  self.assertEqual(scan.category(scope),'Tree removal')
  self.assertTrue(scan.eligible(scope+' bid Due date: 2026-11-19','Test County'))
  self.assertTrue(scan.eligible(body,'Test County'))
  manual={}
  scan.add_lead(manual,'Test County','Hazardous tree removal bid',NOTICE,scope+' Deadline: 2026-11-19',evidence=body)
  self.assertEqual(len(manual),1,msg=str(manual))
  self.assertEqual(len(leads),1,msg=status)
  self.assertEqual(leads[0]['url'],NOTICE)
  self.assertEqual(leads[0]['deadline'],'2026-11-19')
  self.assertEqual(leads[0]['status'],'unverified')
  self.assertEqual(leads[0]['lead_type'],'individual metadata bid candidate')
  self.assertIn('1 individual bid details fetched',status)

 def test_unrelated_metadata_description_does_not_inherit_navigation_keywords(self):
  body=TABLE_NOTICE.replace('Hazardous tree removal along county roads','Office furniture')
  body=body.replace('<h1>County bid detail</h1>','<nav>Tree removal bids</nav>')
  leads,_=self.scan_fixture(body)
  self.assertEqual(leads,[])

 def test_expired_and_closed_metadata_notices_are_excluded(self):
  expired=TABLE_NOTICE.replace('11/19/2026','10/20/2026')
  closed=TABLE_NOTICE.replace('<td>Open</td>','<td>Closed</td>')
  for detail in (expired,closed):
   with self.subTest(detail=detail):
    leads,_=self.scan_fixture(detail)
    self.assertEqual(leads,[])

 def test_index_with_multiple_bid_links_never_becomes_a_notice(self):
  index=TABLE_NOTICE+'<a href="/bid/124">Another tree removal bid</a>'
  leads,_=self.scan_fixture(index)
  self.assertEqual(leads,[])

 def test_table_without_bid_number_is_not_an_individual_notice(self):
  leads,_=self.scan_fixture(TABLE_NOTICE.replace('Bid Number:','Reference:'))
  self.assertEqual(leads,[])

 def test_closing_date_time_label_not_publication_date(self):
  self.assertEqual(scan.deadline('Closing Date/Time: 11/19/2026 10:00 AM'),'2026-11-19')
  self.assertEqual(scan.deadline('Publication Date/Time: 11/19/2026'),'')

if __name__=='__main__':
 unittest.main()
