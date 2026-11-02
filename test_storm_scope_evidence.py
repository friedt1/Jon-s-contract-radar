"""Synthetic storm-work scope regressions; no live notices or manual seeding."""
import datetime as dt
import unittest

import scan


NOW = dt.datetime(2026, 11, 2, 18, tzinfo=dt.timezone.utc)


class StormScopeEvidenceTests(unittest.TestCase):
    def test_generic_storm_damage_is_not_a_tree_contract(self):
        for notice in (
            "Storm damage bid to replace municipal roof shingles",
            "Emergency storm response RFP for electrical panel replacement",
            "Storm damage repair contract for a washed-out bridge",
            "Storm response bid for HVAC and building repairs",
        ):
            with self.subTest(notice=notice):
                self.assertIsNone(scan.category(notice))
                self.assertFalse(scan.eligible(notice, today=NOW.date(), now=NOW))

    def test_explicit_storm_tree_and_debris_scope_stays_discoverable(self):
        for notice, expected in (
            ("Storm debris removal bid along county highways", "Storm cleanup"),
            ("Downed trees cleanup contract along a roadway", "Storm cleanup"),
            ("Fallen trees removal bid after windstorm", "Storm cleanup"),
            ("Storm-damaged trees cleanup RFP", "Storm cleanup"),
            ("Storm damaged tree cleanup contract", "Storm cleanup"),
            ("Storm response bid for hazardous tree removal", "Tree removal"),
            ("Storm cleanup bid for woody debris removal", "Storm cleanup"),
        ):
            with self.subTest(notice=notice):
                self.assertEqual(scan.category(notice), expected)
                self.assertTrue(scan.eligible(notice, today=NOW.date(), now=NOW))

    def test_unrelated_storm_notice_does_not_enter_candidate_feed(self):
        found = {}
        scan.add_lead(
            found, "Synthetic County",
            "Storm damage repair RFP",
            "https://county.example/bids?bidID=911",
            "Repair roof flashing and damaged HVAC units",
        )
        self.assertEqual(found, {})

    def test_historical_erie_and_owego_remain_negative_controls(self):
        self.assertFalse(scan.eligible(
            "Erie tree and stump removal bid due October 28, 2026",
            today=NOW.date(), now=NOW,
        ))
        self.assertFalse(scan.eligible(
            "Owego demolition rebid due November 13, 2026; tree removal by others",
            today=NOW.date(), now=NOW,
        ))


if __name__ == "__main__":
    unittest.main()
