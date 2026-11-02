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

    def test_broome_endorsed_provider_entrypoint_is_not_direct_monitoring(self):
        sources = json.loads(probe_staged_sources.SOURCES.read_text(encoding="utf-8"))
        self.assertEqual(len(sources), 102)
        self.assertEqual(sum(s["mode"] == "direct_page" for s in sources), 18)
        self.assertEqual(sum(s["mode"] == "discovery_pending" for s in sources), 84)
        row = next(x for x in sources if x["name"] == "Broome County")
        url = "https://www.bidnetdirect.com/new-york/broome-county"
        self.assertEqual(row["candidate_official_url"], url)
        self.assertEqual(row["mode"], "discovery_pending")
        self.assertFalse(row["verified_url"])
        self.assertEqual(row["url"], "")
        self.assertEqual(row["delegated_provider"], "BidNet Direct")
        self.assertTrue(row["provider_access_required"])

        # Synthetic provider landing page: even if it returns HTTP 200 and
        # mentions bids, no individual-notice feed or permission is proven.
        def fetch(url, binary=False):
            return ('<h1>Broome County Bid Opportunities</h1>'
                    '<p>Register to view official solicitations.</p>',
                    "text/html", url)

        result = probe_staged_sources.probe(row, fetch=fetch)
        self.assertEqual(result["state"],
                         "listing_reachable_external_provider_access_required")
        self.assertEqual(result["external_provider_host"], "www.bidnetdirect.com")
        self.assertTrue(result["listing_retrieved"])
        self.assertFalse(result["individual_notice_retrieved"])
        self.assertFalse(result["direct_monitoring_activated"])

    def test_broome_provider_403_is_access_forbidden_not_missing_or_open(self):
        from urllib.error import HTTPError
        sources = json.loads(probe_staged_sources.SOURCES.read_text(encoding="utf-8"))
        row = next(x for x in sources if x["name"] == "Broome County")

        def forbidden(url, binary=False):
            raise HTTPError(url, 403, "Forbidden", {}, None)

        result = probe_staged_sources.probe(row, fetch=forbidden)
        self.assertEqual(result["state"], "listing_access_forbidden")
        self.assertEqual(result["http_status"], 403)
        self.assertFalse(result["listing_retrieved"])
        self.assertFalse(result["individual_notice_retrieved"])
        self.assertFalse(result["direct_monitoring_activated"])

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
