import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('scanner',Path(__file__).resolve().parent/'scan.py')
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



from unittest.mock import patch

class ExtractionTests(unittest.TestCase):
    def setUp(self):
        clock=patch.object(scanner,'NOW',scanner.dt.datetime(2026,10,28,16,tzinfo=scanner.dt.timezone.utc))
        clock.start();self.addCleanup(clock.stop)
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



class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.clock=patch.object(scanner,'NOW',scanner.dt.datetime(2026,10,28,16,tzinfo=scanner.dt.timezone.utc))
        self.clock.start();self.addCleanup(self.clock.stop)

    def test_deadline_formats(self):
        for text in ('Due date: 2026-11-02','Closing: 11/02/2026','Submission deadline November 2, 2026','Bids received until Nov 2, 2026'):
            with self.subTest(text=text):self.assertEqual(scanner.deadline(text),'2026-11-02')
        self.assertEqual(scanner.deadline('Posted November 2, 2026'),'')

    def test_closed_expired_and_irrelevant(self):
        for text in ('Tree removal bid closed','Tree removal contract awarded','Tree trimming bid canceled','Tree removal bid due 10/27/2026','Right-of-way vacation bid','Grounds maintenance bid','Computer equipment bid'):
            with self.subTest(text=text):self.assertFalse(scanner.eligible(text))
        self.assertTrue(scanner.eligible('Tree trimming bid due 10/28/2026'))
        self.assertEqual(scanner.category('Tree pruning contract'),'Tree trimming')

    def test_broad_portal_needs_local_evidence(self):
        self.assertFalse(scanner.eligible('Harrisburg tree removal bid','PennBid platform'))
        self.assertTrue(scanner.eligible('Bradford County PA forestry mulching bid','PennBid platform'))

    def direct(self,html,details=None,source=None):
        src=source or {'name':'Chemung County bids','url':'https://example.org/bids','mode':'direct_page'}
        def fake(url,binary=False):
            value=(details or {}).get(url,html)
            return (value.encode() if binary else value,'text/html',url)
        with patch.object(scanner,'fetch',side_effect=fake):return scanner.scan_direct(src)

    def test_no_neighbor_listing_contamination(self):
        html='<table><tr><td>Tree removal bid closed</td><td><a href="/bid/old">Details</a></td></tr><tr><td>Computer bid due 12/01/2026</td><td><a href="/bid/new">Details</a></td></tr></table>'
        leads,_=self.direct(html)
        self.assertEqual(leads,[])

    def test_detail_closure_removes_listing(self):
        leads,_=self.direct('<a href="/bid/1">Tree removal bid</a>',{'https://example.org/bid/1':'<h1>Tree removal bid</h1><p>Closed</p>'})
        self.assertEqual(leads,[])

    def test_listing_row_and_nested_procurement(self):
        html='<a href="/procurement">Current bids</a>'
        details={'https://example.org/procurement':'<table><tr><td>Tree removal bid due 11/02/2026</td><td><a href="/bid/1">Details</a></td></tr></table>', 'https://example.org/bid/1':'<h1>Tree removal bid due 11/02/2026</h1>'}
        leads,_=self.direct(html,details)
        self.assertEqual(len(leads),1)
        self.assertEqual(leads[0]['deadline'],'2026-11-02')
        self.assertEqual(leads[0]['url'],'https://example.org/bid/1')

    def test_platform_host_boundary(self):
        self.assertFalse(scanner.allowed_link('https://pennbid.bonfirehub.com/opportunities/1','https://example.org'))
        self.assertFalse(scanner.allowed_link('https://bonfirehub.com.evil.test/1','https://example.org'))
        self.assertFalse(scanner.allowed_link('javascript:alert(1)','https://example.org'))

    def test_archive_navigation_not_scanned(self):
        html='<a href="/Bid-Recordings">Tree removal bid recordings</a><a href="/bid-results">Tree trimming bid results</a>'
        leads,status=self.direct(html)
        self.assertEqual(leads,[]);self.assertIn('0 details checked',status)

    def test_all_configurations_use_direct_and_discovery(self):
        sources=scanner.json.loads(scanner.SOURCES.read_text())
        direct=[s for s in sources if s.get('mode')=='direct_page']
        self.assertEqual(len(sources), 102)
        # New official integrations must not break regression coverage.
        self.assertGreaterEqual(len(direct), 15)
        for src in direct:
            with self.subTest(source=src['name']):
                with patch.object(scanner,'scan_direct',return_value=([], 'direct fetched')) as d, patch.object(scanner,'scan_news',return_value=[]) as n:
                    name,status,leads=scanner.run(src)
                if src['name'] in scanner.UNCONNECTED_PLATFORMS:
                    d.assert_not_called()
                    self.assertIn('direct access required',status)
                else:
                    d.assert_called_once_with(src)
                n.assert_called_once_with(src)
                self.assertEqual(name,src['name']);self.assertIn('indirect RSS ok',status)

    def test_direct_failure_preserves_news_discovery(self):
        with patch.object(scanner,'scan_direct',side_effect=ValueError('bad HTML')),patch.object(scanner,'scan_news',return_value=[{'id':'one'}]):
            _,status,leads=scanner.run({'name':'Test','mode':'direct_page','url':'https://example.org','verified_url':True})
        self.assertIn('direct error',status);self.assertEqual(leads,[{'id':'one'}])

    def test_pdf_success_and_failure(self):
        with patch.object(scanner.subprocess,'run',return_value=scanner.subprocess.CompletedProcess([],0,'Tree removal bid','')):
            self.assertEqual(scanner.pdf_text(b'%PDF'),'Tree removal bid')
        with patch.object(scanner.subprocess,'run',side_effect=FileNotFoundError):
            self.assertEqual(scanner.pdf_text(b'%PDF'),'')

    def test_news_rejects_old_missing_and_future_dates(self):
        items=''.join('<item><title>Tree removal bid</title><link>https://example.org/'+str(i)+'</link><pubDate>'+d+'</pubDate></item>' for i,d in enumerate(('Tue, 27 Oct 2026 12:00:00 GMT','Wed, 01 Jan 2025 12:00:00 GMT','','Thu, 29 Oct 2026 12:00:00 GMT')))
        with patch.object(scanner,'fetch',return_value=('<rss><channel>'+items+'</channel></rss>','application/xml','https://news.google.com')):
            leads=scanner.scan_news({'name':'Chemung County'})
        self.assertEqual(len(leads),1)

    def test_main_102_targets_history_and_website_schema(self):
        import tempfile
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'data').mkdir()
            history=root/'data/history.json'
            history.write_text(json.dumps({'opportunities':{'old':{'id':'old','first_seen':'2026-01-01','last_seen':'2026-01-01'}}}))
            def fake_run(src):
                out={};scanner.add_lead(out,src['name'],'Tree removal bid','https://example.org/bid')
                return src['name'],'indirect RSS ok; 1 candidates',list(out.values())
            with patch.object(scanner,'ROOT',root),patch.object(scanner,'OUT',root/'data/opportunities.json'),patch.object(scanner,'run',side_effect=fake_run):
                scanner.main();scanner.main()
            import validate_output
            (root/'sources.json').write_text(scanner.SOURCES.read_text())
            validate_output.validate(root)
            data=json.loads((root/'data/opportunities.json').read_text())
            hist=json.loads(history.read_text())['opportunities']
            self.assertEqual(len(data['source_status']),103)
            self.assertEqual(data['source_status']['SAM.gov'],'deferred')
            self.assertEqual(len(data['opportunities']),1)
            self.assertIn('old',hist)
            lead=data['opportunities'][0]
            self.assertTrue({'title','summary','location','source','category','published','url','status'}<=lead.keys())
            self.assertEqual(hist[lead['id']]['first_seen'],scanner.NOW.isoformat(timespec='seconds'))

    def test_total_failure_preserves_output(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'opportunities.json';out.write_text('existing')
            with patch.object(scanner,'OUT',out),patch.object(scanner,'run',side_effect=lambda s:(s['name'],'indirect RSS error: URLError',[])):
                with self.assertRaisesRegex(RuntimeError,'All sources failed'):scanner.main()
            self.assertEqual(out.read_text(),'existing')



class RuntimeTests(unittest.TestCase):
    def test_real_pdf_extractor(self):
        import shutil
        if not shutil.which('pdftotext'):self.skipTest('Optional pdftotext not installed')
        objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>']
        stream=b'BT /F1 12 Tf 72 720 Td (Tree removal bid due 11/02/2026) Tj ET'
        objects.append(b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream')
        pdf=b'%PDF-1.4\n';offsets=[0]
        for i,obj in enumerate(objects,1):
            offsets.append(len(pdf));pdf+=str(i).encode()+b' 0 obj\n'+obj+b'\nendobj\n'
        xref=len(pdf);pdf+=b'xref\n0 6\n0000000000 65535 f \n'
        pdf+=b''.join(f'{n:010} 00000 n \n'.encode() for n in offsets[1:])
        pdf+=b'trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n'+str(xref).encode()+b'\n%%EOF'
        text=scanner.pdf_text(pdf)
        self.assertIn('Tree removal bid',text)
        self.assertEqual(scanner.deadline(text),'2026-11-02')

    def test_validator_rejects_missing_target(self):
        import validate_output
        import tempfile,json
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'data').mkdir()
            (root/'sources.json').write_text(scanner.SOURCES.read_text())
            (root/'data/history.json').write_text('{"opportunities":{}}')
            (root/'data/opportunities.json').write_text(json.dumps({'source_status':{'SAM.gov':'deferred'},'opportunities':[]}))
            with self.assertRaisesRegex(ValueError,'102 targets'):validate_output.validate(root)



class IntegrationShapeTests(unittest.TestCase):
    setUp = RegressionTests.setUp
    direct = RegressionTests.direct
    # Synthetic public-page shapes; these are not captured/live provider fixtures.
    def test_list_record_deadlines_are_isolated(self):
        html='<ul><li>Tree removal bid due 10/01/2026 <a href="/bid/old">Details</a></li><li>Tree trimming bid due 11/02/2026 <a href="/bid/new">Details</a></li></ul>'
        leads,_=self.direct(html,{'https://example.org/bid/new':'<h1>Tree trimming bid due 11/02/2026</h1>'})
        self.assertEqual([x['url'] for x in leads],['https://example.org/bid/new'])

    def test_dynamic_portal_reports_incompleteness(self):
        leads,status=self.direct('<div id="app">Enable JavaScript</div>')
        self.assertEqual(leads,[]);self.assertIn('extraction incomplete',status)

    def test_pdf_attachment(self):
        src={'name':'Chemung County bids','url':'https://example.org/bids','mode':'direct_page'}
        def fake(url,binary=False):
            if binary:return b'%PDF fake','application/pdf',url
            return '<a href="/tree-bid.pdf">Tree removal bid</a>','text/html',url
        with patch.object(scanner,'fetch',side_effect=fake),patch.object(scanner,'pdf_text',return_value='Tree removal bid due 11/02/2026'):
            leads,status=scanner.scan_direct(src)
        self.assertEqual(leads[0]['deadline'],'2026-11-02');self.assertIn('1 PDFs checked',status)

    def test_news_uses_query_override_and_local_evidence(self):
        src={'name':'Nationwide owner','discovery_query':'Owner name','require_local_evidence':True}
        xml='<rss><channel><item><title>Dallas tree removal bid</title><link>https://example.org/outside</link><pubDate>Tue, 27 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>'
        with patch.object(scanner,'fetch',return_value=(xml,'application/xml','https://news.google.com')) as fetch:
            self.assertEqual(scanner.scan_news(src),[])
        query=scanner.up.parse_qs(scanner.up.urlparse(fetch.call_args.args[0]).query)['q'][0]
        self.assertIn('"Owner name"',query);self.assertIn('forestry mulching',query)

if __name__=='__main__':unittest.main()
