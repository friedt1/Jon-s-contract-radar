"""Fail-closed reviewed RSS policy checks: no feed request after bad robots."""
import unittest
from unittest.mock import patch
import local_scan as radar

SOURCE = {
    'name': 'Operator-approved example feed',
    'kind': 'rss',
    'url': 'https://feeds.example.org/rss',
    'public_feed_reviewed': True,
}
RSS = '<rss><channel><item><title>Need tree removal in Elmira NY</title><description>My yard</description><link>https://feeds.example.org/post/1</link><pubDate>Tue, 27 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>'


class ReviewedRSSRobotsTests(unittest.TestCase):
    def run_feed(self, robots):
        called = []
        def getter(url):
            called.append(url)
            return robots if url.endswith('/robots.txt') else RSS
        with patch.object(radar.time, 'sleep', return_value=None):
            try:
                rows = list(radar.records(SOURCE, getter))
                return rows, called, None
            except ValueError as exc:
                return [], called, str(exc)

    def test_html_login_page_cannot_silently_allow_collection(self):
        rows, called, error = self.run_feed('<html><body>Login required</body></html>')
        self.assertEqual(rows, [])
        self.assertIn('robots policy missing or invalid', error)
        self.assertEqual(called, ['https://feeds.example.org/robots.txt'])

    def test_html_with_fake_user_agent_is_not_a_robots_policy(self):
        rows, called, error = self.run_feed('<html>\nUser-agent: *\nAllow: /\n</html>')
        self.assertEqual(rows, [])
        self.assertIn('robots policy missing or invalid', error)
        self.assertEqual(len(called), 1)

    def test_sitemap_only_or_proxy_error_fail_closed(self):
        for policy in ('Sitemap: https://feeds.example.org/sitemap.xml',
                       '403 proxy denied', '', '# no robot directives'):
            with self.subTest(policy=policy):
                rows, called, error = self.run_feed(policy)
                self.assertEqual(rows, [])
                self.assertIn('robots policy missing or invalid', error)
                self.assertEqual(len(called), 1)

    def test_valid_allow_and_disallow_still_work(self):
        rows, called, error = self.run_feed('User-agent: *\nAllow: /')
        self.assertIsNone(error)
        self.assertEqual(len(rows), 1)
        self.assertEqual(len(called), 2)
        rows, called, error = self.run_feed('User-agent: *\nDisallow: /rss')
        self.assertEqual(rows, [])
        self.assertIn('robots disallows feed', error)
        self.assertEqual(len(called), 1)


if __name__ == '__main__':
    unittest.main()
