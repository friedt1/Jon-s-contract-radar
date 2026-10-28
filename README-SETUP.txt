CURRENT SETUP

Use README.md for setup and local validation commands, and docs/VALIDATION.md
for the verification record and remaining live-access limitations.

The authoritative automation is .github/workflows/scan.yml. The obsolete root
scan.yml duplicate was removed to prevent installing a different workflow.
Keep all 102 sources.json target identities. Thirteen direct public integrations
also retain news discovery; 89 targets use indirect discovery. SAM.gov is deferred.

The existing website and its data/opportunities.json path are preserved. No Pages
settings were changed. Review the pull request and hosted checks before merging.
