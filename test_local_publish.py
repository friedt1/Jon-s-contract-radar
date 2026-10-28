"""Real Git integration tests; all remotes and races stay in temporary directories."""
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).parent / 'scripts/publish-local.sh'


class PublishTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.remote = self.root / 'remote.git'
        self.work = self.root / 'work'
        self.other = self.root / 'other'
        self.git(self.root, 'init', '--bare', str(self.remote))
        self.git(self.root, 'clone', str(self.remote), str(self.work))
        self.configure(self.work)
        self.git(self.work, 'checkout', '-b', 'main')
        (self.work / 'data').mkdir()
        for name in ('local_leads', 'local_history', 'opportunities'):
            (self.work / f'data/{name}.json').write_text('base\n')
        self.git(self.work, 'add', '.')
        self.git(self.work, 'commit', '-m', 'base')
        self.git(self.work, 'push', 'origin', 'main')
        self.git(self.root, 'clone', '--branch', 'main', str(self.remote), str(self.other))
        self.configure(self.other)
        for name in ('local_leads', 'local_history'):
            (self.work / f'data/{name}.json').write_text('new local scan\n')

    def git(self, cwd, *args):
        return subprocess.run(['git', *args], cwd=cwd, text=True, capture_output=True, check=True).stdout

    def configure(self, path):
        self.git(path, 'config', 'user.name', 'Offline Test')
        self.git(path, 'config', 'user.email', 'test@example.invalid')

    def publish(self):
        return subprocess.run(['bash', str(SCRIPT)], cwd=self.work, text=True, capture_output=True)

    def race(self, target):
        # Update remote after publisher's commit and immediately before first push.
        hook = self.work / '.git/hooks/pre-push'
        hook.write_text(f'''#!/usr/bin/env bash
set -eu
rm -- "$0"
printf 'concurrent update\\n' > '{self.other}/data/{target}.json'
git -C '{self.other}' add .
git -C '{self.other}' commit -m concurrent >/dev/null
git -C '{self.other}' push origin main >/dev/null
''')
        hook.chmod(0o755)

    def test_normal_and_repeat_publication(self):
        self.assertEqual(self.publish().returncode, 0)
        before = self.git(self.work, 'rev-parse', 'HEAD')
        self.assertEqual(self.publish().returncode, 0)
        self.assertEqual(before, self.git(self.work, 'rev-parse', 'HEAD'))
        self.assertEqual(self.git(self.work, 'show', 'origin/main:data/local_leads.json'), 'new local scan\n')

    def test_contract_race_preserves_both_updates(self):
        self.race('opportunities')
        result = self.publish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git(self.work, 'show', 'origin/main:data/opportunities.json'), 'concurrent update\n')
        self.assertEqual(self.git(self.work, 'show', 'origin/main:data/local_history.json'), 'new local scan\n')

    def test_conflicting_local_race_fails_without_overwrite(self):
        self.race('local_leads')
        result = self.publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Concurrent conflicting update', result.stderr)
        self.assertEqual(self.git(self.other, 'show', 'origin/main:data/local_leads.json'), 'concurrent update\n')
        self.assertFalse((self.work / '.git/rebase-merge').exists())

    def test_unrelated_staged_changes_refused(self):
        (self.work / 'unexpected.txt').write_text('unrelated')
        self.git(self.work, 'add', 'unexpected.txt')
        result = self.publish()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('unrelated staged changes', result.stderr)
        self.assertEqual(self.git(self.work, 'show', 'origin/main:data/local_leads.json'), 'base\n')
