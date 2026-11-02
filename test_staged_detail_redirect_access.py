"""Synthetic staged-access regressions; no real contracts or network requests."""
import unittest

import probe_staged_sources as staged


ENTRY = "https://county.example/Bids.aspx"
SOURCE = {
    "name": "Cortland County",
    "mode": "discovery_pending",
    "candidate_official_url": ENTRY,
    "activation_gate": "Publisher terms review required",
}
LISTING = ('<article><a href="/Bids.aspx?bidID=4">Tree removal</a>'
           '<p>Status: Closed</p></article>')
DETAIL = (b'<h1>Bid Title: Tree removal</h1><p>Bid Number: 4</p>'
          b'<p>Description: Historical notice</p><p>Status: Closed</p>')


def staged_fetch(final, body=DETAIL):
    def fetch(url, binary=False):
        if url == ENTRY:
            return LISTING, "text/html", ENTRY
        return body, "text/html", final
    return fetch


class StagedNoticeRedirectDiagnosticsTests(unittest.TestCase):
    def assert_failed_notice(self, row, state):
        self.assertEqual(row["state"], state)
        self.assertEqual(row["individual_samples_attempted"], 1)
        self.assertEqual(row["individual_samples_confirmed"], 0)
        self.assertEqual(row["individual_sample_failures"][0]["state"], state)
        self.assertFalse(row["individual_notice_retrieved"])
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertNotIn("opportunities", row)

    def test_extension_login_redirects_are_authentication_not_public_bids(self):
        # No password form is necessary when the final destination itself is
        # a login endpoint. Ordinary links to login pages remain harmless.
        for path in ("/Account/Login.aspx?ReturnUrl=%2FBids.aspx",
                     "/account/sign-in.php", "/user/login.html"):
            with self.subTest(path=path):
                final = "https://county.example" + path
                listing_row = staged.probe(SOURCE, fetch=lambda url: (
                    "<h1>Sign in</h1>", "text/html", final))
                self.assertEqual(listing_row["state"],
                                 "listing_authentication_required")
                self.assertFalse(listing_row["listing_retrieved"])
                self.assertFalse(listing_row["direct_monitoring_activated"])
                detail_row = staged.probe(SOURCE, fetch=staged_fetch(
                    final, b"<h1>Sign in</h1>"))
                self.assert_failed_notice(
                    detail_row, "individual_notice_authentication_required")

    def test_unsafe_individual_redirects_fail_closed_before_parsing(self):
        for final, state in (
            ("http://county.example/Bids.aspx?bidID=4",
             "individual_notice_insecure_redirect"),
            ("https://county.example:8443/Bids.aspx?bidID=4",
             "individual_notice_unsafe_redirect"),
            ("https://user:pass@county.example/Bids.aspx?bidID=4",
             "individual_notice_unsafe_redirect"),
            ("https://127.0.0.1/Bids.aspx?bidID=4",
             "individual_notice_unsafe_redirect"),
            ("https://county.example/Bids.aspx?bidID=4%0d",
             "individual_notice_unsafe_redirect"),
        ):
            with self.subTest(final=final):
                row = staged.probe(SOURCE, fetch=staged_fetch(final))
                self.assert_failed_notice(row, state)

    def test_delegated_provider_redirect_requires_authorized_access(self):
        for final, host in (
            ("https://www.bidnetdirect.com/new-york/agency/notice",
             "www.bidnetdirect.com"),
            ("https://procurement.opengov.com/portal/agency/notice",
             "procurement.opengov.com"),
            ("https://pennbid.bonfirehub.com/agency/notice",
             "pennbid.bonfirehub.com"),
        ):
            with self.subTest(host=host):
                row = staged.probe(SOURCE, fetch=staged_fetch(final))
                self.assert_failed_notice(
                    row, "individual_notice_redirected_to_external_provider_access_required")
                self.assertEqual(
                    row["individual_sample_failures"][0]["external_provider_host"], host)

    def test_lookalike_and_unrelated_hosts_are_not_authorized_providers(self):
        for final in (
            "https://www.bidnetdirect.com.attacker.example/notice",
            "https://unrelated.example/notice",
        ):
            with self.subTest(final=final):
                row = staged.probe(SOURCE, fetch=staged_fetch(final))
                self.assert_failed_notice(
                    row, "individual_notice_redirected_off_official_host")
                self.assertNotIn(
                    "external_provider_host", row["individual_sample_failures"][0])

    def test_same_host_changed_bid_identity_still_fails(self):
        row = staged.probe(SOURCE, fetch=staged_fetch(
            "https://county.example/Bids.aspx?bidID=999"))
        self.assert_failed_notice(row, "individual_notice_redirect_or_type_mismatch")

    def test_public_notice_with_login_link_still_confirms_shape_only(self):
        body = DETAIL + b'<a href="/Account/Login.aspx">Vendor sign in</a>'
        row = staged.probe(SOURCE, fetch=staged_fetch(
            "https://county.example/Bids.aspx?bidID=4", body))
        self.assertEqual(row["state"], "notice_format_confirmed_terms_review_required")
        self.assertTrue(row["individual_notice_retrieved"])
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertNotIn("opportunities", row)


if __name__ == "__main__":
    unittest.main()
