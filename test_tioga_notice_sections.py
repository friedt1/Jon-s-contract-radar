"""Offline isolation regression: no adjacent notice can donate its scope."""
import unittest
from unittest.mock import patch
from tioga_notice_sections import notice_sections, deadline_evidence_status

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

    def test_ambiguous_attachment_urls_are_rejected(self):
        # Browsers, proxies and URL parsers can disagree on backslashes,
        # whitespace and control characters in an href.
        html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                '<a href="/docs/valid.pdf">Valid spec</a>'
                '<a href="/docs/white space.pdf">Whitespace</a>'
                '<a href="/docs/line&#10;break.pdf">Newline</a>'
                '<a href="/docs/back\\slash.pdf">Backslash</a>'
                '<a href="/docs/tab&#9;name.pdf">Tab</a>')
        sections = notice_sections(html, URL)
        self.assertEqual(sections[0]['links'], [
            {'url': 'https://tiogacountyny.com/docs/valid.pdf',
             'label': 'Valid spec'}
        ])

    def test_percent_encoded_ambiguous_attachment_urls_are_rejected(self):
        html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                '<a href="/docs/valid%2Dspec.pdf">Valid encoded hyphen</a>'
                '<a href="/docs/white%20space.pdf">Encoded space</a>'
                '<a href="/docs/line%0Abreak.pdf">Encoded newline</a>'
                '<a href="/docs/back%5cslash.pdf">Encoded backslash</a>'
                '<a href="/docs/tab%09name.pdf">Encoded tab</a>'
                '<a href="/docs/del%7Fname.pdf">Encoded DEL</a>')
        sections = notice_sections(html, URL)
        self.assertEqual(sections[0]['links'], [
            {'url': 'https://tiogacountyny.com/docs/valid%2Dspec.pdf',
             'label': 'Valid encoded hyphen'}
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

    def test_historical_links_do_not_exhaust_valid_attachment_budget(self):
        # A large archive within a notice must not hide a later legitimate spec.
        links = ''.join(
            '<a href="/archive/result-%d.pdf">Bid results</a>' % i
            for i in range(35)
        )
        html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                + links + '<a href="/docs/brush.pdf">Specifications</a>')
        sections = notice_sections(html, URL)
        self.assertEqual(sections[0]['links'], [
            {'url': 'https://tiogacountyny.com/docs/brush.pdf',
             'label': 'Specifications'}
        ])

    def test_official_demolition_notice_h1_subheading_preserves_scope(self):
        # The live Tioga DPW rebid uses an H1 NOTICE TO BIDDERS inside
        # its H3 bid block. This is historical, never a live bid fixture.
        html = """<h2>Bids &amp; RFPs</h2>
        <h3>Bid: 67 Central Ave Demolition Project Rebid</h3>
        <h1>NOTICE TO BIDDERS</h1>
        <p>Demolition and site restoration; due November 13, 2026.</p>
        <a href="/docs/demolition.pdf">Project manual</a>
        <h3>Bid: 2026 Tree Removal Results</h3>
        <a href="/docs/tree-results.pdf">Bid tabulation</a>"""
        sections = notice_sections(html, URL)
        self.assertEqual(len(sections), 1)
        self.assertIn('Demolition and site restoration', sections[0]['text'])
        self.assertNotIn('Tree Removal', sections[0]['text'])
        self.assertEqual(len(sections[0]['links']), 1)

    def test_h1_heading_ends_procurement_section(self):
        html = """
        <h2>Bids &amp; RFPs</h2>
        <h3>Bid: Brush clearing</h3>
        <p>Brush specifications.</p>
        <h1>County News</h1>
        <h3>Bid: Tree Removal 2026</h3>
        <p>Not an official procurement listing.</p>
        <a href="/news/tree.pdf">Unrelated attachment</a>
        """
        sections = notice_sections(html, URL)
        self.assertEqual([s['title'] for s in sections], ['Bid: Brush clearing'])
        self.assertEqual(sections[0]['text'], 'Brush specifications.')
        self.assertEqual(sections[0]['links'], [])

    def test_missing_bids_heading_fails_closed(self):
        html = '<h3>Bid: Tree removal</h3><p>Due tomorrow</p>'
        self.assertEqual(notice_sections(html, URL), [])

    def test_no_fabricated_or_cross_host_links(self):
        html = '<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3><a href="https://other.example/bid.pdf">External</a>'
        sections = notice_sections(html, URL)
        self.assertEqual(len(sections), 1)
        self.assertEqual(sections[0]['links'], [])


    def test_large_archive_does_not_hide_late_current_spec(self):
        # More than the old 300-link scan cap precede a valid attachment.
        archive = ''.join(
            '<a href="/archive/result-%d.pdf">Bid results</a>' % i
            for i in range(350)
        )
        html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                + archive + '<a href="/docs/brush.pdf">Specifications</a>')
        sections = notice_sections(html, URL)
        self.assertEqual(sections[0]['links'], [
            {'url': 'https://tiogacountyny.com/docs/brush.pdf',
             'label': 'Specifications'}
        ])

    def test_more_than_two_thousand_historical_links_do_not_hide_spec(self):
        # Historical archive entries cannot consume the candidate scan budget.
        archive = ''.join(
            '<a href="/archive/result-%d.pdf">Bid results</a>' % i
            for i in range(2100)
        )
        html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                + archive + '<a href="/docs/brush.pdf">Specifications</a>')
        sections = notice_sections(html, URL)
        self.assertEqual(sections[0]['links'], [
            {'url': 'https://tiogacountyny.com/docs/brush.pdf',
             'label': 'Specifications'}
        ])

    def test_section_cap_reports_truncation_without_publishing_extra_sections(self):
        html = '<h2>Bids &amp; RFPs</h2>' + ''.join(
            '<h3>Bid: Test %d</h3><p>Offline fixture</p>' % i
            for i in range(1002)
        )
        diagnostics = {}
        sections = notice_sections(html, URL, diagnostics=diagnostics)
        self.assertEqual(len(sections), 1000)
        self.assertEqual(diagnostics['total_sections'], 1002)
        self.assertEqual(diagnostics['sections_truncated'], 2)
        self.assertEqual(diagnostics['attachments_truncated'], 0)

    def test_missing_documents_diagnostic_excludes_historical_results(self):
        html = ('<h2>Bids &amp; RFPs</h2>'
                '<h3>Bid: Brush clearing</h3><p>No linked documents</p>'
                '<h3>Bid: Tree removal results</h3>'
                '<a href="/docs/tree-results.pdf">Bid results</a>'
                '<h3>Bid: Stump removal</h3>'
                '<a href="https://other.example/spec.pdf">Untrusted host</a>'
                '<h3>Bid: Vegetation management</h3>'
                '<a href="/docs/vegetation.pdf">Specifications</a>')
        diagnostics = {}
        sections = notice_sections(html, URL, diagnostics=diagnostics)
        self.assertEqual(len(sections), 3)
        self.assertEqual(diagnostics['notices_without_documents'], 2)
        self.assertEqual(len(sections[-1]['links']), 1)

    def test_attachment_cap_reports_truncation(self):
        links = ''.join(
            '<a href="/docs/spec-%d.pdf">Specifications</a>' % i
            for i in range(31)
        )
        diagnostics = {}
        sections = notice_sections(
            '<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>' + links,
            URL, diagnostics=diagnostics
        )
        self.assertEqual(len(sections[0]['links']), 30)
        self.assertEqual(diagnostics['sections_truncated'], 0)
        self.assertEqual(diagnostics['attachments_truncated'], 1)

    def test_exactly_thirty_attachments_is_not_truncated(self):
        links = ''.join(
            '<a href="/docs/spec-%d.pdf">Specifications</a>' % i
            for i in range(30)
        )
        diagnostics = {}
        sections = notice_sections(
            '<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>' + links,
            URL, diagnostics=diagnostics
        )
        self.assertEqual(len(sections[0]['links']), 30)
        self.assertEqual(diagnostics['attachments_truncated'], 0)

    def test_nonstandard_https_port_is_not_an_official_attachment(self):
        html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                '<a href="https://tiogacountyny.com:8443/docs/brush.pdf">Alternate port</a>'
                '<a href="https://tiogacountyny.com/docs/brush.pdf">Official host</a>')
        sections = notice_sections(html, URL)
        self.assertEqual(sections[0]['links'], [
            {'url': 'https://tiogacountyny.com/docs/brush.pdf',
             'label': 'Official host'}
        ])

    def test_malformed_port_does_not_abort_other_attachments(self):
        html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                '<a href="https://tiogacountyny.com:bad/docs/brush.pdf">Bad port</a>'
                '<a href="https://tiogacountyny.com:99999/docs/brush.pdf">Out of range</a>'
                '<a href="/docs/brush.pdf">Valid specification</a>')
        sections = notice_sections(html, URL)
        self.assertEqual(sections[0]['links'], [
            {'url': 'https://tiogacountyny.com/docs/brush.pdf',
             'label': 'Valid specification'}
        ])


    def test_malformed_ipv6_authority_does_not_abort_notice(self):
        html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                '<a href="https://[broken/docs/brush.pdf">Broken IPv6 host</a>'
                '<a href="https://[::1]/docs/brush.pdf">Different IPv6 host</a>'
                '<a href="/docs/brush.pdf">Valid specification</a>')
        sections = notice_sections(html, URL)
        self.assertEqual(sections[0]['links'], [
            {'url': 'https://tiogacountyny.com/docs/brush.pdf',
             'label': 'Valid specification'}
        ])

    def test_insecure_index_cannot_authorize_official_attachments(self):
        html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                '<a href="https://tiogacountyny.com/docs/brush.pdf">Specifications</a>')
        self.assertEqual(notice_sections(html,
                         'http://tiogacountyny.com/departments/public-works/'), [])

    def test_malformed_page_authority_fails_closed(self):
        self.assertEqual(notice_sections(
            '<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>',
            'https://[broken/path'), [])


    def test_noncanonical_index_authority_fails_closed(self):
        html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                '<a href="/docs/brush.pdf">Specifications</a>')
        bad_indexes = (
            'https://user@tiogacountyny.com/departments/public-works/',
            'https://user:pass@tiogacountyny.com/departments/public-works/',
            'https://tiogacountyny.com:8443/departments/public-works/',
            'https://tiogacountyny.com:bad/departments/public-works/',
            'https://tiogacountyny.com:99999/departments/public-works/',
            'https://tiogacountyny.com/departments/public-works/?preview=1',
            'https://tiogacountyny.com/departments/public-works/#archive',
        )
        for index in bad_indexes:
            with self.subTest(index=index):
                self.assertEqual(notice_sections(html, index), [])
        self.assertEqual(len(notice_sections(html, URL)), 1)

    def test_caller_controlled_https_host_cannot_authorize_documents(self):
        html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                '<a href="/docs/brush.pdf">Specifications</a>')
        untrusted_indexes = (
            'https://attacker.example/departments/public-works/',
            'https://tiogacountyny.com.evil.example/departments/public-works/',
            'https://www.tiogacountyny.com/departments/public-works/',
            'https://tiogacountyny.com/other-page/',
            'https://TIOGACOUNTYNY.COM/departments/public-works/',
            'https://tiogacountyny.com:443/departments/public-works/',
        )
        for index in untrusted_indexes:
            with self.subTest(index=index):
                self.assertEqual(notice_sections(html, index), [])
        self.assertEqual(len(notice_sections(html, URL)), 1)

    def test_untrusted_index_is_rejected_before_html_parser_runs(self):
        # Untrusted caller URLs must not cause even an offline parse.
        with patch('tioga_notice_sections._Sections', side_effect=AssertionError('parsed')) as parser:
            self.assertEqual(notice_sections('<h2>Bids &amp; RFPs</h2>',
                                             'https://attacker.example/bids'), [])
            self.assertEqual(notice_sections('<h2>Bids &amp; RFPs</h2>',
                                             'https://[broken/path'), [])
            parser.assert_not_called()



class DeadlineEvidenceTest(unittest.TestCase):
    def test_owego_demolition_conflicting_official_deadlines(self):
        # Historical Owego demolition rebid: page 2 PM vs document 11 AM.
        # These are regression evidence, NEVER a live opportunity.
        self.assertEqual(deadline_evidence_status(
            '2026-11-13T14:00:00-05:00',
            '2026-11-13T11:00:00-05:00'), 'conflict')

    def test_same_instant_with_different_offsets_is_consistent(self):
        self.assertEqual(deadline_evidence_status(
            '2026-12-01T11:00:00-05:00',
            '2026-12-01T16:00:00+00:00'), 'consistent')

    def test_missing_invalid_or_timezone_naive_deadline_fails_closed(self):
        for value in (None, '', 'not a date', '2026-11-13T14:00:00'):
            with self.subTest(value=value):
                self.assertEqual(deadline_evidence_status(
                    value, '2026-11-13T11:00:00-05:00'),
                    'verification_required')
                self.assertEqual(deadline_evidence_status(
                    '2026-11-13T11:00:00-05:00', value),
                    'verification_required')


class TiogaInputBoundsTest(unittest.TestCase):
    def test_many_small_tags_exceed_parser_budget_without_partial_results(self):
        diagnostics = {}
        html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                '<a href="/docs/brush.pdf">Specifications</a>'
                + '<span></span>' * 11000)
        self.assertLess(len(html), 2_000_000)
        self.assertEqual(notice_sections(html, URL, diagnostics), [])
        self.assertEqual(diagnostics['source_status'], 'html_parse_budget_exceeded')
        self.assertEqual(diagnostics['total_sections'], 0)

    def test_large_text_node_exceeds_parser_budget_without_partial_results(self):
        diagnostics = {}
        html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                '<p>' + 'x' * 1_000_001 + '</p>'
                '<a href="/docs/brush.pdf">Specifications</a>')
        self.assertEqual(notice_sections(html, URL, diagnostics), [])
        self.assertEqual(diagnostics['source_status'], 'html_parse_budget_exceeded')

    def test_oversized_html_fails_closed_with_diagnostic(self):
        diagnostics = {}
        html = HTML + (' ' * 2_000_001)
        self.assertEqual(notice_sections(html, URL, diagnostics), [])
        self.assertEqual(diagnostics['source_status'], 'html_size_limit_exceeded')
        self.assertEqual(diagnostics['total_sections'], 0)


if __name__ == '__main__':
    unittest.main()
