"""Granicus detail scope diagnostics: isolated notice fields, never live bids."""
import datetime as dt
import unittest

import granicus_rfps
import probe_staged_sources as staged
import scan

ENTRY = "https://www.binghamton-ny.gov/government/departments/purchasing/bids-rfps"
NOTICE = "https://www.binghamton-ny.gov/Home/Components/RFP/RFP/505/90"
SOURCE = {
    "name": "City of Binghamton", "mode": "discovery_pending",
    "candidate_official_url": ENTRY, "activation_gate": "Publisher terms review",
}
NOW = dt.datetime(2026, 11, 2, 16, 0, tzinfo=dt.timezone.utc)


def listing(title, due="11/19/2026 10:30 AM"):
    return (
        '<table><tr><td><a href="/Home/Components/RFP/RFP/505/90">'
        + title + '</a></td><td>10/20/2026</td><td>' + due
        + '</td><td>Open</td></tr></table>'
    )


def notice(title, description="", due="11/19/2026 10:30 AM"):
    return (
        '<h1>Bids &amp; RFPs</h1><p>City procurement information.</p>'
        '<h1>' + title + '</h1>'
        '<p>Department: Purchasing</p><p>Start Date: 10/20/2026</p>'
        '<p>Close Date: ' + due + '</p>'
        + ('<p>Description: ' + description + '</p>' if description else '')
        + '<p>Contact Us</p><p>City hall</p>'
    )


class GranicusDetailScopeTests(unittest.TestCase):
    def test_notice_h1_only_not_generic_page_heading(self):
        self.assertEqual(
            granicus_rfps.detail_title_html(
                '<h1>Bids &amp; RFPs</h1><h1>BID: Hazardous <em>tree</em> '
                'removal &amp; stump grinding</h1>'
            ),
            "BID: Hazardous tree removal & stump grinding",
        )
        self.assertEqual(granicus_rfps.detail_title_html(
            '<h1>Bids & RFPs</h1><h2>Tree removal</h2>'
        ), "")
        self.assertEqual(granicus_rfps.detail_title_html(
            '<h1>Procurement</h1><h1>Tree removal</h1>'
        ), "")

    def test_description_requires_label_after_close_date(self):
        self.assertEqual(
            granicus_rfps.detail_description(
                "Description: Tree trimming in navigation. "
                "Start Date: 10/20/2026 Close Date: 11/19/2026 "
                "Description: Office chairs. Contact Us Tree removal"),
            "Office chairs.",
        )
        self.assertEqual(granicus_rfps.detail_description(
            "Start Date: 10/20/2026 Close Date: 11/19/2026 "
            "Trees mentioned in general page footer"), "")

    def test_listing_and_detail_disagreements_are_diagnostic_only(self):
        cases = [
            ("BID: Hazardous tree removal", "BID: Office furniture",
             "Purchase office chairs.", "not_identified", True),
            ("BID: Office furniture", "BID: Hazardous tree removal",
             "Remove hazardous trees and grind stumps.", "Tree removal", True),
            ("BID: Hazardous tree removal", "BID: Hazardous tree removal",
             "Remove hazardous trees and grind stumps.", "Tree removal", False),
            ("BID: Hazardous tree removal", "BID: Site grading and earthwork",
             "Grading and earthwork for site preparation.", "Related site prep", True),
            ("BID: Site grading and earthwork", "BID: Hazardous tree removal",
             "Remove hazardous trees and grind stumps.", "Tree removal", True),
        ]
        for listed, detailed, description, category, mismatch in cases:
            with self.subTest(detailed=detailed):
                def fake_fetch(url, binary=False):
                    if url == ENTRY:
                        return listing(listed), "text/html", url
                    self.assertEqual(url, NOTICE)
                    return notice(detailed, description).encode(), "text/html", url

                report = staged.build([SOURCE], fetch=fake_fetch, now=NOW)
                row = report["probes"][0]
                self.assertEqual(row["state"],
                                 "notice_format_confirmed_terms_review_required")
                self.assertEqual(row["sample_notice_detail_scope_category"], category)
                self.assertEqual(row["sample_notice_detail_scope_evidence"],
                                 "individual_notice_labelled_fields_unverified")
                self.assertEqual(
                    row["sample_notice_listing_detail_scope_disagreement"], mismatch)
                self.assertFalse(row["direct_monitoring_activated"])
                self.assertNotIn("opportunities", report)

    def test_owego_demolition_exclusion_and_expired_erie_case(self):
        cases = [
            ("BID: 67 Central Avenue Owego demolition, tree removal by others",
             "BID: 67 Central Avenue Owego demolition, tree removal by others",
             "not_identified", "deadline_not_passed_unverified",
             "11/19/2026 10:30 AM"),
            ("BID: Erie tree and stump removal",
             "BID: Erie tree and stump removal",
             "Tree removal", "deadline_passed", "10/20/2026 10:30 AM"),
        ]
        for listed, detailed, category, temporal, due in cases:
            with self.subTest(listed=listed):
                def fake_fetch(url, binary=False):
                    if url == ENTRY:
                        return listing(listed, due), "text/html", url
                    return notice(detailed, due=due).encode(), "text/html", url
                report = staged.build([SOURCE], fetch=fake_fetch, now=NOW)
                row = report["probes"][0]
                self.assertEqual(row["sample_notice_detail_scope_category"], category)
                self.assertEqual(row["sample_notice_temporal_evidence"], temporal)
                self.assertFalse(row["direct_monitoring_activated"])
                self.assertNotIn("opportunities", report)
                if "Owego" in listed:
                    self.assertIsNone(scan.category(listed))


if __name__ == "__main__":
    unittest.main()
