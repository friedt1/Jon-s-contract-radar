#!/usr/bin/env bash
# Run only in the clean, disposable Actions checkout, after scanner + validator.
set -euo pipefail
files=(data/local_leads.json data/local_history.json)
git add -- "${files[@]}"
if git diff --cached --quiet; then exit 0; fi
# Use only Bash and Git: ripgrep is not guaranteed on Actions runners.
# NUL-delimited paths prevent whitespace and quoted-path bypasses.
while IFS= read -r -d '' path; do
  case "$path" in
    data/local_leads.json|data/local_history.json) ;;
    *)
      echo "Refusing to publish unrelated staged changes: $path" >&2
      exit 1
      ;;
  esac
done < <(git diff --cached --name-only -z)
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
