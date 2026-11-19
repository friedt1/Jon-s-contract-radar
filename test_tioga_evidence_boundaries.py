"""Fail-closed Tioga evidence regressions; fixtures are not live solicitations."""
import unittest
from tioga_notice_sections import (
    OFFICIAL_INDEX_URL, notice_sections, deadline_evidence_status,
)
from tioga_document_validation import document_response_status

class TiogaEvidenceBoundaryTests(unittest.TestCase):
    def test_missing_index_body_fails_closed_with_diagnostics(self):
        for body in (None, b'<h2>Bids & RFPs</h2>', '', '   '):
            with self.subTest(body=body):
                diagnostics = {}
                self.assertEqual(notice_sections(body, OFFICIAL_INDEX_URL, diagnostics), [])
                self.assertEqual(diagnostics['source_status'], 'invalid_or_empty_html')
                self.assertEqual(diagnostics['total_sections'], 0)
                self.assertEqual(diagnostics['notices_without_documents'], 0)


    def test_untrusted_index_cannot_authorize_documents(self):
        html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                '<a href="/docs/brush.pdf">Specifications</a>')
        for url in (
            'http://tiogacountyny.com/departments/public-works/',
            'https://tiogacountyny.com.evil.example/departments/public-works/',
            OFFICIAL_INDEX_URL + '?preview=1',
            OFFICIAL_INDEX_URL + '#bids',
        ):
            with self.subTest(url=url):
                self.assertEqual(notice_sections(html, url), [])

    def test_encoded_path_separator_cannot_become_a_document_link(self):
        html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                '<a href="/docs%2fprivate/notice.pdf">Encoded slash</a>'
                '<a href="/docs/notice.pdf">Official document</a>')
        sections = notice_sections(html, OFFICIAL_INDEX_URL)
        self.assertEqual(len(sections), 1)
        self.assertEqual([link['url'] for link in sections[0]['links']],
                         ['https://tiogacountyny.com/docs/notice.pdf'])

    def test_double_encoded_separators_are_not_document_evidence(self):
        index = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                 '<a href="/docs%252fprivate/specs.pdf">Unsafe attachment</a>'
                 '<a href="/docs/specs.pdf">Official attachment</a>')
        sections = notice_sections(index, OFFICIAL_INDEX_URL)
        self.assertEqual(len(sections), 1)
        self.assertEqual([link['url'] for link in sections[0]['links']],
                         ['https://tiogacountyny.com/docs/specs.pdf'])
        good = 'https://tiogacountyny.com/docs/specs.pdf'
        bad = 'https://tiogacountyny.com/docs%252fprivate/specs.pdf'
        pdf = b'%PDF-1.7\\n%%EOF'
        self.assertEqual(document_response_status(bad, good, 200,
                                                  'application/pdf', pdf),
                         'untrusted_url')
        self.assertEqual(document_response_status(good, bad, 200,
                                                  'application/pdf', pdf),
                         'untrusted_url')

    def test_repeatedly_encoded_separators_are_rejected(self):
        good = 'https://tiogacountyny.com/docs/specs.pdf'
        pdf = b'%PDF-1.7\\n%%EOF'
        for encoded in ('%25252f', '%2525252f', '%25255c', '%252520'):
            with self.subTest(encoded=encoded):
                bad = 'https://tiogacountyny.com/docs' + encoded + 'private/specs.pdf'
                html = ('<h2>Bids &amp; RFPs</h2><h3>Bid: Brush clearing</h3>'
                        '<a href="' + bad + '">Unsafe attachment</a>')
                sections = notice_sections(html, OFFICIAL_INDEX_URL)
                self.assertEqual(len(sections), 1)
                self.assertEqual(sections[0]['links'], [])
                self.assertEqual(document_response_status(bad, good, 200,
                                 'application/pdf', pdf), 'untrusted_url')
                self.assertEqual(document_response_status(good, bad, 200,
                                 'application/pdf', pdf), 'untrusted_url')

    def test_deadline_evidence_requires_independent_aware_agreement(self):
        self.assertEqual(
            deadline_evidence_status('2026-12-01T11:00:00-05:00',
                                     '2026-12-01T16:00:00+00:00'), 'consistent')
        self.assertEqual(
            deadline_evidence_status('2026-12-01T11:00:00-05:00',
                                     '2026-12-02T11:00:00-05:00'), 'conflict')
        for missing in ('', None, 'December 1, 2026', '2026-12-01T11:00:00'):
            with self.subTest(missing=missing):
                self.assertEqual(
                    deadline_evidence_status('2026-12-01T11:00:00-05:00', missing),
                    'verification_required')

    def test_pdf_looking_login_response_is_not_document_evidence(self):
        url = 'https://tiogacountyny.com/docs/specs.pdf'
        self.assertEqual(
            document_response_status(url, url, 200, 'text/html',
                                     b'%PDF-1.7\n%%EOF'),
            'unsupported_or_mismatched_document')
        self.assertEqual(
            document_response_status(url, 'https://login.example/specs.pdf',
                                     200, 'application/pdf', b'%PDF-1.7\n%%EOF'),
            'untrusted_url')

if __name__ == '__main__':
    unittest.main()
