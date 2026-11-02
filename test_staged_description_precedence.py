"""Staged individual-notice scope must not resurrect work excluded by details.

All fixtures are synthetic and cannot create a live opportunity or activate a
publisher. Erie is expired; Owego demolition excludes tree work.
"""
import datetime as dt
import unittest

import probe_staged_sources as staged


NOW = dt.datetime(2026, 11, 2, 12, tzinfo=dt.timezone.utc)
CIVIC_ENTRY = "https://county.example/Bids.aspx"
CIVIC_NOTICE = CIVIC_ENTRY + "?bidID=17"
CIVIC_SOURCE = {
    "name": "Cortland County",
    "mode": "discovery_pending",
    "candidate_official_url": CIVIC_ENTRY,
    "activation_gate": "Publisher terms review required",
}
CITY_ENTRY = "https://www.binghamton-ny.gov/government/departments/purchasing/bids-rfps"
CITY_NOTICE = "https://www.binghamton-ny.gov/Home/Components/RFP/RFP/505/90"
CITY_SOURCE = {
    "name": "City of Binghamton",
    "mode": "discovery_pending",
    "candidate_official_url": CITY_ENTRY,
    "activation_gate": "Publisher terms review required",
}


def civic_probe(title, description, due="11/19/2026 2:00 PM"):
    listing = (
        '<article><a href="/Bids.aspx?bidID=17">' + title +
        '</a><p>Status: Open</p><p>Closes: ' + due + '</p></article>'
    )
    notice = (
        '<h1>Bid Title: ' + title + '</h1><p>Bid Number: 17</p>'
        '<p>Description: ' + description + '</p><p>Status: Open</p>'
        '<p>Closing Date/Time: ' + due + '</p>'
    )
    def fetch(url, binary=False):
        if url == CIVIC_ENTRY:
            return listing, "text/html", url
        if url != CIVIC_NOTICE or not binary:
            raise AssertionError("Unexpected request: " + url)
        return notice.encode(), "text/html", url
    return staged.build([CIVIC_SOURCE], fetch=fetch, now=NOW)


def city_probe(title, description):
    listing = (
        '<table><tr><td><a href="/Home/Components/RFP/RFP/505/90">'
        + title + '</a></td><td>10/20/2026</td>'
        '<td>11/19/2026 10:30 AM</td><td>Open</td></tr></table>'
    )
    notice = (
        '<h1>Bids &amp; RFPs</h1><h1>' + title + '</h1>'
        '<p>Start Date: 10/20/2026</p>'
        '<p>Close Date: 11/19/2026 10:30 AM</p>'
        '<p>Description: ' + description + '</p><p>Contact Us</p>'
    )
    def fetch(url, binary=False):
        if url == CITY_ENTRY:
            return listing, "text/html", url
        if url != CITY_NOTICE or not binary:
            raise AssertionError("Unexpected request: " + url)
        return notice.encode(), "text/html", url
    return staged.build([CITY_SOURCE], fetch=fetch, now=NOW)


class StagedDescriptionPrecedenceTests(unittest.TestCase):
    def assert_unverified(self, report):
        row = report["probes"][0]
        self.assertEqual(row["state"],
                         "notice_format_confirmed_terms_review_required")
        self.assertFalse(row["direct_monitoring_activated"])
        self.assertNotIn("opportunities", report)
        return row

    def test_civic_title_cannot_override_explicit_tree_exclusion(self):
        row = self.assert_unverified(civic_probe(
            "Hazardous tree removal",
            "Tree removal by others; contractor demolishes existing structure."
        ))
        self.assertEqual(row["sample_notice_listing_scope_category"], "Tree removal")
        self.assertEqual(row["sample_notice_detail_scope_category"], "not_identified")
        self.assertEqual(row["sample_notice_detail_scope_basis"],
                         "individual_notice_description")
        self.assertTrue(row["sample_notice_listing_detail_scope_disagreement"])

    def test_civic_title_cannot_override_unrelated_actual_scope(self):
        row = self.assert_unverified(civic_probe(
            "Hazardous tree removal", "Purchase office furniture and chairs."
        ))
        self.assertEqual(row["sample_notice_detail_scope_category"], "not_identified")
        self.assertTrue(row["sample_notice_listing_detail_scope_disagreement"])

    def test_civic_attachment_boilerplate_uses_fetched_title(self):
        row = self.assert_unverified(civic_probe(
            "Hazardous tree removal", "See attached specifications."
        ))
        self.assertEqual(row["sample_notice_detail_scope_category"], "Tree removal")
        self.assertEqual(row["sample_notice_detail_scope_basis"],
                         "individual_notice_title")
        self.assertFalse(row["sample_notice_listing_detail_scope_disagreement"])

    def test_civic_actual_description_can_reveal_tree_work(self):
        row = self.assert_unverified(civic_probe(
            "General county maintenance", "Roadside tree trimming and pruning."
        ))
        self.assertEqual(row["sample_notice_detail_scope_category"], "Tree trimming")
        self.assertEqual(row["sample_notice_detail_scope_basis"],
                         "individual_notice_description")
        self.assertTrue(row["sample_notice_listing_detail_scope_disagreement"])

    def test_owego_demolition_and_expired_erie_are_not_live(self):
        owego = self.assert_unverified(civic_probe(
            "Owego building demolition", "Tree removal by others."
        ))
        self.assertEqual(owego["sample_notice_detail_scope_category"],
                         "not_identified")
        erie = self.assert_unverified(civic_probe(
            "Erie tree and stump removal", "Tree removal and stump grinding.",
            due="10/28/2026 2:00 PM"
        ))
        self.assertEqual(erie["sample_notice_detail_scope_category"], "Tree removal")
        self.assertEqual(erie["sample_notice_temporal_evidence"], "deadline_passed")

    def test_granicus_specific_description_overrides_tree_heading(self):
        row = self.assert_unverified(city_probe(
            "BID: Hazardous tree removal",
            "Tree removal by others; purchase office supplies."
        ))
        self.assertEqual(row["sample_notice_detail_scope_category"], "not_identified")
        self.assertEqual(row["sample_notice_detail_scope_basis"],
                         "individual_notice_description")
        self.assertTrue(row["sample_notice_listing_detail_scope_disagreement"])

    def test_granicus_attachment_only_description_uses_notice_h1(self):
        row = self.assert_unverified(city_probe(
            "BID: Hazardous tree removal", "See attached specifications."
        ))
        self.assertEqual(row["sample_notice_detail_scope_category"], "Tree removal")
        self.assertEqual(row["sample_notice_detail_scope_basis"],
                         "individual_notice_title")


if __name__ == "__main__":
    unittest.main()
