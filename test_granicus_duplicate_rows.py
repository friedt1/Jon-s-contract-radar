"""Synthetic Granicus duplicate-row regressions; never publish these as bids."""
import datetime as dt
import unittest

import granicus_rfps
import probe_staged_sources as staged
import scan

ENTRY = "https://www.binghamton-ny.gov/government/departments/purchasing/bids-rfps"
NOTICE = "https://www.binghamton-ny.gov/Home/Components/RFP/RFP/420/90"
SOURCE = {"name": "City of Binghamton", "mode": "discovery_pending",
          "candidate_official_url": ENTRY, "activation_gate": "terms review"}


def row(title, due, status, number=420):
    return (
        '<tr><td><a href="/Home/Components/RFP/RFP/'
        + str(number) + '/90">' + title + '</a></td>'
        '<td>09/01/2026</td><td>' + due + '</td>'
        '<td>' + status + '</td></tr>'
    )


def records(html):
    return granicus_rfps.listing_records(scan.parse_html("<table>" + html + "</table>"), ENTRY)


class GranicusDuplicateEvidenceTests(unittest.TestCase):
    def test_same_notice_conflicting_rows_cannot_look_open_or_have_one_deadline(self):
        entries = records(
            row("BID: Tree and stump removal", "11/20/2026 2:00 PM", "Open")
            + row("BID: Tree and stump removal", "10/01/2026 10:30 AM", "Closed")
        )
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["url"], NOTICE)
        self.assertEqual(entries[0]["open_status"], "unknown")
        self.assertEqual(entries[0]["deadline"], "")
        self.assertEqual(entries[0]["deadline_time"], "")
        self.assertTrue(entries[0]["listing_status_conflict"])
        self.assertTrue(entries[0]["listing_deadline_conflict"])
        self.assertEqual(entries[0]["listing_status_evidence"], ["closed", "open"])
        self.assertEqual(len(entries[0]["listing_deadline_evidence"]), 2)

    def test_same_date_different_submission_times_is_a_conflict(self):
        entry = records(
            row("BID: Tree removal", "11/20/2026 9:00 AM", "Open")
            + row("BID: Tree removal", "11/20/2026 2:00 PM", "Open")
        )[0]
        self.assertEqual(entry["deadline"], "")
        self.assertTrue(entry["listing_deadline_conflict"])
        self.assertFalse(entry["listing_status_conflict"])

    def test_identical_rows_and_closed_awarded_are_not_false_conflicts(self):
        same = records(
            row("BID: Tree removal", "11/20/2026 10:30 AM", "Open")
            + row("BID: Tree removal", "11/20/2026 10:30 AM", "Open")
        )[0]
        self.assertEqual(same["deadline"], "2026-11-20")
        self.assertEqual(same["deadline_time"], "10:30 AM")
        self.assertEqual(same["open_status"], "open")
        self.assertFalse(same["listing_deadline_conflict"])
        self.assertFalse(same["listing_status_conflict"])

        closed = records(
            row("BID: Tree removal", "10/01/2026", "Closed")
            + row("BID: Tree removal", "10/01/2026", "Awarded")
        )[0]
        self.assertEqual(closed["open_status"], "closed")
        self.assertFalse(closed["listing_status_conflict"])

    def test_independent_bid_ids_keep_independent_row_evidence(self):
        entries = records(
            row("BID: Tree trimming", "11/20/2026", "Open")
            + row("BID: Owego demolition", "10/01/2026", "Closed", number=421)
        )
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["deadline"], "2026-11-20")
        self.assertEqual(entries[0]["open_status"], "open")
        self.assertEqual(entries[1]["deadline"], "2026-10-01")
        self.assertEqual(entries[1]["open_status"], "closed")
        self.assertFalse(any(entry["listing_status_conflict"] for entry in entries))
        self.assertIsNone(scan.category("BID: Owego demolition"))

    def test_probe_preserves_conflicts_even_if_one_detail_agrees(self):
        html = ("<table>"
                + row("BID: Tree removal", "11/20/2026 2:00 PM", "Open")
                + row("BID: Tree removal", "10/01/2026 10:30 AM", "Closed")
                + "</table>")
        detail = ('<h1>BID: Tree removal</h1><p>Start Date: 09/01/2026</p>'
                  '<p>Close Date: 11/20/2026 2:00 PM</p>'
                  '<p>Description: Synthetic tree work.</p>')
        def fetch(url, binary=False):
            return ((html, "text/html", url) if url == ENTRY else
                    (detail.encode(), "text/html", url))
        result = staged.build(
            [SOURCE], fetch=fetch,
            now=dt.datetime(2026, 10, 31, 4, 30, tzinfo=dt.timezone.utc)
        )
        sample = result["probes"][0]
        self.assertTrue(sample["individual_notice_retrieved"])
        self.assertTrue(sample["sample_notice_status_conflict"])
        self.assertTrue(sample["sample_notice_deadline_conflict"])
        self.assertEqual(sample["sample_notice_temporal_evidence"],
                         "conflicting_status_unverified")
        self.assertFalse(sample["direct_monitoring_activated"])
        self.assertNotIn("opportunities", result)


if __name__ == "__main__":
    unittest.main()
