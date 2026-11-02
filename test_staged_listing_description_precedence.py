"""Listing-card description precedence for staged, unverified procurement probes.

All fixtures are synthetic; Erie is historical and Owego is unrelated.
No test activates a source or publishes a live contract.
"""
import datetime as dt
import unittest

import probe_staged_sources as staged


NOW = dt.datetime(2026, 11, 2, 12, tzinfo=dt.timezone.utc)


def row(title, description, due="2026-11-19"):
    return {
        "title": title, "description": description,
        "deadline": due, "deadline_time": "2:00 PM",
        "open_status": "open",
    }


class StagedListingDescriptionPrecedenceTests(unittest.TestCase):
    def test_explicit_exclusion_overrides_tree_title(self):
        excluded = row("Hazardous tree removal", 
                       "Tree removal by others; purchase office furniture.")
        unrelated = row("Office furniture", "Purchase office furniture.")
        self.assertIsNone(staged._listing_scope_category(excluded))
        self.assertEqual(staged._sample_priority(excluded, NOW),
                         staged._sample_priority(unrelated, NOW))
        self.assertEqual(
            staged._listing_scope_inventory([excluded], NOW)["listing_relevant_count"], 0)

    def test_unrelated_specific_description_overrides_tree_title(self):
        misleading = row("Hazardous tree removal", "Purchase desks and chairs.")
        self.assertIsNone(staged._listing_scope_category(misleading))
        self.assertEqual(
            staged._listing_scope_inventory([misleading], NOW)["listing_relevant_count"], 0)

    def test_specific_tree_description_overrides_generic_title(self):
        tree = row("General maintenance", "Roadside tree trimming and pruning.")
        self.assertEqual(staged._listing_scope_category(tree), "Tree trimming")
        self.assertEqual(
            staged._listing_scope_inventory([tree], NOW)["listing_relevant_count"], 1)

    def test_attachment_only_description_falls_back_to_title(self):
        tree = row("Hazardous tree removal", "See attached specifications.")
        self.assertEqual(staged._listing_scope_category(tree), "Tree removal")
        self.assertEqual(
            staged._listing_scope_inventory([tree], NOW)["listing_relevant_count"], 1)

    def test_erie_expired_and_owego_demolition_stay_nonlive(self):
        erie = row("Erie tree and stump removal",
                   "Tree removal and stump grinding.", due="2026-10-28")
        owego = row("Owego building demolition", "Tree removal by others.")
        inventory = staged._listing_scope_inventory([erie, owego], NOW)
        self.assertEqual(inventory["listing_relevant_count"], 1)
        self.assertEqual(inventory["listing_relevant_by_temporal_evidence"]["closed_or_elapsed"], 1)
        self.assertEqual(inventory["listing_relevant_by_temporal_evidence"]["future_or_today_unverified"], 0)


if __name__ == "__main__":
    unittest.main()
