"""Historical Erie and Owego examples are regression fixtures, never live bids.

These tests exercise only offline notice isolation. They do not seed the
production scanner, assert current availability, or fetch public websites.
"""
import unittest

from tioga_notice_sections import OFFICIAL_INDEX_URL, notice_sections


class HistoricalOpportunityIsolationTests(unittest.TestCase):
    def test_erie_tree_and_stump_results_not_a_live_notice(self):
        html = (
            '<h2>Bids &amp; RFPs</h2>'
            '<h3>Bid Results: Erie tree and stump removal</h3>'
            '<a href="/docs/erie-tree-stump-results.pdf">Bid results</a>'
        )
        self.assertEqual(notice_sections(html, OFFICIAL_INDEX_URL), [])

    def test_owego_demolition_rebid_results_not_a_live_notice(self):
        html = (
            '<h2>Bids &amp; RFPs</h2>'
            '<h3>RFP: Owego demolition rebid results</h3>'
            '<a href="/docs/owego-demolition.pdf">Specifications</a>'
        )
        self.assertEqual(notice_sections(html, OFFICIAL_INDEX_URL), [])

    def test_result_attachment_cannot_authorize_tree_bid(self):
        html = (
            '<h2>Bids &amp; RFPs</h2>'
            '<h3>Bid: Tree and stump removal</h3>'
            '<a href="/docs/award-results.pdf">Award results</a>'
        )
        diagnostics = {}
        notices = notice_sections(html, OFFICIAL_INDEX_URL, diagnostics)
        self.assertEqual(len(notices), 1)
        self.assertEqual(notices[0]['links'], [])
        self.assertEqual(diagnostics['notices_without_documents'], 1)


if __name__ == '__main__':
    unittest.main()
