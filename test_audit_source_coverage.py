import unittest

from audit_source_coverage import audit, strict_failures


class CoverageAuditTests(unittest.TestCase):
    def test_indirect_is_not_direct(self):
        result = audit([{"name": "County", "mode": "discovery_pending", "url": "",
                         "verified_url": False}])
        self.assertEqual(result["not_directly_monitored"], 1)

    def test_homepage_without_verified_url_is_not_direct(self):
        result = audit([{"name": "County", "mode": "direct_page",
                         "url": "https://example.org", "verified_url": False}])
        self.assertEqual(result["direct_configured"], 0)

    def test_direct_configuration_is_not_live_verification(self):
        result = audit([{"name": "County", "mode": "direct_page",
                         "url": "https://example.org/bids", "verified_url": True}])
        self.assertEqual(result["direct_configured"], 1)
        self.assertIn("not independently verified", result["sources"][0]["status"])

    def test_unconnected_portal_urls_are_not_fetch_targets(self):
        result = audit([
            {"name": "PennBid platform", "mode": "direct_page",
             "url": "https://pennbid.bonfirehub.com", "verified_url": True},
            {"name": "BidNet NY platform", "mode": "direct_page",
             "url": "https://www.bidnetdirect.com/new-york", "verified_url": True},
            {"name": "Chemung County bids", "mode": "direct_page",
             "url": "https://chemungcountyny.gov/Bids.aspx", "verified_url": True},
            {"name": "Pending", "mode": "discovery_pending", "url": "",
             "verified_url": False},
        ])
        self.assertEqual(result["total"], 4)
        self.assertEqual(result["direct_configured"], 3)
        self.assertEqual(result["direct_fetch_targets"], 1)
        self.assertEqual(result["configured_provider_access_required"], 2)
        self.assertEqual(result["not_directly_monitored"], 1)
        for row in result["sources"][:2]:
            self.assertTrue(row["provider_access_required"])
            self.assertFalse(row["direct_fetch_target"])
            self.assertIn("not connected", row["status"])
        self.assertTrue(result["sources"][2]["direct_fetch_target"])
        self.assertFalse(result["sources"][3]["direct_fetch_target"])

    def test_platform_name_alias_cannot_bypass_access_gate(self):
        # Inventory display casing/whitespace is not an authorization signal.
        rows = [
            {"name": "  pennbid   PLATFORM ", "mode": "direct_page",
             "url": "https://pennbid.bonfirehub.com", "verified_url": True},
            {"name": "bidnet ny PLATFORM", "mode": "direct_page",
             "url": "https://www.bidnetdirect.com/new-york", "verified_url": True},
        ]
        result = audit(rows)
        self.assertEqual(result["direct_configured"], 2)
        self.assertEqual(result["configured_provider_access_required"], 2)
        self.assertEqual(result["direct_fetch_targets"], 0)
        self.assertTrue(all(row["provider_access_required"] for row in result["sources"]))
        self.assertTrue(any("provider access required: 2" in reason
                            for reason in strict_failures(result, expected_targets=2)))

    def test_staged_platform_alias_requires_provider_access(self):
        # Moving an unconnected platform from direct to staged must not
        # silently downgrade its authorization blocker.
        rows = [
            {"name": "  pennbid   PLATFORM ", "mode": "discovery_pending",
             "candidate_official_url": "https://pennbid.bonfirehub.com"},
            {"name": "BidNet NY platform", "mode": "discovery_pending",
             "candidate_official_url": "https://www.bidnetdirect.com/new-york"},
        ]
        report = audit(rows)
        self.assertEqual(report["staged_provider_access_required"], 2)
        self.assertEqual(report["direct_fetch_targets"], 0)
        for row in report["sources"]:
            self.assertTrue(row["staged_provider_access_required"])
            self.assertIn("provider_authorization_required", row["activation_blockers"])
            self.assertIn("authorization required", row["status"])

    def test_staged_urls_are_not_active_connections(self):
        result = audit([
            {"name": "Staged", "mode": "discovery_pending", "url": "",
             "verified_url": False, "candidate_official_url": "https://county.example/bids",
             "activation_gate": "Review robots and individual bid extraction"},
            {"name": "Unknown", "mode": "discovery_pending", "url": "",
             "verified_url": False},
            {"name": "Broken direct", "mode": "direct_page", "url": "",
             "verified_url": True},
        ])
        self.assertEqual(result["not_directly_monitored"], 3)
        self.assertEqual(result["official_urls_staged"], 1)
        self.assertEqual(result["discovery_required"], 1)
        self.assertEqual(result["invalid_direct_configurations"], 1)
        self.assertFalse(result["sources"][0]["direct_fetch_target"])
        self.assertIn("not verified", result["sources"][0]["status"])
        self.assertEqual(result["sources"][0]["candidate_official_url"],
                         "https://county.example/bids")
        self.assertIn("robots", result["sources"][0]["activation_gate"])

    def test_invalid_staged_candidate_is_diagnosed_not_activated(self):
        rows = [
            {"name": "Private network", "mode": "discovery_pending",
             "candidate_official_url": "https://127.0.0.1/bids"},
            {"name": "Insecure", "mode": "discovery_pending",
             "candidate_official_url": "http://county.example/bids"},
            {"name": "Valid staged", "mode": "discovery_pending",
             "candidate_official_url": "https://county.example/bids"},
            {"name": "Unknown", "mode": "discovery_pending"},
        ]
        report = audit(rows)
        self.assertEqual(report["invalid_staged_candidate_urls"], 2)
        self.assertEqual(report["official_urls_staged"], 1)
        self.assertEqual(report["discovery_required"], 1)
        self.assertEqual(report["direct_fetch_targets"], 0)
        for row in report["sources"][:2]:
            self.assertTrue(row["invalid_staged_candidate_url"])
            self.assertFalse(row["official_url_staged"])
            self.assertIsNone(row["candidate_official_url"])
            self.assertIn("invalid staged candidate URL", row["status"])
        self.assertFalse(report["sources"][2]["invalid_staged_candidate_url"])
        self.assertFalse(report["sources"][3]["invalid_staged_candidate_url"])

    def test_publisher_homepage_does_not_masquerade_as_bid_index(self):
        sources = [
            {"name": "Homepage", "mode": "discovery_pending", "url": "",
             "verified_url": False, "candidate_official_url": "https://county.example/",
             "official_page_role": "publisher_entrypoint_only"},
            {"name": "Bid index", "mode": "discovery_pending", "url": "",
             "verified_url": False, "candidate_official_url": "https://town.example/Bids.aspx"},
        ]
        result = audit(sources)
        self.assertEqual(result["official_urls_staged"], 2)
        self.assertEqual(result["staged_publisher_entrypoints_only"], 1)
        self.assertEqual(result["direct_configured"], 0)
        self.assertTrue(result["sources"][0]["staged_publisher_entrypoint_only"])
        self.assertIn("bid index not identified", result["sources"][0]["status"])
        self.assertFalse(result["sources"][1]["staged_publisher_entrypoint_only"])

    def test_strict_gate_rejects_missing_target_even_if_every_remaining_page_is_direct(self):
        # A silently dropped agency must not make a 101/101 direct audit pass.
        rows = [
            {"name": f"Agency {n}", "mode": "direct_page",
             "url": f"https://agency{n}.example/bids", "verified_url": True}
            for n in range(101)
        ]
        report = audit(rows)
        self.assertEqual(report["not_directly_monitored"], 0)
        self.assertEqual(report["direct_fetch_targets"], 101)
        blockers = strict_failures(report)
        self.assertTrue(any("inventory rows: 101" in b for b in blockers))
        self.assertTrue(any("unique named targets: 101" in b for b in blockers))

    def test_strict_gate_rejects_unnamed_and_duplicate_target_rows(self):
        rows = [
            {"name": f"Agency {n}", "mode": "direct_page",
             "url": f"https://agency{n}.example/bids", "verified_url": True}
            for n in range(100)
        ]
        rows += [
            {"name": "Agency 0", "mode": "direct_page",
             "url": "https://duplicate.example/bids", "verified_url": True},
            {"name": "   ", "mode": "direct_page",
             "url": "https://unnamed.example/bids", "verified_url": True},
        ]
        report = audit(rows)
        self.assertEqual(report["total"], 102)
        self.assertEqual(report["unique_named_targets"], 100)
        self.assertEqual(report["unnamed_source_rows"], 1)
        self.assertEqual(report["duplicate_source_rows"], 1)
        self.assertFalse(report["inventory_integrity_ok"])
        self.assertTrue(any("inventory names invalid" in b
                            for b in strict_failures(report)))

    def test_case_and_whitespace_aliases_cannot_inflate_named_inventory(self):
        # A 102-row inventory can otherwise hide a missing agency behind
        # differently formatted copies of another named source.
        rows = [
            {"name": "Tioga County NY", "mode": "direct_page",
             "url": "https://county.example/bids", "verified_url": True},
            {"name": "  tIoGa   COUNTY NY  ", "mode": "direct_page",
             "url": "https://duplicate.example/bids", "verified_url": True},
            {"name": "Other County", "mode": "direct_page",
             "url": "https://other.example/bids", "verified_url": True},
        ]
        report = audit(rows)
        self.assertEqual(report["total"], 3)
        self.assertEqual(report["unique_named_targets"], 2)
        self.assertEqual(report["duplicate_source_rows"], 1)
        self.assertEqual(report["duplicate_source_names"], ["Tioga County NY"])
        self.assertEqual([r["duplicate_source_name"] for r in report["sources"]],
                         [True, True, False])
        self.assertEqual(report["sources"][1]["source"], "tIoGa COUNTY NY")
        self.assertTrue(any("inventory names invalid" in b
                            for b in strict_failures(report, expected_targets=3)))

    def test_strict_gate_is_structural_not_live_extraction_proof(self):
        rows = [
            {"name": f"Agency {n}", "mode": "direct_page",
             "url": f"https://agency{n}.example/bids", "verified_url": True}
            for n in range(102)
        ]
        report = audit(rows)
        self.assertEqual(strict_failures(report), [])
        self.assertIn("not independently verified", report["sources"][0]["status"])
        self.assertTrue(any("inventory rows" in b
                            for b in strict_failures(report, expected_targets=103)))

    def test_staged_supplier_gateway_requires_authorization_not_fetch(self):
        rows = [
            {"name": "County supplier portal", "mode": "discovery_pending",
             "candidate_official_url": "https://county.example/vendor",
             "provider_access_required": True},
            {"name": "Delegated city portal", "mode": "discovery_pending",
             "candidate_official_url": "https://city.example/bids",
             "delegated_provider": "Supplier gateway"},
        ]
        report = audit(rows)
        self.assertEqual(report["staged_provider_access_required"], 2)
        self.assertEqual(report["official_urls_staged"], 2)
        self.assertEqual(report["direct_fetch_targets"], 0)
        self.assertEqual(report["direct_configured"], 0)
        for row in report["sources"]:
            self.assertTrue(row["staged_provider_access_required"])
            self.assertFalse(row["direct_fetch_target"])
            self.assertIn("authorization required", row["status"])

    def test_shared_gateway_does_not_count_duplicate_agency_as_second_publisher(self):
        rows = [
            {"name": "Tioga County", "mode": "discovery_pending",
             "candidate_official_url": "https://procurement.example/bids?utm_source=one"},
            {"name": " TIOGA  COUNTY ", "mode": "discovery_pending",
             "candidate_official_url": "https://procurement.example/bids?utm_source=two"},
            {"name": "Owego", "mode": "discovery_pending",
             "candidate_official_url": "https://procurement.example/bids"},
        ]
        report = audit(rows)
        self.assertEqual(report["unique_named_targets"], 2)
        self.assertEqual(report["duplicate_source_rows"], 1)
        self.assertEqual(report["distinct_official_entrypoints"], 1)
        self.assertEqual(report["shared_official_entrypoint_targets"], 2)
        self.assertEqual(len(report["shared_official_entrypoint_groups"]), 1)
        self.assertTrue(all(row["shared_official_entrypoint"] for row in report["sources"]))
        self.assertEqual(report["direct_fetch_targets"], 0)

    def test_current_102_source_inventory_is_accounted_for(self):
        import json
        from pathlib import Path
        sources = json.loads((Path(__file__).parent / "sources.json").read_text())
        result = audit(sources)
        self.assertEqual(result["total"], 102)
        self.assertEqual(
            result["direct_configured"] + result["official_urls_staged"]
            + result["invalid_direct_configurations"] + result["invalid_staged_candidate_urls"]
            + result["discovery_required"],
            102,
        )
        self.assertEqual(result["not_directly_monitored"],
                         result["official_urls_staged"] + result["invalid_direct_configurations"]
                         + result["invalid_staged_candidate_urls"] + result["discovery_required"])


if __name__ == "__main__":
    unittest.main()
