"""Fail-closed access challenge classification at HTML/document boundaries.

Synthetic responses only: no real bid is created, promoted, or activated.
"""
import unittest

from access_challenge import challenge_kind


class ChallengeBoundaryRegressionTests(unittest.TestCase):
    def test_markers_in_pdf_and_plain_text_are_not_html_challenges(self):
        for payload in (
            b"%PDF-1.7\n<html><script>cf-chl-</script>",
            b"Bid attachment notes: /cdn-cgi/challenge-platform/",
            b'{"html":"<html>cf-chl-</html>"}',
        ):
            with self.subTest(payload=payload[:30]):
                self.assertIsNone(challenge_kind(payload))

    def test_ordinary_procurement_mentions_do_not_trigger_block(self):
        for payload in (
            '<html><h1>CAPTCHA accessibility procurement</h1></html>',
            '<html><p>Cloudflare services and aws-waf-token training</p></html>',
            '<html><p>Tree removal contract: robots and captcha policy</p></html>',
        ):
            with self.subTest(payload=payload[:40]):
                self.assertIsNone(challenge_kind(payload))

    def test_explicit_interstitial_markers_are_blocked(self):
        cases = (
            ('<html><script src="/cdn-cgi/challenge-platform/h/g"></script></html>',
             "cloudflare_challenge"),
            ('<!DOCTYPE HTML><html><script>cf-chl-abc</script></html>',
             "cloudflare_challenge"),
            ('<html><div class="h-captcha">Verify you are human</div></html>',
             "captcha_challenge"),
            ('<html><script>aws-waf-token</script><p>challenge</p></html>',
             "waf_challenge"),
        )
        for payload, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(challenge_kind(payload.encode()), expected)

    def test_utf8_bom_before_html_challenge_is_detected(self):
        payload = b"\xef\xbb\xbf<html><script src=\"/cdn-cgi/challenge-platform/\"></script></html>"
        self.assertEqual(challenge_kind(payload), "cloudflare_challenge")
        self.assertEqual(challenge_kind(payload.decode("utf-8")), "cloudflare_challenge")
        self.assertIsNone(challenge_kind(b"\xef\xbb\xbf%PDF-1.7 cf-chl-"))

    def test_non_text_inputs_do_not_raise_or_signal_success(self):
        for payload in (None, 42, {}, []):
            with self.subTest(payload=payload):
                self.assertIsNone(challenge_kind(payload))


if __name__ == "__main__":
    unittest.main()
