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

    def test_empty_and_fragment_links_are_not_documents(self):
        html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                '<a>Missing href</a><a href="">Empty href</a>'
                '<a href="#details">Page anchor</a>'
                '<a href="/documents/brush.pdf">Actual document</a>')
        sections = notice_sections(html, URL)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]['links'], [
            {'url': 'https://tiogacountyny.com/documents/brush.pdf',
             'label': 'Actual document'}
        ])

    def test_same_page_and_query_only_links_are_not_documents(self):
        html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                '<a href="?download=1">Query-only index link</a>'
                '<a href="/departments/public-works/">Index link</a>'
                '<a href="/departments/public-works/?file=brush.pdf">Index query</a>'
                '<a href="/docs/brush.pdf#page=2">Fragment link</a>'
                '<a href="/docs/brush.pdf">Actual specification</a>')
        sections = notice_sections(html, URL)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]['links'], [
            {'url': 'https://tiogacountyny.com/docs/brush.pdf',
             'label': 'Actual specification'}
        ])

    def test_notice_headings_outside_bid_section_are_ignored(self):
        html = """
        <h2>News</h2>
        <h3>Bid: Tree Removal 2026</h3>
        <p>Not an official procurement notice.</p>
        <h2>Bids &amp; RFPs</h2>
        <h3>Bid: Brush clearing</h3>
        <p>Current section text.</p>
        <h2>Archived News</h2>
        <h3>Bid: Tree Removal 2025</h3>
        <a href="/archive/tree.pdf">Historical document</a>
        """
        sections = notice_sections(html, URL)
        self.assertEqual([s['title'] for s in sections], ['Bid: Brush clearing'])
        self.assertNotIn('Tree Removal', sections[0]['text'])
        self.assertEqual(sections[0]['links'], [])

    def test_h4_non_bid_heading_ends_previous_notice(self):
        html = """
        <h2>Bids &amp; RFPs</h2>
        <h3>Bid: Overhead Door Construction</h3>
        <p>Door construction only.</p>
        <h4>Historical Tree Removal Results</h4>
        <p>Tree removal bid results from a previous year.</p>
        <a href="/archive/trees.pdf">Historical trees</a>
        """
        sections = notice_sections(html, URL)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]['text'], 'Door construction only.')
        self.assertEqual(sections[0]['links'], [])

    def test_results_attachment_inside_current_notice_is_not_a_live_document(self):
        html = """
        <h2>Bids &amp; RFPs</h2>
        <h3>Bid: Brush clearing</h3>
        <p>Current bid specifications.</p>
        <a href="/docs/brush-specs.pdf">Specifications</a>
        <a href="/docs/tree-results.pdf">Historical tree results</a>
        <a href="/docs/award.pdf">Award notice</a>
        <a href="/docs/old.pdf">2025 Bid Tabulation</a>
        """
        sections = notice_sections(html, URL)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]['links'], [
            {'url': 'https://tiogacountyny.com/docs/brush-specs.pdf',
             'label': 'Specifications'}
        ])

    def test_attachment_labels_cannot_inject_tree_scope_or_deadline(self):
        html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Door construction</h3>'
                '<p>Due December 1, 2026. Door installation only.</p>'
                '<a href="/docs/door.pdf">Specifications</a>'
                '<a href="/docs/old.pdf">Tree removal results due tomorrow</a>')
        sections = notice_sections(html, URL)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]['text'],
                         'Due December 1, 2026. Door installation only.')
        self.assertEqual(len(sections[0]['links']), 1)
        self.assertEqual(sections[0]['links'][0]['label'], 'Specifications')

    def test_duplicate_attachment_links_are_not_repeated(self):
        html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                '<a href="/docs/brush.pdf">Specifications</a>'
                '<a href="https://tiogacountyny.com/docs/brush.pdf">Download again</a>'
                '<h3>Bid: Stump removal</h3>'
                '<a href="/docs/brush.pdf">Separate notice attachment</a>')
        sections = notice_sections(html, URL)
        self.assertEqual(len(sections), 2)
        self.assertEqual(sections[0]['links'], [
            {'url': 'https://tiogacountyny.com/docs/brush.pdf',
             'label': 'Specifications'}
        ])
        self.assertEqual(len(sections[1]['links']), 1)

    def test_missing_bids_heading_fails_closed(self):
        html = '<h3>Bid: Tree removal</h3><p>Due tomorrow</p>'
        self.assertEqual(notice_sections(html, URL), [])

    def test_no_fabricated_or_cross_host_links(self):
        html = '<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3><a href="https://other.example/bid.pdf">External</a>'
        sections = notice_sections(html, URL)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]['links'], [])


if __name__ == '__main__':
    unittest.main()
