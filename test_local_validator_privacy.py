"""Public-artifact privacy gate: even historical JSON must not leak contacts."""
import datetime as dt
import json
import pathlib
import tempfile
import unittest

from local_scan import assemble
from validate_local_output import validate

NOW = dt.datetime(2026, 10, 28, 15, tzinfo=dt.timezone.utc)
SOURCE = {"name": "Public sample", "kind": "mastodon", "url": "https://social.example/api/v1/timelines/tag/elmira"}
BODY = "Looking for tree removal at my house in Elmira NY. Need a quote."


def scan_payload(body=BODY):
    return json.dumps([{"content": body, "visibility": "public",
                        "url": "https://social.example/@example/123",
                        "created_at": "2026-10-27T12:00:00Z"}])


class PublicPrivacyValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.sources = self.root / "sources.json"
        self.sources.write_text(json.dumps([SOURCE]), encoding="utf-8")
        self.feed, self.history = assemble([SOURCE], {"leads": {}}, NOW,
                                           getter=lambda _: scan_payload(),
                                           pause=lambda _: None)
        self.write()

    def write(self):
        (self.root / "local_leads.json").write_text(json.dumps(self.feed), encoding="utf-8")
        (self.root / "local_history.json").write_text(json.dumps(self.history), encoding="utf-8")

    def test_clean_artifacts_pass(self):
        validate(self.root, self.sources)

    def test_unredacted_current_and_history_fail(self):
        uid = self.feed["leads"][0]["id"]
        for secret in ("607-555-0123", "hello@example.org", "123 Main Street"):
            with self.subTest(secret=secret):
                original = self.feed["leads"][0]["summary"]
                self.feed["leads"][0]["summary"] = original + " " + secret
                self.history["leads"][uid]["summary"] = original + " " + secret
                self.write()
                with self.assertRaisesRegex(AssertionError, "Private contact or street address"):
                    validate(self.root, self.sources)
                self.feed["leads"][0]["summary"] = original
                self.history["leads"][uid]["summary"] = original

    def test_historical_only_privacy_violation_fails(self):
        uid = self.feed["leads"][0]["id"]
        empty_feed, retained_history = assemble([SOURCE], self.history,
                                                 NOW + dt.timedelta(hours=1),
                                                 getter=lambda _: "[]",
                                                 pause=lambda _: None)
        self.feed, self.history = empty_feed, retained_history
        self.history["leads"][uid]["evidence_snippet"] += " 607-555-0123"
        self.write()
        with self.assertRaisesRegex(AssertionError, "Private contact or street address"):
            validate(self.root, self.sources)


if __name__ == "__main__":
    unittest.main()
