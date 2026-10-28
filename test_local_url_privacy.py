"""Public lead links must not disclose private contacts in URL parameters."""
import datetime as dt
import json
import pathlib
import tempfile
import unittest

from local_scan import candidate, canonical
from test_local_scan import NOW, SOCIAL, record, assemble
from validate_local_output import validate


class PermalinkPrivacyTests(unittest.TestCase):
    def test_private_query_parameters_are_rejected(self):
        bad = (
            'https://social.example/post/123?email=owner%40example.org',
            'https://social.example/post/123?phone=607-555-0199',
            'https://social.example/post/123?address=123%20Main%20Street',
            'https://social.example/post/123?ref=owner%40example.org',
            'https://social.example/post/123?message=Call%20607-555-0199',
            'https://social.example/post/123?access_token=secret',
        )
        for url in bad:
            with self.subTest(url=url):
                self.assertEqual(canonical(url), '')
                self.assertIsNone(candidate(record(url=url), SOCIAL, NOW))

    def test_safe_identifiers_and_tracking_normalize(self):
        self.assertEqual(canonical('https://social.example/post/123?bid=2149991&utm_source=test#section'),
                         'https://social.example/post/123?bid=2149991')
        self.assertIsNotNone(candidate(record(url='https://social.example/post/123?bid=2149991'), SOCIAL, NOW))

    def test_history_validator_rejects_private_permalink(self):
        feed, history = assemble()
        uid = feed['leads'][0]['id']
        private = 'https://social.example/post/123?email=owner%40example.org'
        feed['leads'][0]['url'] = private
        history['leads'][uid]['url'] = private
        with tempfile.TemporaryDirectory() as folder:
            directory = pathlib.Path(folder)
            (directory/'local_leads.json').write_text(json.dumps(feed), encoding='utf-8')
            (directory/'local_history.json').write_text(json.dumps(history), encoding='utf-8')
            with self.assertRaises(AssertionError):
                validate(directory)

if __name__ == '__main__':
    unittest.main()
