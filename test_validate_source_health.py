"""Offline regression for real scan-validation failure; no live bids are seeded."""
import json
import tempfile
import unittest
from pathlib import Path

import scan
import source_config
import source_health
import validate_output


class ValidateSourceHealthTests(unittest.TestCase):
    def payload(self):
        sources = json.loads(scan.SOURCES.read_text(encoding="utf-8"))
        statuses = {s["name"]: "indirect RSS ok; 0 candidates" for s in sources}
        # Generic same-host details do not necessarily come from CivicPlus
        # bidID cards; the two counters are not interchangeable.
        statuses["Tioga County NY"] = (
            "direct fetched; 1 listing pages; 2 details checked; "
            "1 individual bid details fetched; 0 candidates"
        )
        # A blocked homepage must still be accounted for in health states.
        statuses["Chemung County bids"] = "direct error: HTTPError HTTP 403"
        health = source_health.summarize(sources, statuses)
        configured = {s["name"] for s in sources
                      if s.get("mode") == "direct_page" and
                      source_config.direct_configured(s)}
        fetched = sum("direct fetched" in statuses[n] for n in configured)
        coverage = {
            "total_targets": len(sources),
            "direct_configured": len(configured),
            "pending_direct": len(sources) - len(configured),
            "direct_fetched": fetched,
            "direct_not_fetched": len(configured) - fetched,
            "indirect_rss_succeeded": sum("indirect RSS ok" in x
                                          for x in statuses.values()),
            "verified_open_contracts": 0,
        }
        statuses["SAM.gov"] = "deferred"
        return sources, {
            "source_status": statuses, "source_coverage": coverage,
            "source_health": health, "opportunities": [],
        }

    def check(self, sources, payload):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data").mkdir()
            (root / "sources.json").write_text(json.dumps(sources))
            (root / "data/opportunities.json").write_text(json.dumps(payload))
            (root / "data/history.json").write_text(
                json.dumps({"opportunities": {}}))
            validate_output.validate(root)

    def test_generic_detail_without_bid_card_count_is_valid(self):
        sources, payload = self.payload()
        row = next(r for r in payload["source_health"]["sources"]
                   if r["name"] == "Tioga County NY")
        self.assertEqual(row["individual_bid_records_found"], 0)
        self.assertEqual(row["individual_bid_details_fetched"], 1)
        self.assertEqual(row["detail_fetches_attempted"], 2)
        self.assertEqual(payload["source_health"]["counts"]["http_blocked"], 1)
        self.check(sources, payload)

    def test_named_inventory_cannot_be_replaced_with_102_other_names(self):
        sources, payload = self.payload()
        payload["source_coverage"]["expected_source_names"] = sorted(
            [s["name"] for s in sources][1:] + ["Unrecognized County"])
        with self.assertRaisesRegex(ValueError, "Expected source inventory"):
            self.check(sources, payload)

    def test_swapped_health_states_fail_even_when_totals_match(self):
        sources, payload = self.payload()
        rows = {row["name"]: row for row in payload["source_health"]["sources"]}
        self.assertEqual(rows["Tioga County NY"]["direct_state"], "fetched_unverified")
        self.assertEqual(rows["Town of Lansing"]["direct_state"], "staged_official_url")
        rows["Tioga County NY"]["direct_state"], rows["Town of Lansing"]["direct_state"] = (
            rows["Town of Lansing"]["direct_state"],
            rows["Tioga County NY"]["direct_state"],
        )
        with self.assertRaisesRegex(ValueError, "Source health state disagrees"):
            self.check(sources, payload)

    def test_balanced_but_forged_health_counts_fail(self):
        sources, payload = self.payload()
        counts = payload["source_health"]["counts"]
        counts["fetched_unverified"] += 1
        counts["not_configured"] -= 1
        with self.assertRaisesRegex(ValueError, "Source health count disagrees"):
            self.check(sources, payload)

    def test_mixed_access_failure_totals_cannot_be_forged(self):
        sources, payload = self.payload()
        # The top-level page can succeed while individual notices fail.
        payload['source_status']['Tioga County NY'] = (
            'direct fetched; 1 listing pages; 2 details checked; '
            '1 individual bid details fetched; '
            '2 detail errors: RobotsDenied,HTTPError HTTP 429; '
            '1 pagination errors: HTTPError HTTP 403'
        )
        payload['source_health'] = source_health.summarize(
            sources, payload['source_status'])
        counts = payload['source_health']['counts']
        self.assertEqual(counts['detail_robots_blocked_sources'], 1)
        self.assertEqual(counts['detail_rate_limited_sources'], 1)
        self.assertEqual(counts['pagination_http_blocked_sources'], 1)
        self.check(sources, payload)

        counts['detail_rate_limited_sources'] = 0
        with self.assertRaisesRegex(ValueError, 'Source health count disagrees'):
            self.check(sources, payload)

    def test_access_failure_row_cannot_hide_mixed_errors(self):
        sources, payload = self.payload()
        payload['source_status']['Tioga County NY'] = (
            'direct fetched; 1 listing pages; 2 details checked; '
            '1 individual bid details fetched; '
            '2 detail errors: RobotsDenied,HTTPError HTTP 429'
        )
        payload['source_health'] = source_health.summarize(
            sources, payload['source_status'])
        row = next(r for r in payload['source_health']['sources']
                   if r['name'] == 'Tioga County NY')
        self.assertEqual(row['detail_error_types'],
                         ['robots_blocked', 'rate_limited'])
        self.check(sources, payload)

        row['detail_error_types'] = ['robots_blocked']
        with self.assertRaisesRegex(ValueError, 'Source health diagnostic disagrees'):
            self.check(sources, payload)

    def test_legacy_health_without_nonexclusive_arrays_remains_readable(self):
        sources, payload = self.payload()
        for row in payload['source_health']['sources']:
            row.pop('detail_error_types', None)
            row.pop('pagination_error_types', None)
        self.check(sources, payload)

    def test_detail_count_still_cannot_exceed_attempts(self):
        sources, payload = self.payload()
        row = next(r for r in payload["source_health"]["sources"]
                   if r["name"] == "Tioga County NY")
        row["individual_bid_details_fetched"] = 3
        payload["source_health"]["counts"]["individual_bid_details_fetched"] = 3
        with self.assertRaisesRegex(ValueError, "exceeds attempted fetches"):
            self.check(sources, payload)


if __name__ == "__main__":
    unittest.main()
