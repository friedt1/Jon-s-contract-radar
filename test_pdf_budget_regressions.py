"""Offline PDF-budget prioritization regressions; no live notices or network calls."""
import unittest
import scan


class PdfBudgetPriorityTests(unittest.TestCase):
    def test_current_year_pdf_beats_archived_year(self):
        current = scan.pdf_listing_recency(
            'Tree and stump removal bid PDF',
            'https://county.example/bids/2026/tree-removal.pdf', 2026)
        old = scan.pdf_listing_recency(
            'Tree and stump removal bid PDF',
            'https://county.example/bids/2021/tree-removal.pdf', 2026)
        self.assertGreater(current, old)

    def test_opaque_document_id_does_not_imply_year(self):
        self.assertEqual(0, scan.pdf_listing_recency(
            'Bid PDF', 'https://county.example/DocumentCenter/View/2026', 2026))

    def test_query_year_does_not_imply_publication_year(self):
        self.assertEqual(0, scan.pdf_listing_recency(
            'Bid PDF', 'https://county.example/DocumentCenter/View/4321?year=2026', 2026))

    def test_row_year_is_only_priority_hint(self):
        self.assertEqual(3, scan.pdf_listing_recency(
            'Download PDF', 'https://county.example/media/abc123', 2026,
            context='2026 tree removal bid'))
        self.assertFalse(scan.deadline('2026 tree removal bid'))

    def test_archived_award_is_not_a_live_bid(self):
        self.assertTrue(scan.published_result_link('Tree removal bid results'))
        self.assertTrue(scan.excluded_url('https://county.example/bid-results/2026.pdf'))

    def test_provider_link_cannot_be_fetched_as_same_host_detail(self):
        origin = 'https://county.example/Bids.aspx'
        portal = 'https://vendor.bidnetdirect.com/solicitations/123'
        self.assertTrue(scan.provider_link(portal))
        self.assertFalse(scan.allowed_link(portal, origin))

    def test_unrelated_demolition_is_not_tree_work(self):
        self.assertIsNone(scan.category('Owego demolition of vacant structure; tree removal by others'))

    def test_erie_tree_and_stump_scope_is_tree_work(self):
        self.assertEqual('Tree removal', scan.category('Erie County tree and stump removal bid'))


if __name__ == '__main__':
    unittest.main()
