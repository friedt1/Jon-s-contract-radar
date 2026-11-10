"""Offline regression: missing scan timezone must not expire an NY/PA bid."""
import datetime as dt
import unittest

from submission_deadlines import explicit_closing_passed


class ExplicitCutoffTimezoneTests(unittest.TestCase):
    NOTICE = "Sealed bids due November 10, 2026 at 2:00 PM"

    def test_naive_clock_cannot_expire_bid_using_runner_timezone(self):
        # A naive clock could mean UTC, Eastern, or the CI host's local zone.
        self.assertFalse(explicit_closing_passed(
            self.NOTICE, dt.datetime(2026, 11, 10, 20, 0)))
        self.assertFalse(explicit_closing_passed(self.NOTICE, None))

    def test_aware_utc_clock_is_converted_to_eastern(self):
        self.assertFalse(explicit_closing_passed(
            self.NOTICE, dt.datetime(2026, 11, 10, 18, 59,
                                     tzinfo=dt.timezone.utc)))
        self.assertTrue(explicit_closing_passed(
            self.NOTICE, dt.datetime(2026, 11, 10, 19, 1,
                                     tzinfo=dt.timezone.utc)))


if __name__ == "__main__":
    unittest.main()
