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
        self.assertNotIn('November 13', sections[1]['text'])
        self.assertEqual(len(sections[1]['links']), 1)

    def test_no_fabricated_or_cross_host_links(self):
        html = '<h3>Bid: Brush clearing</h3><a href="https://other.example/bid.pdf">External</a>'
        sections = notice_sections(html, URL)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]['links'], [])


if __name__ == '__main__':
    unittest.main()
