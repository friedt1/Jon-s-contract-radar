"""Offline deadline-field regressions for Granicus staging, never live leads."""
import datetime as dt
import unittest

import granicus_rfps as granicus
import probe_staged_sources as staged
import scan

ENTRY = "https://www.binghamton-ny.gov/government/departments/purchasing/bids-rfps"
NOTICE = "https://www.binghamton-ny.gov/Home/Components/RFP/RFP/420/90"


def row_html(cells, title="Emergency tree removal"):
    return ('<table><tr><td><a href="/Home/Components/RFP/RFP/420/90">'
            + title + '</a></td>' + ''.join('<td>' + cell + '</td>' for cell in cells)
            + '<td>Open</td></tr></table>')


def record(cells):
    return granicus.listing_records(scan.parse_html(row_html(cells)), ENTRY)[0]


class GranicusDeadlineFieldEvidenceTests(unittest.TestCase):
    def test_explicit_close_date_wins_over_question_and_start_dates(self):
        result = record(["Start Date: 09/01/2026",
                         "Questions Due: 09/20/2026 5:00 PM",
                         "Close Date: 11/02/2026 10:30 AM"])
        self.assertEqual(result["deadline"], "2026-11-02")
        self.assertEqual(result["deadline_time"], "10:30 AM")

    def test_question_deadline_is_not_submission_cutoff(self):
        result = record(["Start Date: 09/01/2026",
                         "Questions Due: 09/20/2026 5:00 PM"])
        self.assertEqual(result["deadline"], "")
        self.assertEqual(result["deadline_time"], "")

    def test_unlabeled_three_dates_cannot_select_second_date(self):
        result = record(["09/01/2026", "09/20/2026", "11/02/2026"])
        self.assertEqual(result["deadline"], "")

    def test_malformed_explicit_close_does_not_borrow_other_date(self):
        result = record(["Start Date: 09/01/2026",
                         "Close Date: TBD",
                         "Pre-bid meeting: 09/20/2026"])
        self.assertEqual(result["deadline"], "")

    def test_original_two_column_start_close_layout_remains_supported(self):
        result = record(["09/01/2026", "11/02/2026 10:30 AM"])
        self.assertEqual(result["deadline"], "2026-11-02")
        self.assertEqual(result["deadline_time"], "10:30 AM")

    def test_erie_and_owego_examples_remain_diagnostic_only(self):
        html = ('<table><tr><td><a href="/Home/Components/RFP/RFP/420/90">'
                'Erie historical tree and stump removal</a></td>'
                '<td>09/01/2025</td><td>10/01/2025</td><td>Closed</td></tr>'
                '<tr><td><a href="/Home/Components/RFP/RFP/421/90">'
                'Owego demolition</a></td><td>09/01/2026</td>'
                '<td>11/02/2026</td><td>Open</td></tr></table>')
        detail = ('<h1>Historical bid</h1><p>Start Date: 09/01/2025</p>'
                  '<p>Close Date: 10/01/2025</p><p>Status: Closed</p>')
        source = {"name": "City of Binghamton", "mode": "discovery_pending",
                  "candidate_official_url": ENTRY, "activation_gate": "terms review"}

        def fetch(url, binary=False):
            if url == ENTRY:
                return html, "text/html", url
            return detail.encode(), "text/html", url

        result = staged.build([source], fetch=fetch,
                              now=dt.datetime(2026, 10, 30, tzinfo=dt.timezone.utc))
        self.assertEqual(result["probes"][0]["individual_records_discovered"], 2)
        self.assertFalse(result["probes"][0]["direct_monitoring_activated"])
        self.assertNotIn("opportunities", result)


if __name__ == "__main__":
    unittest.main()
