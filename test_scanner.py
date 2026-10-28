import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('scanner',Path(__file__).resolve().parents[1]/'scan.py')
scanner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)

class ScannerTests(unittest.TestCase):
    def test_missing_href_does_not_crash(self):
        p=scanner.parse_html('<html><a>Missing link</a><a href="/bids.aspx?bidID=416">Tree services</a></html>')
        self.assertEqual(p.links[0][1],'')
        self.assertEqual(p.links[1][1],'/bids.aspx?bidID=416')
    def test_bid_table_is_parsed(self):
        p=scanner.parse_html('<table><tr><td>Tree removal</td><td><a href="/bids/2">View bid</a></td></tr></table>')
        self.assertIn('Tree removal',p.rows[0])
    def test_categories(self):
        self.assertEqual(scanner.category('Forestry mulching work'),'Land clearing')
        self.assertEqual(scanner.category('right-of-way clearing'),'Vegetation management')
        self.assertIsNone(scanner.category('Buy a new computer'))
    def test_lead_schema(self):
        out={}
        scanner.add_lead(out,'County','Tree removal bid','https://example.org/bid/1','tree removal')
        self.assertEqual(len(out),1)
        self.assertEqual(next(iter(out.values()))['status'],'unverified')
    def test_invalid_lead(self):
        out={}
        scanner.add_lead(out,'County','General notice','https://example.org/notice')
        self.assertEqual(out,{})

if __name__=='__main__':unittest.main()

from unittest.mock import patch

class ExtractionTests(unittest.TestCase):
    def test_direct_link_bid(self):
        src={'name':'Test County','url':'https://example.org/bids','mode':'direct_page'}
        html='<html><a href="/bids.aspx?bidID=416">Tree Services</a></html>'
        def fake_fetch(url,binary=False):
            if binary:return (b'<html>Tree removal bid</html>','text/html',url)
            return (html,'text/html','https://example.org/bids')
        with patch.object(scanner,'fetch',side_effect=fake_fetch):
            leads,status=scanner.scan_direct(src)
        self.assertGreaterEqual(len(leads),1)
        self.assertIn('direct fetched',status)
    def test_news_date_applies_to_own_result(self):
        src={'name':'Test County'}
        xml='''<rss><channel><item><title>Test County tree removal bid</title><description>Bid for tree removal</description><link>https://example.org/one</link><pubDate>Tue, 27 Oct 2026 12:00:00 GMT</pubDate></item><item><title>Test County brush clearing contract</title><description>Brush clearing</description><link>https://example.org/two</link><pubDate>Mon, 26 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>'''
        with patch.object(scanner,'fetch',return_value=(xml,'application/xml','https://news.google.com/rss')):
            leads=scanner.scan_news(src)
        self.assertEqual(len(leads),2)
        dates={x['url']:x['published'] for x in leads}
        self.assertEqual(dates['https://example.org/one'],'2026-10-27')
        self.assertEqual(dates['https://example.org/two'],'2026-10-26')
