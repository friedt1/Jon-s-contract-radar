"""Offline staged-source probes: no real site or opportunity is asserted."""
import unittest
from urllib.error import HTTPError
from unittest.mock import Mock

import probe_staged_sources as staged
import robots_policy


ENTRY = "https://county.example/Bids.aspx"
SOURCE = {
    "name": "Cortland County",
    "mode": "discovery_pending",
    "candidate_official_url": ENTRY,
    "activation_gate": "Terms review",
}


def listing():
    return ('<article><a href="/Bids.aspx?bidID=4">Tree removal bid</a>'
            '<p>Status: Closed</p></article>')


def detail():
    return ('<h1>Bid Title: Tree removal</h1><p>Bid Number: 4</p>'
            '<p>Description: Historical removal notice.</p><p>Status: Closed</p>')


class StagedProbeTests(unittest.TestCase):
    def test_historical_notice_proves_shape_not_live_opportunity(self):
        calls = []
        def fetch(url, binary=False):
            calls.append(url)
            if url == ENTRY:
                return listing(), "text/html", url
            return detail().encode(), "text/html", url
        result = staged.build([SOURCE], fetch=fetch, now=staged.dt.datetime(
            2026, 10, 29, tzinfo=staged.dt.timezone.utc))
        row = result["probes"][0]
        self.assertEqual(row["state"], "notice_format_confirmed_terms_review_required")
        self.assertTrue(row["individual_notice_retrieved"])
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertEqual(row["sample_notice_status"], "closed")
        self.assertEqual(len(calls), 2)
        self.assertNotIn("opportunities", result)

    def test_listing_detail_status_conflict_requires_review(self):
        # An old "Open" listing can coexist with a closed individual notice,
        # or a detail can appear open while its listing says closed.
        for listed, detailed in (("Open", "Closed"), ("Closed", "Open")):
            with self.subTest(listed=listed, detailed=detailed):
                html = ('<article><a href="/Bids.aspx?bidID=4">Tree removal</a>'
                        f'<p>Status: {listed}</p><p>Closes: 11/17/2026 10:00 AM</p>'
                        '</article>')
                notice = ('<h1>Bid Title: Tree removal</h1><p>Bid Number: 4</p>'
                          '<p>Description: Removal work</p>'
                          f'<p>Status: {detailed}</p>'
                          '<p>Closing Date/Time: 11/17/2026 10:00 AM</p>')

                def fetch(url, binary=False):
                    if url == ENTRY:
                        return html, "text/html", url
                    return notice.encode(), "text/html", url

                row = staged.probe(SOURCE, fetch=fetch, now=staged.dt.datetime(
                    2026, 10, 29, tzinfo=staged.dt.timezone.utc))
                self.assertEqual(row["state"], "notice_format_confirmed_terms_review_required")
                self.assertEqual(row["sample_notice_listing_status"], listed.lower())
                self.assertEqual(row["sample_notice_status"], detailed.lower())
                self.assertTrue(row["sample_notice_status_conflict"])
                self.assertEqual(row["sample_notice_temporal_evidence"],
                                 "conflicting_status_unverified")
                self.assertFalse(row["direct_monitoring_activated"])

    def test_agreeing_status_does_not_create_false_conflict(self):
        row = staged.probe(SOURCE, fetch=lambda url, binary=False: (
            (listing(), "text/html", url) if url == ENTRY else
            (detail().encode(), "text/html", url)
        ))
        self.assertFalse(row["sample_notice_status_conflict"])
        self.assertEqual(row["sample_notice_listing_status"], "closed")
        self.assertEqual(row["sample_notice_temporal_evidence"], "closed_or_awarded")

    def test_closed_and_awarded_are_not_false_availability_conflicts(self):
        html = ('<article><a href="/Bids.aspx?bidID=4">Tree removal</a>'
                '<p>Status: Closed</p></article>')
        notice = ('<h1>Bid Title: Tree removal</h1><p>Bid Number: 4</p>'
                  '<p>Description: Removal work</p><p>Status: Awarded</p>')

        def fetch(url, binary=False):
            return ((html, "text/html", url) if url == ENTRY else
                    (notice.encode(), "text/html", url))

        row = staged.probe(SOURCE, fetch=fetch)
        self.assertEqual(row["sample_notice_status"], "awarded")
        self.assertFalse(row["sample_notice_status_conflict"])
        self.assertEqual(row["sample_notice_temporal_evidence"], "closed_or_awarded")

    def test_robots_blocked_never_fetches_notice(self):
        fetch = Mock(side_effect=robots_policy.RobotsDenied("disallowed"))
        row = staged.probe(SOURCE, fetch=fetch)
        self.assertEqual(row["state"], "listing_robots_blocked")
        self.assertFalse(row["listing_retrieved"])
        self.assertEqual(fetch.call_count, 1)

    def test_no_bidid_is_not_marked_as_live_adapter(self):
        def fetch(url, binary=False):
            return "<p>Purchasing office</p>", "text/html", url
        row = staged.probe(SOURCE, fetch=fetch)
        self.assertEqual(row["state"], "listing_reachable_no_bidid_records")
        self.assertFalse(row["direct_monitoring_activated"])

    def test_non_civicplus_requires_separate_adapter(self):
        other = dict(SOURCE, name="Allegany County")
        row = staged.probe(other, fetch=lambda url: ("<h1>County bids</h1>", "text/html", url))
        self.assertEqual(row["state"], "listing_reachable_adapter_required")

    def test_official_listing_redirect_to_provider_requires_adapter(self):
        # A public county bids URL can redirect directly to a hosted provider.
        # This is not evidence of permission or a working per-notice feed.
        source = dict(SOURCE, name="Ontario County")
        calls = []
        def fetch(url, binary=False):
            calls.append(url)
            return "<h1>Solicitations</h1>", "text/html", (
                "https://procurement.opengov.com/portal/agency")
        row = staged.probe(source, fetch=fetch)
        self.assertEqual(row["state"],
                         "listing_redirected_to_external_provider_access_required")
        self.assertEqual(row["external_provider_host"], "procurement.opengov.com")
        self.assertFalse(row["listing_retrieved"])
        self.assertFalse(row["individual_notice_retrieved"])
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertEqual(calls, [ENTRY])

    def test_same_host_login_redirect_is_not_a_public_bid_listing(self):
        for path in ("/Account/Login?ReturnUrl=%2FBids.aspx",
                     "/sign-in?return=%2FBids.aspx"):
            with self.subTest(path=path):
                row = staged.probe(SOURCE, fetch=lambda url: (
                    "<h1>Sign in</h1>", "text/html",
                    "https://county.example" + path))
                self.assertEqual(row["state"], "listing_authentication_required")
                self.assertFalse(row["listing_retrieved"])
                self.assertFalse(row["individual_notice_retrieved"])
                self.assertFalse(row["direct_monitoring_activated"])

    def test_same_url_login_form_requires_authentication(self):
        login = ('<html><title>Sign In - County Procurement</title>'
                 '<form><input type="password" name="password"></form></html>')
        row = staged.probe(SOURCE, fetch=lambda url: (login, "text/html", url))
        self.assertEqual(row["state"], "listing_authentication_required")
        self.assertFalse(row["listing_retrieved"])
        # An ordinary public bids page may link to a login area. Do not
        # misclassify it as a login-only page without an actual form.
        public = ('<h1>County bids</h1><a href="/Account/Login">Log in</a>')
        other = dict(SOURCE, name="Allegany County")
        row = staged.probe(other, fetch=lambda url: (public, "text/html", url))
        self.assertEqual(row["state"], "listing_reachable_adapter_required")
        self.assertTrue(row["listing_retrieved"])

    def test_https_to_http_downgrade_is_not_verified_listing(self):
        row = staged.probe(SOURCE, fetch=lambda url: (
            "<h1>County bids</h1>", "text/html", "http://county.example/Bids.aspx"))
        self.assertEqual(row["state"], "listing_insecure_redirect")
        self.assertFalse(row["listing_retrieved"])
        self.assertFalse(row["direct_monitoring_activated"])

    def test_unrelated_or_lookalike_listing_redirect_is_not_provider(self):
        source = dict(SOURCE, name="Ontario County")
        for target in ("https://other.example/bids",
                       "https://procurement.opengov.com.evil.example/bids"):
            with self.subTest(target=target):
                row = staged.probe(source, fetch=lambda url: (
                    "<h1>Solicitations</h1>", "text/html", target))
                self.assertEqual(row["state"], "listing_redirected_off_official_host")
                self.assertNotIn("external_provider_host", row)
                self.assertFalse(row["direct_monitoring_activated"])

    def test_opengov_delegation_requires_provider_access(self):
        other = dict(SOURCE, name="Ontario County")
        row = staged.probe(other, fetch=lambda url: (
            "<h1>Current bids are posted on OpenGov</h1>", "text/html", url))
        self.assertEqual(row["state"],
                         "listing_reachable_external_provider_access_required")
        self.assertFalse(row["individual_notice_retrieved"])
        self.assertFalse(row["direct_monitoring_activated"])

    def test_labeled_outbound_bid_portal_is_access_required_not_adapter_ready(self):
        other = dict(SOURCE, name="Ontario County")
        for host in ("procurement.opengov.com", "pennbid.bonfirehub.com",
                     "www.bidnetdirect.com", "www.publicpurchase.com"):
            with self.subTest(host=host):
                html = ('<h1>Purchasing</h1><a href="https://' + host +
                        '/agency">View Bids & RFPs</a>')
                row = staged.probe(other, fetch=lambda url: (html, "text/html", url))
                self.assertEqual(row["state"],
                                 "listing_reachable_external_provider_access_required")
                self.assertFalse(row["direct_monitoring_activated"])
                self.assertFalse(row["individual_notice_retrieved"])

    def test_unrelated_or_lookalike_portal_link_does_not_claim_delegation(self):
        other = dict(SOURCE, name="Ontario County")
        for html in (
            '<h1>Purchasing</h1><a href="https://procurement.opengov.com/">Privacy policy</a>',
            '<h1>Purchasing</h1><a href="https://opengov.com.evil.example/bids">View Bids</a>',
        ):
            with self.subTest(html=html):
                row = staged.probe(other, fetch=lambda url: (html, "text/html", url))
                self.assertNotEqual(row["state"],
                                    "listing_reachable_external_provider_access_required")
                self.assertFalse(row["direct_monitoring_activated"])

    def test_outbound_link_diagnostics_reject_unsafe_destinations(self):
        # Synthetic links only. A fetched agency homepage must not promote
        # private, malformed or encoded-control links to provider/PDF evidence.
        for href in (
            "https://127.0.0.1/notice.pdf",
            "https://0x7f.0.0.1/notice.pdf",
            "https://bids.internal/notice.pdf",
            "https://county.example:8443/notice.pdf",
            "https://user:pass@county.example/notice.pdf",
            "https://cdn.example/notice%0aInjected.pdf",
            "https://procurement.opengov.com/portal?return=%0d",
            "https://procurement.opengov.com/portal#%09",
            "http://cdn.example/notice.pdf",
        ):
            with self.subTest(href=href):
                self.assertIsNone(staged._safe_link(ENTRY, href))
        self.assertEqual(
            staged._safe_link(ENTRY, "/bid-packet.pdf#page=2").hostname,
            "county.example")
        self.assertEqual(
            staged._safe_link(
                ENTRY,
                "https://cdn.example/notice%20packet.pdf?X-Amz-Signature=abc"
            ).hostname, "cdn.example")

    def test_unsafe_outbound_links_do_not_create_false_provider_or_pdf_evidence(self):
        source = dict(SOURCE, name="Ontario County")
        html = (
            '<h1>Purchasing bids</h1>'
            '<a href="https://127.0.0.1/notice.pdf">Bid packet</a>'
            '<a href="https://procurement.opengov.com/portal?return=%0a">'
            'View Bids</a>'
        )
        row = staged.probe(source, fetch=lambda url: (html, "text/html", url))
        self.assertEqual(row["state"], "listing_reachable_adapter_required")
        self.assertNotIn("off_host_pdf_hosts_unverified", row)
        self.assertFalse(row["direct_monitoring_activated"])

    def test_listing_http_failures_are_not_generic_errors(self):
        for code, state in ((401, "listing_authentication_required"),
                            (403, "listing_access_forbidden"),
                            (404, "listing_not_found"),
                            (429, "listing_rate_limited"),
                            (503, "listing_server_error")):
            with self.subTest(code=code):
                error = HTTPError(ENTRY, code, "blocked", None, None)
                row = staged.probe(SOURCE, fetch=Mock(side_effect=error))
                self.assertEqual(row["state"], state)
                self.assertEqual(row["http_status"], code)
                self.assertFalse(row["listing_retrieved"])
                self.assertFalse(row["direct_monitoring_activated"])

    def test_individual_http_failures_are_not_generic_errors(self):
        for code, state in ((401, "individual_notice_authentication_required"),
                            (403, "individual_notice_access_forbidden"),
                            (429, "individual_notice_rate_limited")):
            with self.subTest(code=code):
                def fetch(url, binary=False):
                    if url == ENTRY:
                        return listing(), "text/html", url
                    raise HTTPError(url, code, "blocked", None, None)
                row = staged.probe(SOURCE, fetch=fetch)
                self.assertEqual(row["state"], state)
                self.assertEqual(row["individual_sample_failures"][0]["http_status"], code)
                self.assertFalse(row["individual_notice_retrieved"])
                self.assertFalse(row["direct_monitoring_activated"])

    def test_individual_notice_login_wall_is_not_confirmed_notice(self):
        # A listing may be public even when each notice is login-gated.
        login = (b'<html><h1>Sign In</h1><form>'
                 b'<input type="password" name="password"></form></html>')
        for final in (ENTRY.replace("Bids.aspx", "Bids.aspx?bidID=4"),
                      "https://county.example/Account/Login?ReturnUrl=%2FBids.aspx"):
            with self.subTest(final=final):
                def fetch(url, binary=False):
                    if url == ENTRY:
                        return listing(), "text/html", url
                    return login, "text/html", final
                row = staged.probe(SOURCE, fetch=fetch)
                self.assertEqual(row["state"], "individual_notice_authentication_required")
                self.assertFalse(row["individual_notice_retrieved"])
                self.assertFalse(row["direct_monitoring_activated"])
                self.assertEqual(row["individual_samples_attempted"], 1)

    def test_public_individual_notice_with_login_link_remains_parseable(self):
        def fetch(url, binary=False):
            if url == ENTRY:
                return listing(), "text/html", url
            return (detail() + '<a href="/Account/Login">Sign In</a>').encode(), "text/html", url
        row = staged.probe(SOURCE, fetch=fetch)
        self.assertEqual(row["state"], "notice_format_confirmed_terms_review_required")
        self.assertTrue(row["individual_notice_retrieved"])
        self.assertFalse(row["direct_monitoring_activated"])

    def test_fetcher_blocked_redirect_is_not_generic_listing_error(self):
        for message, state in (
            ("cross-host redirect requires an approved source adapter", "listing_redirect_blocked"),
            ("HTTPS downgrade redirect", "listing_insecure_redirect"),
        ):
            with self.subTest(message=message):
                row = staged.probe(SOURCE, fetch=Mock(side_effect=staged.scan.UnsafeRedirect(message)))
                self.assertEqual(row["state"], state)
                self.assertFalse(row["listing_retrieved"])
                self.assertFalse(row["direct_monitoring_activated"])

    def test_fetcher_blocked_detail_redirect_is_not_generic_fetch_error(self):
        for message, state in (
            ("redirect changed solicitation identity", "individual_notice_redirect_blocked"),
            ("HTTPS downgrade redirect", "individual_notice_insecure_redirect"),
        ):
            with self.subTest(message=message):
                def fetch(url, binary=False):
                    if url == ENTRY:
                        return listing(), "text/html", url
                    raise staged.scan.UnsafeRedirect(message)
                row = staged.probe(SOURCE, fetch=fetch)
                self.assertEqual(row["state"], state)
                self.assertEqual(row["individual_sample_failures"][0]["state"], state)
                self.assertFalse(row["individual_notice_retrieved"])
                self.assertFalse(row["direct_monitoring_activated"])

    def test_future_deadline_sample_precedes_stale_open_notice(self):
        html = (
            '<article><a href="/Bids.aspx?bidID=4">Old tree bid</a>'
            '<p>Status: Open</p><p>Closes: 10/01/2026 10:00 AM</p></article>'
            '<article><a href="/Bids.aspx?bidID=5">Future tree bid</a>'
            '<p>Status: Open</p><p>Closes: 11/15/2026 10:00 AM</p></article>'
        )
        calls = []
        def fetch(url, binary=False):
            calls.append(url)
            if url == ENTRY:
                return html, "text/html", url
            return detail().encode(), "text/html", url
        row = staged.probe(SOURCE, fetch=fetch, now=staged.dt.datetime(
            2026, 10, 29, 18, tzinfo=staged.dt.timezone.utc))
        self.assertEqual(row["individual_records_discovered"], 2)
        self.assertEqual(row["individual_samples_attempted"], 1)
        self.assertIn("bidID=5", row["sample_notice_url"])
        self.assertEqual(len(calls), 2)
        self.assertFalse(row["direct_monitoring_activated"])

    def test_redirect_to_homepage_does_not_prove_individual_notice(self):
        def fetch(url, binary=False):
            if url == ENTRY:
                return listing(), "text/html", url
            return detail().encode(), "text/html", ENTRY
        row = staged.probe(SOURCE, fetch=fetch)
        self.assertEqual(row["state"], "individual_notice_redirect_or_type_mismatch")
        self.assertFalse(row["individual_notice_retrieved"])

    def test_detail_robots_denial_is_distinct_from_listing_denial(self):
        def fetch(url, binary=False):
            if url == ENTRY:
                return listing(), "text/html", url
            raise robots_policy.RobotsDenied("detail disallowed")
        row = staged.probe(SOURCE, fetch=fetch)
        self.assertEqual(row["state"], "individual_notice_robots_blocked")
        self.assertTrue(row["listing_retrieved"])
        self.assertFalse(row["individual_notice_retrieved"])

    def test_no_staged_sources_does_not_create_false_coverage(self):
        result = staged.build([{"name":"Other","mode":"discovery_pending"}],fetch=Mock())
        self.assertEqual(result["staged_entrypoints"],0)
        self.assertEqual(result["probes"],[])


    def test_broken_first_notice_retries_next_without_publishing(self):
        listing = ('<article><a href="/Bids.aspx?bidID=4">Old tree removal</a></article>'
                   '<article><a href="/Bids.aspx?bidID=5">Tree removal</a></article>')
        calls = []
        def fetch(url, binary=False):
            calls.append(url)
            if url == ENTRY:
                return listing, "text/html", url
            if "bidID=4" in url:
                raise OSError("historical notice missing")
            return detail().encode(), "text/html", url

        result = staged.build([SOURCE], fetch=fetch)
        row = result["probes"][0]
        self.assertEqual(row["state"], "notice_format_confirmed_terms_review_required")
        self.assertEqual(row["individual_records_discovered"], 2)
        self.assertEqual(row["individual_samples_attempted"], 2)
        self.assertEqual(row["individual_sample_failures"][0]["state"],
                         "individual_notice_fetch_error")
        self.assertEqual(row["individual_sample_failures"][0]["error_type"], "OSError")
        self.assertTrue(row["sample_notice_url"].endswith("bidID=5"))
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertNotIn("opportunities", result)
        self.assertEqual(len(calls), 3)

    def test_missing_fields_and_robots_denial_can_fall_back(self):
        listing = ('<article><a href="/Bids.aspx?bidID=4">Tree bid</a></article>'
                   '<article><a href="/Bids.aspx?bidID=5">Tree bid</a></article>'
                   '<article><a href="/Bids.aspx?bidID=6">Tree bid</a></article>')
        def fetch(url, binary=False):
            if url == ENTRY:
                return listing, "text/html", url
            if "bidID=4" in url:
                raise robots_policy.RobotsDenied("notice path denied")
            if "bidID=5" in url:
                return b"<h1>County purchasing homepage</h1>", "text/html", url
            return detail().encode(), "text/html", url

        row = staged.probe(SOURCE, fetch=fetch)
        self.assertEqual(row["state"], "notice_format_confirmed_terms_review_required")
        self.assertEqual(row["individual_samples_attempted"], 3)
        self.assertEqual([x["state"] for x in row["individual_sample_failures"]],
                         ["individual_notice_robots_blocked",
                          "individual_notice_fields_missing"])
        self.assertTrue(row["sample_notice_url"].endswith("bidID=6"))
        self.assertFalse(row["direct_monitoring_activated"])

    def test_bounded_failures_do_not_fetch_fourth_notice(self):
        listing = "".join(
            f'<article><a href="/Bids.aspx?bidID={n}">Tree removal</a></article>'
            for n in range(4, 8)
        )
        calls = []
        def fetch(url, binary=False):
            calls.append(url)
            if url == ENTRY:
                return listing, "text/html", url
            raise OSError("notice unavailable")

        row = staged.probe(SOURCE, fetch=fetch)
        self.assertEqual(row["state"], "individual_notice_fetch_error")
        self.assertEqual(row["individual_records_discovered"], 4)
        self.assertEqual(row["individual_samples_attempted"], staged.MAX_SAMPLE_DETAILS)
        self.assertEqual(len(row["individual_sample_failures"]), staged.MAX_SAMPLE_DETAILS)
        self.assertEqual(len(calls), staged.MAX_SAMPLE_DETAILS + 1)
        self.assertFalse(row["individual_notice_retrieved"])
        self.assertFalse(row["direct_monitoring_activated"])

    def test_mixed_sample_failures_are_reported_distinctly(self):
        listing = ('<article><a href="/Bids.aspx?bidID=4">Tree bid</a></article>'
                   '<article><a href="/Bids.aspx?bidID=5">Tree bid</a></article>')
        def fetch(url, binary=False):
            if url == ENTRY:
                return listing, "text/html", url
            if "bidID=4" in url:
                raise robots_policy.RobotsDenied("denied")
            raise OSError("gone")

        row = staged.probe(SOURCE, fetch=fetch)
        self.assertEqual(row["state"], "individual_notice_samples_failed")
        self.assertEqual(row["individual_samples_attempted"], 2)
        self.assertEqual(len(row["individual_sample_failures"]), 2)
        self.assertFalse(row["individual_notice_retrieved"])


    def test_withdrawn_or_expired_sample_is_historical_not_available(self):
        for state in ("Withdrawn", "Expired"):
            with self.subTest(state=state):
                html = ('<article><a href="/Bids.aspx?bidID=4">Tree and stump removal</a>'
                        f'<p>Status: {state}</p><p>Closes: 11/17/2026</p></article>')
                notice = ('<h1>Bid Title: Tree and stump removal</h1>'
                          '<p>Bid Number: 4</p><p>Description: Removal work</p>'
                          f'<p>Status: {state}</p>'
                          '<p>Closing Date/Time: 11/17/2026</p>')
                def fetch(url, binary=False):
                    if url == ENTRY:
                        return html, "text/html", url
                    return notice.encode(), "text/html", url
                row = staged.probe(SOURCE, fetch=fetch)
                self.assertEqual(row["sample_notice_status"], state.lower())
                self.assertEqual(row["sample_notice_temporal_evidence"], "closed_or_awarded")
                self.assertFalse(row["direct_monitoring_activated"])



if __name__ == "__main__":
    unittest.main()
