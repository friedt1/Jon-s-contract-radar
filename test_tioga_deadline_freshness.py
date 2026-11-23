"""Offline regression only: no fixture represents an active solicitation."""
import unittest
from tioga_notice_sections import deadline_open_status


class DeadlineFreshnessTests(unittest.TestCase):
    def test_owego_demolition_deadline_elapsed(self):
        deadline = '2026-11-13T14:00:00-05:00'
        self.assertEqual(deadline_open_status(deadline, deadline,
                         '2026-11-18T20:00:00-05:00'), 'deadline_elapsed')

    def test_exact_deadline_is_not_open(self):
        deadline = '2026-11-13T14:00:00-05:00'
        self.assertEqual(deadline_open_status(deadline, deadline, deadline),
                         'deadline_elapsed')

    def test_timezone_equivalent_evidence_is_consistent(self):
        self.assertEqual(deadline_open_status('2026-12-01T11:00:00-05:00',
                         '2026-12-01T16:00:00+00:00',
                         '2026-11-18T20:00:00-05:00'),
                         'deadline_future_unverified')

    def test_future_deadline_never_proves_live_bid(self):
        future = '2026-12-01T11:00:00-05:00'
        self.assertEqual(deadline_open_status(future, future,
                         '2026-11-18T20:00:00-05:00'),
                         'deadline_future_unverified')

    def test_conflicting_and_missing_evidence_fail_closed(self):
        deadline = '2026-12-01T11:00:00-05:00'
        for index, doc in ((deadline, None), (None, deadline),
                           (deadline, '2026-12-02T11:00:00-05:00'),
                           ('2026-12-01T11:00:00', deadline)):
            with self.subTest(index=index, doc=doc):
                self.assertEqual(deadline_open_status(index, doc,
                                 '2026-11-18T20:00:00-05:00'),
                                 'verification_required')

    def test_invalid_or_naive_current_time_fails_closed(self):
        deadline = '2026-12-01T11:00:00-05:00'
        for now in (None, '', '2026-11-18T20:00:00', 'not a date', 123):
            with self.subTest(now=now):
                self.assertEqual(deadline_open_status(deadline, deadline, now),
                                 'verification_required')

    def test_noncanonical_iso_dates_fail_closed(self):
        canonical = '2026-12-01T11:00:00-05:00'
        invalid = (
            '20261201T110000-05:00',
            '2026-W49-2T11:00:00-05:00',
            '2026-12-01 11:00:00-05:00',
            '2026-12-01T11:00-05:00',
            '2026-12-01T11:00:00',
        )
        for value in invalid:
            with self.subTest(value=value):
                self.assertEqual(deadline_open_status(value, value,
                                 '2026-11-18T20:00:00-05:00'),
                                 'verification_required')
                self.assertEqual(deadline_open_status(canonical, canonical,
                                 value), 'verification_required')

    def test_utc_z_and_numeric_offset_agree(self):
        self.assertEqual(deadline_open_status('2026-12-01T16:00:00Z',
                         '2026-12-01T11:00:00-05:00',
                         '2026-11-18T20:00:00-05:00'),
                         'deadline_future_unverified')
