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


    def test_all_generated_feeds_retry_non_force_push_after_rebase(self):
        # A scheduled local scan once passed tests and extraction but lost
        # a race with a concurrent main merge at git push. Retrying must
        # fetch/rebase again, never force-push over other scan results.
        for path in (".github/workflows/scan.yml",
                     ".github/workflows/local-leads.yml",
                     ".github/workflows/staged-probe.yml"):
            with self.subTest(workflow=path):
                workflow = (ROOT / path).read_text()
                self.assertIn("for attempt in 1 2 3 4 5; do", workflow)
                self.assertIn("git pull --rebase origin main", workflow)
                self.assertIn("if git push origin HEAD:main; then", workflow)
                self.assertIn('if [ "$attempt" -eq 5 ]; then', workflow)
                self.assertIn('exit 1', workflow)
                self.assertNotIn("git push --force", workflow)
                self.assertNotIn("git push -f ", workflow)
                self.assertLess(workflow.index("git pull --rebase origin main"),
                                workflow.index("if git push origin HEAD:main; then"))


if __name__ == "__main__":
    unittest.main()
