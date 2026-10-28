import datetime as dt
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
import local_scan as radar

NOW = dt.datetime(2026, 10, 28, 12, tzinfo=dt.timezone.utc)
SOCIAL = {'name': 'Public town', 'kind': 'mastodon', 'url': 'https://social.example/api/v1/timelines/tag/elmira'}
NEWS = {'name': 'News', 'kind': 'news', 'url': 'https://news.example/rss'}
BODY = 'Looking for tree removal at my house in Elmira NY. Need a quote.'


def record(body=BODY, **kwargs):
    return {'title': '', 'body': body, 'url': 'https://social.example/@person/123', 'published': '2026-10-27T12:00:00Z', **kwargs}


def timeline(*bodies):
    return json.dumps([{'content': body, 'visibility': 'public', 'url': f'https://social.example/@person/{i}', 'created_at': '2026-10-27T12:00:00Z'} for i, body in enumerate(bodies)])


def assemble(sources=None, previous=None, getter=None, now=NOW):
    return radar.assemble(sources or [SOCIAL], previous or {'leads': {}}, now, getter or (lambda _: timeline(BODY)), pause=lambda _: None)


class ClassificationTests(unittest.TestCase):
    def test_explicit_request_and_score(self):
        lead = radar.candidate(record(), SOCIAL, NOW)
        self.assertEqual(lead['lead_type'], 'service_request')
        self.assertEqual(lead['customer_type'], 'homeowner')
        self.assertEqual(lead['location'], 'Elmira, NY')
        self.assertEqual(lead['services'], ['Tree removal'])
        self.assertGreaterEqual(lead['score'], 80)
        self.assertIn('unverified', lead['geography_note'])

    def test_all_services_and_pa_commercial(self):
        for service in radar.SERVICES:
            lead = radar.candidate(record(f'Our business in Wellsboro PA needs {service.lower()}. Seeking quotes.'), SOCIAL, NOW)
            self.assertIn(service, lead['services'])
            self.assertEqual(lead['customer_type'], 'commercial')
            self.assertEqual(lead['location'], 'Wellsboro, PA')

    def test_no_demand_chatter_ad_jobs_closed(self):
        for body in ('Tree removal happened in Elmira.', 'We offer tree removal in Elmira. Need help? Call us.', 'Now hiring tree removal workers in Elmira.', 'Looking for tree removal in Elmira but already hired someone.', 'Looking for a tree removal machine for sale in Elmira.'):
            self.assertIsNone(radar.candidate(record(body), SOCIAL, NOW), body)

    def test_news_never_becomes_request(self):
        lead = radar.candidate(record(), NEWS, NOW)
        self.assertEqual(lead['lead_type'], 'news_context')
        self.assertLess(lead['score'], 50)
        self.assertIn('not a customer', lead['verification'])
        self.assertIsNone(radar.candidate(record('According to a press release, Elmira residents need tree removal.'), SOCIAL, NOW))

    def test_location_required_and_ambiguous_towns(self):
        for body in ('Need tree removal at my house.', 'Need tree removal in Athens.', 'Need tree removal in Elmira Ontario.', 'Need tree removal in Athens GA.', 'Need tree removal in Corning CA.'):
            self.assertIsNone(radar.candidate(record(body), SOCIAL, NOW), body)
        self.assertEqual(radar.candidate(record('Need tree removal in Athens PA.'), SOCIAL, NOW)['location'], 'Athens, PA')

    def test_dates_reject_missing_old_future_invalid(self):
        for value in ('', 'bad', '2026-09-01', '2026-10-29T12:00:00Z'):
            self.assertIsNone(radar.candidate(record(published=value), SOCIAL, NOW), value)
        self.assertIsNotNone(radar.candidate(record(published='Tue, 27 Oct 2026 12:00:00 GMT'), SOCIAL, NOW))

    def test_contacts_redacted_no_invented_fields(self):
        lead = radar.candidate(record(BODY + ' Email me a@example.org or call 607-555-0101.'), SOCIAL, NOW)
        self.assertNotIn('a@example.org', str(lead))
        self.assertNotIn('607-555-0101', str(lead))
        self.assertNotIn('phone', lead)
        self.assertNotIn('email', lead)

    def test_residential_address_not_republished(self):
        lead = radar.candidate(record(
            'Looking for tree removal at 123 Main Street, Elmira NY. '
            'Need a quote; email me at tree@example.org or call 607-555-0199.'
        ), SOCIAL, NOW)
        self.assertIsNotNone(lead)
        for field in ('title', 'summary', 'evidence_snippet'):
            self.assertNotIn('123 Main Street', lead[field])
            self.assertNotIn('tree@example.org', lead[field])
            self.assertNotIn('607-555-0199', lead[field])
        self.assertIn('[address on source]', lead['evidence_snippet'])
        self.assertEqual(lead['location'], 'Elmira, NY')

    def test_html_text_does_not_include_script(self):
        self.assertEqual(radar.text('<p>Need <b>tree removal</b></p><script>bad()</script>'), 'Need tree removal')


class FetchAndFeedTests(unittest.TestCase):
    def test_url_validation_and_normalization(self):
        for url in ('javascript:alert(1)', 'http://example.org/post', 'https://user:pass@example.org', 'https://127.0.0.1/x', 'https://localhost/x', 'https://169.254.169.254/x', 'https://example.org:9000/x'):
            self.assertFalse(radar.safe_url(url), url)
        self.assertEqual(radar.canonical('https://EXAMPLE.org/p/?utm_source=x&b=2&a=1#x'), 'https://example.org/p?a=1&b=2')

    def test_redirect_refused(self):
        with self.assertRaisesRegex(ValueError, 'redirect refused'):
            radar.NoRedirect().redirect_request(None, None, 302, '', {}, 'http://localhost/')

    def test_public_visibility_only_no_boosts(self):
        entries = json.loads(timeline(BODY, BODY, BODY, BODY))
        entries[0]['visibility'] = 'private'
        entries[1]['visibility'] = 'unlisted'
        entries[2]['reblog'] = {'content': BODY}
        self.assertEqual(len(list(radar.records(SOCIAL, lambda _: json.dumps(entries)))), 1)

    def test_rss_and_atom(self):
        rss = '<rss><channel><item><title>Need tree removal in Elmira</title><description>my yard</description><link>https://example.org/1</link><pubDate>Tue, 27 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>'
        source = {**SOCIAL, 'kind': 'rss', 'public_feed_reviewed': True}
        calls = []
        def get(url):
            calls.append(url)
            return 'User-agent: *\nAllow: /' if url.endswith('robots.txt') else rss
        rows = list(radar.records(source, get))
        self.assertEqual(len(rows), 1)
        self.assertIsNotNone(radar.candidate(rows[0], source, NOW))
        self.assertTrue(calls[0].endswith('/robots.txt'))
        atom = '<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Need stump grinding in Wellsboro</title><summary>Our home</summary><link href="https://example.org/2"/><updated>2026-10-27T12:00:00Z</updated></entry></feed>'
        rows = list(radar.records(NEWS, lambda _: atom))
        self.assertEqual(rows[0]['url'], 'https://example.org/2')

    def test_rss_fails_closed_for_robots_and_unreviewed(self):
        with self.assertRaisesRegex(ValueError, 'review public feed'):
            list(radar.records({**SOCIAL, 'kind': 'rss'}, lambda _: ''))
        with self.assertRaisesRegex(ValueError, 'robots disallows'):
            list(radar.records({**SOCIAL, 'kind': 'rss', 'public_feed_reviewed': True}, lambda _: 'User-agent: *\nDisallow: /'))

    def test_restricted_social_and_duplicate_sources_rejected(self):
        for sources in ([SOCIAL, SOCIAL], [{**SOCIAL, 'url': 'https://www.facebook.com/private'}], []):
            with self.assertRaises(ValueError): radar.validate_sources(sources)


class PersistenceTests(unittest.TestCase):
    def test_url_and_cross_post_dedup_history_repeatability(self):
        sources = [SOCIAL, {**SOCIAL, 'name': 'Other public town', 'url': 'https://social.example/other'}]
        def get(url):
            entries = json.loads(timeline(BODY))
            if url.endswith('other'): entries[0]['url'] = 'https://another.example/post/2?utm_source=ad'
            return json.dumps(entries)
        feed, history = assemble(sources=sources, getter=get)
        self.assertEqual(len(feed['leads']), 1)
        self.assertEqual(len(feed['leads'][0]['source_links']), 2)
        first = feed['leads'][0]['first_seen']
        feed2, history2 = assemble(sources=sources, previous=history, getter=get, now=NOW + dt.timedelta(days=1))
        self.assertEqual(feed2['leads'][0]['first_seen'], first)
        self.assertNotEqual(feed2['leads'][0]['last_seen'], first)
        self.assertEqual(len(history2['leads']), 1)
        self.assertEqual(feed2['leads'][0]['id'], feed['leads'][0]['id'])

    def test_removed_posts_stay_in_history_not_current(self):
        _, history = assemble()
        feed, history2 = assemble(previous=history, getter=lambda _: '[]')
        self.assertFalse(feed['leads'])
        self.assertEqual(len(history2['leads']), 1)

    def test_partial_failures_are_visible(self):
        def get(url):
            if url == SOCIAL['url']: raise OSError('unreachable')
            return '<rss><channel/></rss>'
        feed, _ = assemble(sources=[SOCIAL, NEWS], getter=get)
        self.assertEqual(feed['source_status'][SOCIAL['name']]['state'], 'error')
        self.assertEqual(feed['request_sources_ok'], 0)
        self.assertFalse(feed['leads'])

    def test_all_failure_preserves_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp)
            for name in ('local_leads.json', 'local_history.json'):
                (path / name).write_text('{"leads": {}}')
            before = {p.name: p.read_bytes() for p in path.iterdir()}
            with patch('sys.argv', ['local_scan.py', '--data-dir', tmp]), patch.object(radar, 'fetch', side_effect=OSError()), patch.object(radar, 'assemble', side_effect=RuntimeError('All local sources failed')):
                with self.assertRaises(RuntimeError): radar.main()
            self.assertEqual({p.name: p.read_bytes() for p in path.iterdir()}, before)
        with self.assertRaisesRegex(RuntimeError, 'All local sources failed'):
            assemble(getter=lambda _: '<invalid')

    def test_invalid_source_payload_cannot_publish_partial_records(self):
        def rows(source, getter):
            yield record()
            raise ValueError('malformed later record')
        with patch.object(radar, 'records', rows):
            with self.assertRaises(RuntimeError): assemble()

    def test_corrupt_history_not_silently_reset(self):
        with self.assertRaises(ValueError): assemble(previous={'leads': []})

    def test_cli_writes_only_local_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp)
            real_assemble = radar.assemble
            with patch('sys.argv', ['local_scan.py', '--data-dir', tmp]), patch.object(radar, 'assemble', wraps=lambda sources, previous, now: real_assemble([SOCIAL], previous, NOW, getter=lambda _: timeline(BODY), pause=lambda _: None)):
                radar.main()
                radar.main()
            self.assertEqual(sorted(x.name for x in path.iterdir()), ['local_history.json', 'local_leads.json'])
            feed = json.loads((path / 'local_leads.json').read_text())
            history = json.loads((path / 'local_history.json').read_text())
            self.assertEqual(feed['leads'][0]['id'], next(iter(history['leads'])))

    def test_default_source_configuration(self):
        sources = json.loads((radar.ROOT / 'local_sources.json').read_text())
        radar.validate_sources(sources)
        self.assertTrue(any(s['kind'] == 'mastodon' for s in sources))
        self.assertTrue(any(s['kind'] == 'news' for s in sources))


if __name__ == '__main__': unittest.main()
