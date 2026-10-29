"""Regression: source URLs must not disclose contact data in URL paths."""
import datetime as dt
import unittest
import local_scan as radar

NOW = dt.datetime(2026, 10, 28, 12, tzinfo=dt.timezone.utc)
SOURCE = {"name": "Public town", "kind": "mastodon", "url": "https://social.example/api/v1/timelines/tag/elmira"}

class PathPrivacyTests(unittest.TestCase):
    def test_private_path_rejected_even_when_encoded(self):
        for url in (
            "https://social.example/@607-555-0199/post",
            "https://social.example/post/123-Main-Street-Elmira",
            "https://social.example/post/123%20Main%20Street",
            "https://social.example/post/contact%40example.org",
            "https://social.example/post/%2B16075550199",
        ):
            with self.subTest(url=url):
                self.assertEqual(radar.canonical(url), "")
                record = {
                    "title": "Need tree removal in Elmira NY",
                    "body": "Looking for tree removal at my home in Elmira NY.",
                    "url": url,
                    "published": "2026-10-27T12:00:00Z",
                }
                self.assertIsNone(radar.candidate(record, SOURCE, NOW))

    def test_nested_percent_encoded_contacts_are_rejected(self):
        # One decode pass leaves %2B, %40, or %20 in these URLs. A
        # downstream web server may decode again before displaying the path.
        for url in (
            "https://social.example/post/%252B16075550199",
            "https://social.example/post/contact%2540example.org",
            "https://social.example/post/123%2520Main%2520Street",
            "https://social.example/post/2156?ref=owner%2540example.org",
            "https://social.example/post/2156?ref=123%2520Main%2520Street",
            "https://social.example/post/2156?%2565mail=owner",
        ):
            with self.subTest(url=url):
                self.assertEqual(radar.canonical(url), "")

    def test_safe_opaque_permalink_remains_usable(self):
        url = "https://social.example/@homeowner/1099999999999"
        self.assertEqual(radar.canonical(url), url)
        self.assertEqual(
            radar.canonical("https://social.example/post/2156?bidID=416&utm_source=ad"),
            "https://social.example/post/2156?bidID=416",
        )

if __name__ == "__main__":
    unittest.main()
