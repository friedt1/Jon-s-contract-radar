"""Official URL staging is not live bid monitoring or verified opportunity discovery."""
import json
import unittest

import civicplus_bids
import probe_staged_sources


class NewYorkStagedCountyTests(unittest.TestCase):
    def test_official_urls_are_staged_not_direct(self):
        sources = json.loads(probe_staged_sources.SOURCES.read_text(encoding="utf-8"))
        self.assertEqual(len(sources), 102)
        self.assertEqual(len({s["name"] for s in sources}), 102)
        expected = {
            "Livingston County": "https://www.livingstoncountyny.gov/Bids.aspx",
            "Wyoming County": "https://www.wyomingcountyny.gov/Bids.aspx",
        }
        for name, url in expected.items():
            with self.subTest(name=name):
                row = next(x for x in sources if x["name"] == name)
                self.assertEqual(row["mode"], "discovery_pending")
                self.assertFalse(row["verified_url"])
                self.assertFalse(row["url"])
                self.assertEqual(row["candidate_official_url"], url)
                self.assertTrue(row["activation_gate"])
                self.assertIn(name, civicplus_bids.SOURCES)

    def test_staged_probe_never_promotes_even_when_notice_parses(self):
        def fake_fetch(url, binary=False):
            if not binary:
                return ('<article><a href="/Bids.aspx?bidID=81">Unrelated food supply RFQ</a>'
                        '<p>Status: Open</p></article>'), "text/html", url
            return (b'<h1>Bid Number: 81</h1><p>Status: Open</p>'
                    b'<p>Description: Food supplies, no tree work.</p>'), "text/html", url

        row = probe_staged_sources.probe({
            "name": "Wyoming County",
            "mode": "discovery_pending",
            "candidate_official_url": "https://www.wyomingcountyny.gov/Bids.aspx",
            "activation_gate": "Terms review",
        }, fetch=fake_fetch)
        self.assertTrue(row["individual_notice_retrieved"])
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertNotIn("opportunities", row)
        self.assertEqual(row["state"], "notice_format_confirmed_terms_review_required")


if __name__ == "__main__":
    unittest.main()
