"""HTTP 200 anti-bot interstitials are not successful procurement fetches.

Synthetic HTML only; never creates an opportunity or changes source activation.
"""
import unittest
from unittest.mock import patch

import access_challenge
import scan
import source_health


URL = "https://county.example/Bids.aspx"
SOURCE = {"name": "County", "mode": "direct_page", "url": URL, "verified_url": True}


class Response:
    status = 200
    url = URL

    def __init__(self, body, ctype="text/html"):
        self.body = body
        self.headers = {"Content-Type": ctype}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, count):
        return self.body[:count]


class AntiBotChallengeTests(unittest.TestCase):
    def test_only_explicit_challenge_markers(self):
        samples = (
            (b'<html><title>Just a moment</title><script src="/cdn-cgi/challenge-platform/h/b/orchestrate"></script></html>', "cloudflare_challenge"),
            (b'<!doctype html><html><div id="px-captcha">Verify you are human</div></html>', "captcha_challenge"),
            (b'<html><script>aws-waf-token</script>captcha</html>', "waf_challenge"),
            (b'<html><h1>Tree removal RFP</h1><p>Cloudflare and CAPTCHA training</p></html>', None),
            (b'<html><h1>Tree trimming bid</h1></html>', None),
            (b'%PDF-1.4 cf-chl- /cdn-cgi/challenge-platform/', None),
        )
        for body, expected in samples:
            with self.subTest(body=body[:35]):
                self.assertEqual(access_challenge.challenge_kind(body), expected)

    def test_whitespace_before_bom_challenge_and_pdf_boundary(self):
        # Some publishers prepend whitespace before a UTF-8 BOM. The HTML
        # challenge still needs detection, but PDFs must remain unaffected.
        for body in (
            b' \r\n\xef\xbb\xbf<html><script>cf-chl-test</script></html>',
            ' \n\ufeff<!doctype html><html><script>cf-chl-test</script></html>',
        ):
            with self.subTest(body=repr(body)[:50]):
                self.assertEqual(access_challenge.challenge_kind(body),
                                 "cloudflare_challenge")
        self.assertIsNone(access_challenge.challenge_kind(
            b' \r\n\xef\xbb\xbf%PDF-1.7 cf-chl-test'))

    def test_http_200_challenge_fails_closed_before_parsing(self):
        body = (b'<html><title>Just a moment</title><script '
                b'src="/cdn-cgi/challenge-platform/h/b/orchestrate"></script></html>')
        with patch.object(scan.robots_policy, "assert_allowed"), patch.object(
            scan.ur, "build_opener"
        ) as opener:
            opener.return_value.open.return_value = Response(body)
            with self.assertRaises(access_challenge.AccessChallenge):
                scan.fetch(URL)
            with self.assertRaises(access_challenge.AccessChallenge):
                scan.fetch(URL, binary=True)

    def test_normal_html_and_pdf_not_blocked(self):
        for body, ctype in (
            (b'<html><h1>Tree removal bid</h1></html>', "text/html"),
            (b'%PDF-1.4 /cdn-cgi/challenge-platform/', "application/pdf"),
        ):
            with self.subTest(ctype=ctype), patch.object(
                scan.robots_policy, "assert_allowed"
            ), patch.object(scan.ur, "build_opener") as opener:
                opener.return_value.open.return_value = Response(body, ctype)
                result, kind, final = scan.fetch(URL, binary=True)
                self.assertEqual(result, body)
                self.assertEqual(final, URL)

    def test_source_health_separates_challenge_from_success(self):
        with patch.object(scan, "scan_direct", side_effect=access_challenge.AccessChallenge(
            "cloudflare_challenge"
        )), patch.object(scan, "scan_news", return_value=[]):
            _, status, leads = scan.run(SOURCE)
        self.assertEqual(leads, [])
        self.assertIn("direct error: AccessChallenge", status)
        row = source_health.classify(SOURCE, status)
        self.assertEqual(row["direct_state"], "challenge_blocked")
        self.assertEqual(row["individual_bid_details_fetched"], 0)
        self.assertEqual(source_health.summarize([SOURCE], {SOURCE["name"]: status})[
            "counts"]["challenge_blocked"], 1)

    def test_detail_and_pagination_challenge_diagnostics(self):
        status = ("direct fetched; 1 listing pages; 2 detail errors: AccessChallenge;"
                  " 1 pagination errors: AccessChallenge; 0 individual bid details fetched")
        row = source_health.classify(SOURCE, status)
        self.assertEqual(row["detail_access_state"], "challenge_blocked")
        self.assertEqual(row["pagination_access_state"], "challenge_blocked")
        self.assertEqual(row["detail_error_types"], ["challenge_blocked"])
        self.assertEqual(row["pagination_error_types"], ["challenge_blocked"])
        counts = source_health.summarize([SOURCE], {"County": status})["counts"]
        self.assertEqual(counts["detail_challenge_blocked_sources"], 1)
        self.assertEqual(counts["pagination_challenge_blocked_sources"], 1)


    def test_staged_probe_reports_listing_and_notice_challenges(self):
        import probe_staged_sources
        source = {"name": "Cortland County", "mode": "discovery_pending",
                  "candidate_official_url": URL, "activation_gate": "Terms review"}
        def blocked(url, binary=False):
            raise access_challenge.AccessChallenge("cloudflare_challenge")
        row = probe_staged_sources.probe(source, fetch=blocked)
        self.assertEqual(row["state"], "listing_access_challenge")
        self.assertFalse(row["listing_retrieved"])
        self.assertFalse(row["direct_monitoring_activated"])

        listing = ('<article><a href="/Bids.aspx?bidID=4">Tree removal</a>'
                   '<p>Status: Open</p></article>')
        def blocked_detail(url, binary=False):
            if url == URL:
                return listing, "text/html", URL
            raise access_challenge.AccessChallenge("captcha_challenge")
        row = probe_staged_sources.probe(source, fetch=blocked_detail)
        self.assertEqual(row["state"], "individual_notice_access_challenge")
        self.assertEqual(row["individual_samples_attempted"], 1)
        self.assertEqual(row["individual_sample_failures"][0]["state"],
                         "individual_notice_access_challenge")
        self.assertFalse(row["individual_notice_retrieved"])
        self.assertFalse(row["direct_monitoring_activated"])


if __name__ == "__main__":
    unittest.main()
