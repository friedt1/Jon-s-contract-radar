"""Offline isolation regression: no adjacent notice can donate its scope."""
import unittest
from tioga_notice_sections import notice_sections

URL = 'https://tiogacountyny.com/departments/public-works/'
HTML = """
<h2>Bids & RFPs</h2>
<h3>Bid: 67 Central Ave Demolition Rebid</h3>
<p>Sealed bids due November 13, 2026 at 2:00 PM. Demolition only.</p>
<a href="/media/demolition.pdf">Bid specifications</a>
<h3>Bid: Public Safety Building Utility Roll-up Door</h3>
<p>Due December 1, 2026 at 11 AM. Door construction only.</p>
<a href="/media/door.pdf">Specifications</a>
<h3>Bid: Tree Removal 2026 Bid Results</h3>
<a href="/media/tree-results.pdf">Bid results PDF</a>
<h2>Other department information</h2>
<a href="/media/unrelated.pdf">Other link</a>
"""


class TiogaSectionsTest(unittest.TestCase):
    def test_sections_are_isolated_and_results_excluded(self):
        sections = notice_sections(HTML, URL)
        self.assertEqual(len(sections), 2)
        self.assertIn('November 13', sections[0]['text'])
        self.assertNotIn('December 1', sections[0]['text'])
        self.assertNotIn('tree', sections[0]['text'].lower())
        self.assertEqual(len(sections[0]['links']), 1)
        self.assertEqual(sections[0]['links'][0]['url'], 'https://tiogacountyny.com/media/demolition.pdf')
        self.assertIn('December 1', sections[1]['text'])
        self.assertNotIn('Tree Removal', sections[1]['text'])
        self.assertNotIn('Other department information', sections[1]['text'])
        self.assertNotIn('Bid: Public Safety', sections[0]['text'])
        self.assertNotIn('November 13', sections[1]['text'])
        self.assertEqual(len(sections[1]['links']), 1)

    def test_official_notice_order_and_historical_attachment_isolation(self):
        # Synthetic HTML in the order observed on the official DPW page
        # on 2026-11-14; paths are fixtures, not verified live documents.
        html = """
        <h2>Bids &amp; RFPs</h2>
        <h3>Bid: Public Safety Building Utility Roll-up Door Construction Project</h3>
        <p>Sealed bids due December 1, 2026 at 11:00 AM.</p>
        <a href="/fixture/door.pdf">Door specifications</a>
        <h3>Bid: 67 Central Ave Demolition Project Rebid</h3>
        <p>Sealed bids due November 13, 2026 at 2:00 PM.</p>
        <a href="/fixture/demolition.pdf">Demolition specifications</a>
        <h3>Bid: 2026 Snow Sand Results</h3>
        <a href="/fixture/sand-results.pdf">Bid results</a>
        <h3>Bid: 2026 April Commodities Bid Results II</h3>
        <a href="/fixture/tree-results.pdf">Tree Removal 2026 Bid Results</a>
        <h2>Other department information</h2>
        """
        sections = notice_sections(html, URL)
        self.assertEqual(len(sections), 2)
        self.assertIn('Roll-up Door', sections[0]['title'])
        self.assertIn('December 1', sections[0]['text'])
        self.assertNotIn('Demolition', sections[0]['text'])
        self.assertNotIn('Tree Removal', sections[0]['text'])
        self.assertIn('Demolition', sections[1]['title'])
        self.assertIn('November 13', sections[1]['text'])
        self.assertNotIn('December 1', sections[1]['text'])
        self.assertNotIn('Tree Removal', sections[1]['text'])
        self.assertTrue(all('results' not in link['url'] for section in sections for link in section['links']))

    def test_no_fabricated_or_cross_host_links(self):
        html = '<h3>Bid: Brush clearing</h3><a href="https://other.example/bid.pdf">External</a>'
        sections = notice_sections(html, URL)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]['links'], [])


if __name__ == '__main__':
    unittest.main()
