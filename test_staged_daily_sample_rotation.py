"""Offline staged-source sample rotation tests; no bids enter production."""
import datetime as dt
import unittest

import probe_staged_sources as staged


UTC = dt.timezone.utc
DAY = dt.datetime(2026, 11, 1, 18, tzinfo=UTC)


def notice(number, title="Tree removal", due="2026-11-19", status="open"):
    return {
        "url": f"https://county.example/Bids.aspx?bidID={number}",
        "title": title,
        "description": title,
        "deadline": due,
        "deadline_time": "2:00 PM",
        "open_status": status,
    }


class StagedDailySampleRotationTests(unittest.TestCase):
    def test_equal_priority_notices_all_sampled_in_three_days(self):
        records = [notice(n) for n in range(9)]
        seen = set()
        batches = []
        for days in range(3):
            chosen = staged._daily_sample_candidates(
                records, DAY + dt.timedelta(days=days))
            self.assertEqual(len(chosen), 3)
            batches.append(tuple(row["url"] for row in chosen))
            seen.update(row["url"] for row in chosen)
        self.assertEqual(seen, {row["url"] for row in records})
        self.assertEqual(len(set(batches)), 3)

    def test_same_utc_day_is_stable_and_input_is_not_modified(self):
        records = [notice(n) for n in range(8)]
        original = records.copy()
        morning = DAY.replace(hour=1)
        evening = DAY.replace(hour=23)
        self.assertEqual(
            staged._daily_sample_candidates(records, morning),
            staged._daily_sample_candidates(records, evening))
        self.assertEqual(records, original)

    def test_higher_priority_notices_remain_ahead_of_tied_boundary(self):
        records = ([notice(0, "Hazardous tree removal"),
                    notice(1, "Hazardous tree removal")]
                   + [notice(n, "Office furniture") for n in range(2, 10)]
                   + [notice(10, "Erie tree and stump removal",
                             due="2026-10-28")])
        sampled = set()
        for days in range(8):
            chosen = staged._daily_sample_candidates(
                records, DAY + dt.timedelta(days=days))
            self.assertEqual([row["url"] for row in chosen[:2]],
                             [records[0]["url"], records[1]["url"]])
            self.assertNotIn(records[-1], chosen)
            sampled.add(chosen[2]["url"])
        self.assertEqual(sampled, {row["url"] for row in records[2:10]})

    def test_expired_and_excluded_scope_never_preempt_future_notices(self):
        future = [notice(n, "Office furniture") for n in range(3)]
        expired = [notice(10 + n, "Erie tree and stump removal",
                          due="2026-10-28") for n in range(8)]
        excluded = notice(99, "Owego demolition; tree removal by others",
                          due="2026-10-28")
        for days in range(5):
            chosen = staged._daily_sample_candidates(
                future + expired + [excluded],
                DAY + dt.timedelta(days=days))
            self.assertEqual(chosen, future)

    def test_no_extra_requests_when_fewer_notices_or_zero_budget(self):
        records = [notice(1), notice(2)]
        self.assertEqual(staged._daily_sample_candidates(records, DAY), records)
        self.assertEqual(staged._daily_sample_candidates(records, DAY, 0), [])


if __name__ == "__main__":
    unittest.main()
