"""Offline feed-validator regressions; all bid records are synthetic fixtures.

No fixture is inserted into production opportunities or represented as live work.
"""
import datetime as dt
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import scan
import validate_output


class FeedValidationRegressions(unittest.TestCase):
    NOW = dt.datetime(2026, 10, 30, 17, 0, tzinfo=dt.timezone.utc)  # 1 PM Eastern

    def notice(self, **overrides):
        lead = {
            "id": "synthetic-erie-style-tree-stump",
            "title": "Tree and stump removal sealed bid",
            "summary": "Sealed bid for tree and stump removal in Chemung County",
            "url": "https://county.example/Bids.aspx?bidID=321",
            "source": "Chemung County bids",
            "location": "Chemung County, NY",
            "category": "Tree removal",
            "published": "2026-10-30",
            "status": "unverified",
            "open_status": "unverified",
            "lead_type": "individual county bid candidate",
            "deadline": "2026-10-30",
            "deadline_time": "9:00 AM",
            "deadline_timezone": "America/New_York",
            "deadline_status": "date_and_time_unverified",
            "review_priority": "review",
        }
        lead.update(overrides)
        return lead

    def validate_fixture(self, lead):
        # Exercise the full validator, not only its new helper. Use all 102
        # real target names but no production feed/history mutations.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "data").mkdir()
            sources = json.loads(scan.SOURCES.read_text(encoding="utf-8"))
            (root / "sources.json").write_text(json.dumps(sources), encoding="utf-8")
            statuses = {src["name"]: "indirect RSS error: RobotsDenied" for src in sources}
            statuses["SAM.gov"] = "deferred"
            feed = {"source_status": statuses, "opportunities": [lead]}
            (root / "data/opportunities.json").write_text(json.dumps(feed), encoding="utf-8")
            history = {"opportunities": {lead["id"]: lead}}
            (root / "data/history.json").write_text(json.dumps(history), encoding="utf-8")
            with patch.object(scan, "NOW", self.NOW):
                validate_output.validate(root)

    def test_erie_style_elapsed_same_day_cutoff_cannot_be_published(self):
        with self.assertRaisesRegex(ValueError, "Elapsed submission cutoff"):
            self.validate_fixture(self.notice())

    def test_future_same_day_clock_remains_unverified_not_auto_closed(self):
        self.validate_fixture(self.notice(deadline_time="6:00 PM"))

    def test_date_only_and_incompatible_timezone_are_not_guessed(self):
        self.validate_fixture(self.notice(deadline_time=""))
        self.validate_fixture(self.notice(deadline_timezone="America/Chicago"))

    def test_publisher_award_or_withdrawal_cannot_survive_feed_validation(self):
        for status in ("Bid Status: Awarded", "Solicitation Status - Withdrawn"):
            with self.subTest(status=status):
                with self.assertRaisesRegex(ValueError, "Closed/expired notice"):
                    self.validate_fixture(self.notice(
                        deadline="2026-11-05", deadline_time="", open_status=status))

    def test_expired_triage_priority_cannot_be_published(self):
        with self.assertRaisesRegex(ValueError, "Closed/expired notice"):
            self.validate_fixture(self.notice(
                deadline="2026-11-05", deadline_time="", review_priority="expired_check"))

    def test_malformed_or_credentialed_notice_urls_cannot_be_published(self):
        # No production records: synthetic feed/history in a temporary folder.
        urls = (
            "https://user:pass@county.example/Bids.aspx?bidID=321",
            "https://county.example:bad/Bids.aspx?bidID=321",
            "https://county.example/Bids.aspx?bidID=321" + chr(10) + "X-Injected:yes",
            "javascript:alert(1)",
            "https://[broken/Bids.aspx?bidID=321",
        )
        for url in urls:
            with self.subTest(url=url):
                with self.assertRaisesRegex(ValueError, "Invalid URL"):
                    self.validate_fixture(self.notice(
                        url=url, deadline="2026-11-05", deadline_time=""))

    def test_encoded_control_notice_urls_cannot_be_published(self):
        # The final publication gate must reject encoded control bytes even
        # when the source page did not contain a literal newline.
        for url in (
            "https://county.example/Bids.aspx?bidID=321%0aX-Injected",
            "https://county.example/Bids.aspx?bidID=321%0D",
            "https://county.example/Bids.aspx%00?bidID=321",
            "https://county.example/Bids.aspx?bidID=321#details%7f",
        ):
            with self.subTest(url=url):
                with self.assertRaisesRegex(ValueError, "Invalid URL"):
                    self.validate_fixture(self.notice(
                        url=url, deadline="2026-11-05", deadline_time=""))

    def test_valid_http_and_https_notice_urls_remain_unverified(self):
        for url in ("http://county.example/Bids.aspx?bidID=321",
                    "https://county.example/Bids.aspx?bidID=321"):
            with self.subTest(url=url):
                self.validate_fixture(self.notice(
                    url=url, deadline="2026-11-05", deadline_time=""))

    def test_owego_demolition_without_tree_scope_is_still_ineligible(self):
        with self.assertRaisesRegex(ValueError, "Ineligible lead"):
            self.validate_fixture(self.notice(
                title="Owego building demolition rebid",
                summary="Demolition of a vacant building and site restoration",
                deadline="2026-11-05", deadline_time=""))


if __name__ == "__main__":
    unittest.main()
