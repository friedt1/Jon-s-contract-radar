"""Offline quality fixtures are synthetic regression cases, never real leads."""
import datetime as dt
import json
import pathlib
import tempfile
import unittest
from unittest.mock import patch
import local_scan as radar
from test_local_scan import NOW, SOCIAL, NEWS, BODY, record, timeline, assemble
from validate_local_output import validate


class QualityTests(unittest.TestCase):
    def test_evidence_contract_and_no_verification_claim(self):
        lead = radar.candidate(record(), SOCIAL, NOW)
        self.assertIn('Looking for tree removal', lead['evidence_snippet'])
        self.assertEqual(lead['verification_state'], 'unverified_candidate')
        self.assertEqual(lead['duplicate_key'], lead['fingerprint'])
        self.assertTrue(lead['limitations'])
        self.assertIn('heuristic', lead['confidence'])
        article = radar.candidate(record(), NEWS, NOW)
        self.assertEqual(article['verification_state'], 'not_a_request')

    def test_historical_privacy_redaction_preserves_identity_and_history(self):
        _, previous = assemble()
        uid, prior = next(iter(previous['leads'].items()))
        original_url = prior['url']
        prior['title'] = 'Need tree removal at 123 West Second Street in Elmira NY'
        prior['summary'] = 'Email owner@example.com or call (607) 555-1212 at 123 West Second Street'
        prior['evidence_snippet'] = prior['summary']
        feed, history = assemble(sources=[SOCIAL], previous=previous,
                                 getter=lambda _: '[]', now=NOW + dt.timedelta(days=1))
        self.assertEqual(feed['leads'], [])
        sanitized = history['leads'][uid]
        self.assertEqual(sanitized['id'], uid)
        self.assertEqual(sanitized['url'], original_url)
        self.assertEqual(sanitized['first_seen'], prior['first_seen'])
        for field in ('title', 'summary', 'evidence_snippet'):
            self.assertNotIn('123 West Second Street', sanitized[field])
            self.assertNotIn('owner@example.com', sanitized[field])
            self.assertNotIn('607) 555-1212', sanitized[field])
        self.assertIn('[address on source]', sanitized['title'])
        self.assertIn('[contact on source]', sanitized['summary'])

    def test_historical_privacy_redaction_rejects_nontext(self):
        _, previous = assemble()
        next(iter(previous['leads'].values()))['summary'] = ['not a text value']
        with self.assertRaisesRegex(ValueError, 'lead text must be a string'):
            assemble(sources=[SOCIAL], previous=previous,
                     getter=lambda _: '[]', now=NOW + dt.timedelta(days=1))

    def test_negative_need_and_seller_recommendation(self):
        for phrase in ["I don't need tree removal in Elmira", 'We highly recommend our tree removal in Elmira', 'Not looking for tree removal in Elmira', 'Need customers for tree removal in Elmira; fully insured']:
            self.assertIsNone(radar.candidate(record(phrase), SOCIAL, NOW), phrase)

    def test_seller_recommendation_is_not_a_customer_request(self):
        for phrase in ('I recommend tree removal in Elmira NY.',
                       'We would recommend tree removal in Elmira NY.'):
            self.assertIsNone(radar.candidate(record(phrase), SOCIAL, NOW), phrase)
        self.assertIsNotNone(radar.candidate(
            record('Can anyone recommend a tree removal company in Elmira NY?'),
            SOCIAL, NOW))

    def test_seller_ad_questions_are_not_customer_requests(self):
        # Ads often open with the same question a homeowner would ask.
        ads = (
            'Need tree removal in Elmira NY? Contact us today!',
            'Looking for tree trimming in Elmira NY? Our crews are available.',
            'Need stump grinding in Elmira NY? Get a free quote.',
            'Who can remove a tree in Elmira NY? We can help!',
            'Need tree removal in Elmira NY? Schedule a free estimate.',
        )
        for phrase in ads:
            with self.subTest(phrase=phrase):
                self.assertIsNone(radar.candidate(record(phrase), SOCIAL, NOW))
        # Do not reject actual people asking for a referral or a quote.
        for phrase in (
            'Can anyone recommend tree removal in Elmira NY?',
            'Looking for a quote for stump grinding in Elmira NY.',
        ):
            with self.subTest(phrase=phrase):
                self.assertIsNotNone(radar.candidate(record(phrase), SOCIAL, NOW))

    def test_news_cannot_resurrect_or_downgrade_historical_request(self):
        _, previous = assemble()
        prior = next(iter(previous['leads'].values()))
        rss = ('<rss><channel><item><title>' + BODY + '</title>'
               '<link>' + prior['url'] + '</link>'
               '<pubDate>Tue, 27 Oct 2026 12:00:00 GMT</pubDate>'
               '</item></channel></rss>')
        feed, history = assemble(sources=[NEWS], previous=previous,
                                 getter=lambda _: rss,
                                 now=NOW + dt.timedelta(days=1))
        self.assertEqual(feed['leads'], [])
        self.assertEqual(feed['metrics']['request_candidates'], 0)
        self.assertEqual(feed['metrics']['news_context'], 0)
        self.assertEqual(history['leads'][prior['id']], prior)

    def test_news_cannot_downgrade_request_in_same_scan(self):
        rss = ('<rss><channel><item><title>' + BODY + '</title>'
               '<link>https://social.example/@person/123</link>'
               '<pubDate>Tue, 27 Oct 2026 12:00:00 GMT</pubDate>'
               '</item></channel></rss>')
        feed, history = assemble(sources=[SOCIAL, NEWS],
                                 getter=lambda url: rss if url == NEWS['url'] else timeline(BODY))
        self.assertEqual(len(feed['leads']), 1)
        self.assertEqual(feed['leads'][0]['lead_type'], 'service_request')
        self.assertEqual(history['leads'][feed['leads'][0]['id']]['lead_type'], 'service_request')

    def test_same_generic_title_does_not_merge_different_customers(self):
        # Two different local customers can use the same headline on one day.
        # They must not collapse into a single lead merely because the
        # headline, town, and posting date match.
        common = 'Looking for tree removal in Elmira NY'
        entries = [
            {'title': common, 'body': 'Need a quote for a fallen maple at my house in Elmira NY.',
             'url': 'https://social.example/@first/101', 'published': '2026-10-27T12:00:00Z'},
            {'title': common, 'body': 'Need a quote for two tall pines in my yard in Elmira NY.',
             'url': 'https://social.example/@second/102', 'published': '2026-10-27T12:00:00Z'},
        ]
        with patch.object(radar, 'records', return_value=iter(entries)):
            feed, history = radar.assemble([SOCIAL], {'leads': {}}, NOW,
                                           getter=lambda _: '[]', pause=lambda _: None)
        self.assertEqual(len(feed['leads']), 2)
        self.assertEqual(len(history['leads']), 2)
        self.assertEqual(len({lead['duplicate_key'] for lead in feed['leads']}), 2)

    def test_legacy_fingerprint_still_matches_stable_permalink(self):
        # Existing history must keep its original ID and first-seen date.
        _, previous = assemble()
        prior = next(iter(previous['leads'].values()))
        prior['fingerprint'] = 'legacy-title-only-fingerprint'
        prior['duplicate_key'] = prior['fingerprint']
        feed, history = assemble(previous=previous, now=NOW + dt.timedelta(hours=1))
        self.assertEqual(len(feed['leads']), 1)
        self.assertEqual(feed['leads'][0]['id'], prior['id'])
        self.assertEqual(feed['leads'][0]['first_seen'], prior['first_seen'])
        self.assertEqual(len(history['leads']), 1)

    def test_metrics_explain_zero_and_keep_articles_separate(self):
        feed, _ = assemble(getter=lambda _: timeline('Tree removal in Elmira', 'We offer tree removal in Elmira', 'Need tree removal in Texas', 'Need a plumber in Elmira'))
        status = feed['source_status'][SOCIAL['name']]
        self.assertEqual(status['records_inspected'], 4)
        self.assertEqual(sum(status['rejected'].values()), 4)
        self.assertEqual(feed['metrics']['verified_requests'], 0)
        self.assertEqual(feed['metrics']['qualified_leads'], 0)
        self.assertFalse(feed['leads'])

    def test_news_metrics_never_qualified(self):
        rss = '<rss><channel><item><title>Need tree removal in Elmira</title><link>https://example.org/story</link><pubDate>Tue, 27 Oct 2026 12:00:00 GMT</pubDate></item></channel></rss>'
        feed, _ = assemble(sources=[NEWS], getter=lambda _: rss)
        self.assertEqual(feed['metrics']['news_context'], 1)
        self.assertEqual(feed['metrics']['request_candidates'], 0)
        self.assertEqual(feed['request_sources_ok'], 0)

    def test_request_outage_with_healthy_news_preserves_published_artifacts(self):
        # A news-only partial success must not overwrite previously published
        # current customer requests or historical records.
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)
            (path / 'local_leads.json').write_text('{"sentinel": "prior customer feed"}')
            (path / 'local_history.json').write_text('{"leads": {}, "sentinel": "prior history"}')
            before = {name: (path / name).read_bytes() for name in
                      ('local_leads.json', 'local_history.json')}
            original = radar.assemble
            def isolated(sources, previous, now):
                return original([SOCIAL, NEWS], previous, now,
                                getter=lambda url: '<rss><channel/></rss>' if url == NEWS['url'] else
                                       (_ for _ in ()).throw(OSError('request feed unavailable')),
                                pause=lambda _: None)
            with (patch('sys.argv', ['local_scan.py', '--data-dir', directory]),
                  patch.object(radar, 'assemble', side_effect=isolated)):
                with self.assertRaisesRegex(RuntimeError, 'All request sources failed'):
                    radar.main()
            self.assertEqual(before, {name: (path / name).read_bytes() for name in before})

    def test_html_error_is_source_failure_not_empty_success(self):
        with self.assertRaisesRegex(RuntimeError, 'All local sources failed'):
            assemble(sources=[NEWS], getter=lambda _: '<html><body>Login</body></html>')

    def test_full_history_survives_expiry_and_partial_failures(self):
        _, history = assemble()
        original = next(iter(history['leads'].values()))
        history['leads'] = {str(i): {**original, 'id':str(i), 'fingerprint':str(i)} for i in range(2005)}
        # No retention truncation; failure at one source cannot purge old records.
        feed, saved = assemble(sources=[SOCIAL, NEWS], previous=history,
                              getter=lambda url: '[]' if url == SOCIAL['url'] else '<bad',
                              now=NOW + dt.timedelta(days=31))
        self.assertFalse(feed['leads'])
        self.assertEqual(saved['leads'], history['leads'])

    def test_rate_limits_for_reviewed_feeds(self):
        source = {**SOCIAL, 'kind':'rss', 'public_feed_reviewed':True}
        def get(url):
            return 'User-agent: *\nAllow: /\nCrawl-delay: 4\nRequest-rate: 1/10' if url.endswith('robots.txt') else '<rss/>'
        with patch.object(radar.time, 'sleep') as sleep:
            self.assertEqual(list(radar.records(source, get)), [])
            sleep.assert_called_once_with(10)
        with self.assertRaisesRegex(ValueError, 'operator scheduling'):
            list(radar.records(source, lambda _: 'User-agent: *\nAllow: /\nCrawl-delay: 120'))

    def test_current_v2_artifacts_validate_and_tampering_fails(self):
        sources = json.loads((radar.ROOT / 'local_sources.json').read_text())
        def get(url):
            return '<rss/>' if 'news.google.com' in url else timeline(BODY)
        feed, history = radar.assemble(sources, {'leads':{}}, NOW, getter=get, pause=lambda _:None)
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory)
            radar.write_json(path / 'local_leads.json', feed)
            radar.write_json(path / 'local_history.json', history)
            validate(path)
            feed['metrics']['qualified_leads'] = 1
            radar.write_json(path / 'local_leads.json', feed)
            with self.assertRaises(AssertionError): validate(path)
