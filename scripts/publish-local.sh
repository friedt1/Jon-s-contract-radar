#!/usr/bin/env bash
# Run only in the clean, disposable Actions checkout, after scanner + validator.
set -euo pipefail
files=(data/local_leads.json data/local_history.json)
git add -- "${files[@]}"
if git diff --cached --quiet; then exit 0; fi
if git diff --cached --name-only | rg -v '^data/local_(leads|history)\.json$'; then
  echo 'Refusing to publish unrelated staged changes' >&2
  exit 1
fi
git commit -m 'Update local customer discoveries and history'
for attempt in 1 2 3; do
  if git push origin HEAD:main; then exit 0; fi
  # Rebase preserves concurrent contract/source/code updates. A conflict (including
  # a newer local feed) fails closed rather than choosing either snapshot blindly.
  if ! git pull --rebase origin main; then
    git rebase --abort
    echo 'Concurrent conflicting update; preserving remote results. Rerun scan.' >&2
    exit 1
  fi
done
echo 'Push failed after three attempts; no force push attempted.' >&2
exit 1
