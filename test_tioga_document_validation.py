"""Offline tests: links and MIME declarations alone do not prove a bid PDF."""
import unittest
from tioga_document_validation import document_response_status as check

GOOD = 'https://tiogacountyny.com/docs/notice.pdf'
PDF = b'%PDF-1.7\n1 0 obj\n'


class DocumentResponseTests(unittest.TestCase):
    def test_valid_pdf_evidence_only(self):
        self.assertEqual(check(GOOD, GOOD, 200, 'application/pdf; charset=binary', PDF),
                         'verified_document_response')

    def test_redirect_must_end_on_official_host(self):
        for final in ('https://evil.example/notice.pdf',
                      'http://tiogacountyny.com/docs/notice.pdf',
                      'https://tiogacountyny.com:8443/docs/notice.pdf',
                      'https://user@tiogacountyny.com/docs/notice.pdf',
                      'https://[broken/docs/notice.pdf'):
            with self.subTest(final=final):
                self.assertEqual(check(GOOD, final, 200, 'application/pdf', PDF),
                                 'untrusted_url')

    def test_response_must_be_real_pdf(self):
        for status, mime, body, expected in (
            (404, 'application/pdf', PDF, 'http_error'),
            (200, 'application/pdf', b'<html>login</html>', 'unsupported_or_mismatched_document'),
            (200, 'text/html', PDF, 'unsupported_or_mismatched_document'),
            (200, 'application/pdf', b'', 'empty_or_invalid_body'),
            (200, 'application/pdf', None, 'empty_or_invalid_body'),
        ):
            with self.subTest(status=status, mime=mime, body=body):
                self.assertEqual(check(GOOD, GOOD, status, mime, body), expected)

    def test_untrusted_requested_url(self):
        self.assertEqual(check('https://evil.example/notice.pdf', GOOD, 200,
                               'application/pdf', PDF), 'untrusted_url')


if __name__ == '__main__':
    unittest.main()
