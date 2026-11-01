"""Offline staged-probe prioritization tests; no actual bids are published."""
import datetime as dt
import unittest

import probe_staged_sources as staged
import scan


NOW = dt.datetime(2026, 10, 31, 20, tzinfo=dt.timezone.utc)
ENTRY = "https://county.example/Bids.aspx"
SOURCE = {
    "name": "Cortland County", "mode": "discovery_pending",
    "candidate_official_url": ENTRY,
    "activation_gate": "Publisher terms and live notice validation required",
}


def record(title, due="2026-11-19", status="open"):
    return {
        "title": title, "description": title, "deadline": due,
        "deadline_time": "2:00 PM", "open_status": status,
    }


class StagedRelevantSamplingTests(unittest.TestCase):
    def test_tree_and_vegetation_scopes_win_only_within_same_temporal_tier(self):
        unrelated = record("Office furniture RFP")
        tree = record("Hazardous tree removal and stump grinding bid")
        vegetation = record("Roadside vegetation management RFP")
        site_prep = record("Site grading and earthwork RFP")
        priorities = staged._sample_priority
        self.assertLess(priorities(tree, NOW), priorities(vegetation, NOW))
        self.assertLess(priorities(vegetation, NOW), priorities(site_prep, NOW))
        self.assertLess(priorities(site_prep, NOW), priorities(unrelated, NOW))

    def test_future_unrelated_still_preempts_expired_or_conflicted_tree(self):
        current = record("Office furniture RFP")
        expired = record("Tree and stump removal", due="2026-10-28")
        conflicted = dict(record("Tree trimming bid"),
                          listing_deadline_conflict=True)
        closed = record("Storm debris cleanup", status="closed")
        for stale in (expired, conflicted, closed):
            with self.subTest(stale=stale):
                self.assertLess(staged._sample_priority(current, NOW),
                                staged._sample_priority(stale, NOW))

    def test_owego_demolition_tree_work_by_others_not_relevant(self):
        owego = record("67 Central Avenue demolition rebid. Tree removal by others")
        unrelated = record("Office furniture RFP")
        self.assertIsNone(scan.category(owego["title"]))
        self.assertEqual(staged._sample_priority(owego, NOW),
                         staged._sample_priority(unrelated, NOW))
        # Historical Erie-style expiration must never become an open bid.
        erie = record("Erie tree and stump removal", due="2026-10-28")
        self.assertGreater(staged._sample_priority(erie, NOW),
                           staged._sample_priority(unrelated, NOW))

    def test_fourth_relevant_notice_sampled_before_three_unrelated_cards(self):
        cards = [
            ("101", "Office furniture procurement"),
            ("102", "IT support RFP"),
            ("103", "Uniform supply bid"),
            ("104", "Hazardous tree removal bid"),
        ]
        html = "".join(
            f'<article><a href="/Bids.aspx?bidID={bidid}">{title}</a>'
            '<p>Status: Open</p><p>Closes: 11/19/2026 2:00 PM</p></article>'
            for bidid, title in cards
        )
        calls = []

        def fake_fetch(url, binary=False):
            calls.append(url)
            if url == ENTRY:
                return html, "text/html", url
            self.assertTrue(binary)
            self.assertEqual(url, ENTRY + "?bidID=104")
            detail = (
                "<h1>Bid Title: Hazardous tree removal bid</h1>"
                "<p>Bid Number: 104</p>"
                "<p>Description: Removal of hazardous trees.</p>"
                "<p>Status: Open</p>"
                "<p>Closing Date/Time: 11/19/2026 2:00 PM</p>"
            )
            return detail.encode(), "text/html", url

        result = staged.probe(SOURCE, fetch=fake_fetch, now=NOW)
        self.assertEqual(result["individual_records_discovered"], 4)
        self.assertEqual(result["individual_samples_attempted"], 1)
        self.assertEqual(calls, [ENTRY, ENTRY + "?bidID=104"])
        self.assertEqual(result["state"], "notice_format_confirmed_terms_review_required")
        self.assertTrue(result["individual_notice_retrieved"])
        self.assertFalse(result["direct_monitoring_activated"])
        self.assertNotIn("opportunities", result)


if __name__ == "__main__":
    unittest.main()
