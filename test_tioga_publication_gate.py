"""Offline publication gate regressions; no live bids are created."""
import unittest
from datetime import datetime, timezone
from tioga_publication_gate import publication_decision

BASE = dict(index_deadline='2026-12-01T11:00:00-05:00',
            document_deadline='2026-12-01T16:00:00+00:00',
            checked_at=datetime(2026, 11, 18, tzinfo=timezone.utc),
            official_document_verified=True, eligible_tree_scope=True,
            geographic_match=True)


class PublicationGateTest(unittest.TestCase):
    def test_fully_verified_future_candidate_is_not_auto_published(self):
        self.assertEqual(publication_decision(**BASE),
                         (True, 'verified_candidate_not_publication'))

    def test_no_document_or_no_scope_or_no_geography_fails_closed(self):
        for key in ('official_document_verified', 'eligible_tree_scope', 'geographic_match'):
            with self.subTest(key=key):
                self.assertFalse(publication_decision(**{**BASE, key: False})[0])

    def test_owego_demolition_conflict_and_expiration(self):
        case = {**BASE, 'index_deadline': '2026-11-13T14:00:00-05:00',
                'document_deadline': '2026-11-13T11:00:00-05:00',
                'eligible_tree_scope': False}
        self.assertFalse(publication_decision(**case)[0])
        case['eligible_tree_scope'] = True
        self.assertEqual(publication_decision(**case)[1], 'deadline_conflict')
        case['index_deadline'] = case['document_deadline']
        self.assertEqual(publication_decision(**case)[1], 'expired')

    def test_historical_erie_results_cannot_become_live(self):
        self.assertEqual(publication_decision(**{**BASE, 'historical_or_awarded': True}),
                         (False, 'historical_or_awarded'))

    def test_missing_deadline_or_naive_check_time(self):
        self.assertEqual(publication_decision(**{**BASE, 'document_deadline': None})[1],
                         'deadline_verification_required')
        self.assertEqual(publication_decision(**{**BASE, 'checked_at': datetime(2026, 11, 18)})[1],
                         'check_time_unverified')

    def test_naive_or_malformed_deadline_fails_closed(self):
        for deadline in ('2026-12-01T11:00:00', 'not-a-date', '', None):
            with self.subTest(deadline=deadline):
                self.assertEqual(
                    publication_decision(**{**BASE, 'document_deadline': deadline})[0],
                    False)

    def test_timezone_equivalent_deadlines_are_consistent(self):
        self.assertEqual(
            publication_decision(**{**BASE,
                'index_deadline': '2026-12-01T11:00:00-05:00',
                'document_deadline': '2026-12-01T16:00:00+00:00'}),
            (True, 'verified_candidate_not_publication'))

    def test_non_boolean_evidence_flags_fail_closed(self):
        for key in ('official_document_verified', 'eligible_tree_scope',
                    'geographic_match', 'historical_or_awarded'):
            for value in ('False', 'True', None, 0, 1, []):
                with self.subTest(key=key, value=value):
                    self.assertEqual(publication_decision(**{**BASE, key: value}),
                                     (False, 'invalid_evidence_flags'))

    def test_invalid_check_times_fail_closed(self):
        # Malformed clocks must not be interpreted as a valid scan timestamp.
        for checked_at in (None, '2026-11-18T00:00:00Z', 0, {}, datetime(2026, 11, 18)):
            with self.subTest(checked_at=checked_at):
                self.assertEqual(
                    publication_decision(**{**BASE, 'checked_at': checked_at}),
                    (False, 'check_time_unverified'))

    def test_offset_aware_clock_at_deadline_is_expired(self):
        # Different offsets representing the same instant cannot reopen a bid.
        from datetime import timedelta
        eastern = timezone(timedelta(hours=-5))
        self.assertEqual(
            publication_decision(**{**BASE,
                'checked_at': datetime(2026, 12, 1, 11, tzinfo=eastern)}),
            (False, 'expired'))

    def test_exact_deadline_is_not_open(self):
        self.assertEqual(publication_decision(**{**BASE,
            'checked_at': datetime(2026, 12, 1, 16, tzinfo=timezone.utc)})[1], 'expired')


if __name__ == '__main__':
    unittest.main()
