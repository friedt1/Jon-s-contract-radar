"""Offline regression checks for scheduled source coverage and feed publication.

These tests inspect workflow configuration only. They never request a bid,
activate a staged source, or publish a purported live opportunity.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent


class WorkflowFreshnessTests(unittest.TestCase):
    def test_staged_probe_refreshes_when_registry_or_adapter_changes(self):
        workflow = (ROOT / ".github/workflows/staged-probe.yml").read_text()
        self.assertIn("  push:\n    branches: [main]\n    paths:\n      - sources.json", workflow)
        for path in ("probe_staged_sources.py", "civicplus_bids.py",
                     "granicus_rfps.py", "robots_policy.py"):
            self.assertIn("      - " + path, workflow)
        self.assertIn("github.event_name == 'push'", workflow)
        self.assertIn("github.ref == 'refs/heads/main'", workflow)
        # A generated diagnostic commit must never trigger another probe.
        self.assertNotIn("\n      - data/staged_probes.json\n", workflow)

    def test_scanner_rebases_on_latest_main_before_publishing(self):
        workflow = (ROOT / ".github/workflows/scan.yml").read_text()
        commit = workflow.index("git commit -m 'Update contract leads and history'")
        rebase = workflow.index("git pull --rebase origin main")
        push = workflow.index("git push origin HEAD:main")
        self.assertLess(commit, rebase)
        self.assertLess(rebase, push)


if __name__ == "__main__":
    unittest.main()
