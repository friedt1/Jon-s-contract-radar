"""RSS 1.0/RDF regression fixtures are synthetic; no live leads or new sources."""
import datetime as dt
import unittest
from unittest.mock import patch

import local_scan as radar

NOW = dt.datetime(2026, 10, 28, 18, tzinfo=dt.timezone.utc)
SOURCE = {
    "name": "Reviewed community RSS fixture",
    "kind": "rss",
    "url": "https://community.example/feed.rdf",
    "public_feed_reviewed": True,
}
RDF = """<?xml version="1.0"?>
<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
         xmlns="http://purl.org/rss/1.0/"
         xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel rdf:about="https://community.example/feed.rdf">
    <title>Community requests</title>
  </channel>
  <item rdf:about="https://community.example/post/123">
    <title>Looking for tree trimming in Elmira NY</title>
    <description>Need a quote for my yard</description>
    <link>https://community.example/post/123</link>
    <dc:date>2026-10-27T12:00:00Z</dc:date>
  </item>
  <item rdf:about="https://community.example/post/124">
    <title>Monthly neighborhood meeting in Elmira NY</title>
    <description>Discussion only</description>
    <dc:date>2026-10-27T12:00:00Z</dc:date>
  </item>
  <item rdf:about="https://community.example/post/125">
    <title>Looking for stump grinding in Elmira NY</title>
    <description>Need a quote for our yard</description>
  </item>
</rdf:RDF>"""


def get(url):
    if url.endswith("/robots.txt"):
        return "User-agent: *\nAllow: /\n"
    if url == SOURCE["url"]:
        return RDF
    raise AssertionError("Unexpected network request: " + url)


class RDFTests(unittest.TestCase):
    def test_rdf_records_are_not_silently_dropped(self):
        with patch.object(radar.time, "sleep", return_value=None):
            rows = list(radar.records(SOURCE, getter=get))
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[0]["title"], "Looking for tree trimming in Elmira NY")
        self.assertEqual(rows[0]["url"], "https://community.example/post/123")
        self.assertEqual(rows[0]["published"], "2026-10-27T12:00:00Z")
        self.assertEqual(rows[1]["url"], "https://community.example/post/124")
        self.assertEqual(rows[2]["published"], "")
        self.assertIsNotNone(radar.candidate(rows[0], SOURCE, NOW))
        self.assertIsNone(radar.candidate(rows[2], SOURCE, NOW))

    def test_rdf_qualified_candidate_is_unverified_and_history_preserved(self):
        with patch.object(radar.time, "sleep", return_value=None):
            feed, history = radar.assemble(
                [SOURCE], {"leads": {}}, NOW, getter=get, pause=lambda _: None
            )
        self.assertEqual(feed["source_status"][SOURCE["name"]]["records_inspected"], 3)
        self.assertEqual(len(feed["leads"]), 1)
        lead = feed["leads"][0]
        self.assertEqual(lead["lead_type"], "service_request")
        self.assertEqual(lead["verification_state"], "unverified_candidate")
        self.assertEqual(lead["location"], "Elmira, NY")
        self.assertEqual(feed["metrics"]["verified_requests"], 0)
        self.assertEqual(feed["metrics"]["qualified_leads"], 0)
        self.assertEqual(len(history["leads"]), 1)
        self.assertEqual(feed["source_status"][SOURCE["name"]]["rejected"]["undated"], 1)
        self.assertEqual(feed["source_status"][SOURCE["name"]]["rejected"]["no_service_match"], 1)


if __name__ == "__main__":
    unittest.main()
