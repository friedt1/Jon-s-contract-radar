"""Synthetic rural address privacy tests; no real customer data."""
import datetime as dt
import unittest

import local_scan as radar
from test_local_scan import NOW, SOCIAL, record, timeline


class RuralAddressPrivacyTests(unittest.TestCase):
    def test_rural_house_numbers_redacted_without_removing_road_names(self):
        for address in (
            "2536 Route 49", "1200 State Route 14", "1410 County Road 64",
            "2500 Rte 15", "500 Rt 17", "122 Highway 6",
            "123 County Hwy 4", "126 State Rd 3",
        ):
            with self.subTest(address=address):
                text = "Looking for tree removal at " + address + " in Elmira NY."
                sanitized = radar.redact_public_text(text)
                self.assertNotIn(address, sanitized)
                self.assertIn("[address on source]", sanitized)
        for public_road in ("Route 49", "State Route 14", "County Road 64"):
            self.assertEqual(radar.redact_public_text(public_road), public_road)

    def test_current_lead_redacts_rural_address(self):
        address = "2536 Route 49"
        lead = radar.candidate(record(
            "Looking for tree removal at " + address + " in Elmira NY. Need a quote."
        ), SOCIAL, NOW)
        self.assertIsNotNone(lead)
        for field in ("title", "summary", "evidence_snippet"):
            self.assertNotIn(address, lead[field])
        self.assertEqual(lead["location"], "Elmira, NY")
        self.assertEqual(lead["verification_state"], "unverified_candidate")

    def test_historical_rural_address_redacted_without_losing_identity(self):
        previous_feed, previous = radar.assemble(
            [SOCIAL], {"leads": {}}, NOW,
            getter=lambda _: timeline("Looking for tree removal in Elmira NY. Need a quote."),
            pause=lambda _: None,
        )
        uid = previous_feed["leads"][0]["id"]
        previous["leads"][uid]["summary"] += " at 1200 State Route 14"
        feed, history = radar.assemble(
            [SOCIAL], previous, NOW + dt.timedelta(days=1),
            getter=lambda _: "[]", pause=lambda _: None,
        )
        self.assertEqual(feed["leads"], [])
        self.assertIn(uid, history["leads"])
        self.assertNotIn("1200 State Route 14", history["leads"][uid]["summary"])
        self.assertIn("[address on source]", history["leads"][uid]["summary"])


if __name__ == "__main__":
    unittest.main()
