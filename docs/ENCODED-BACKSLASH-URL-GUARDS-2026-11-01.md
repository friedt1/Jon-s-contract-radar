# Encoded-backslash URL safety for procurement extraction (2026-11-01)

The configured-source validator and three individual-notice discovery paths
previously rejected literal backslashes and percent-encoded control characters
but did not reject `%5C` (percent-encoded backslash). Some intermediaries
can interpret this character as a path separator. A malformed URL should not
count as a verified direct source, a staged official entrypoint, or an
individual notice worth a bounded request.

This change consistently rejects `%5c` / `%5C` in:
- `source_config.valid_public_https_url` (source inventory and audit);
- `scan.safe_detail_url` (general same-host notice requests);
- `civicplus_bids.individual_url` (county bidID notices);
- `granicus_rfps.individual_url` (Binghamton staged notice diagnostics);
- `probe_staged_sources._safe_link` (diagnostic outbound links).

`test_encoded_backslash_url_guards.py` checks malformed and ordinary URLs,
coverage accounting, and the guarantee that an invalid configured source
never calls the direct scanner. All test URLs are synthetic, not bids.

**Operational boundary:** No source is activated or removed. The inventory
remains 102 named targets, 18 configured direct pages and 84 staged official
entrypoints; staging is not operational individual-contract monitoring.
This patch does not authorize automated access, change request budgets,
claim an open bid, or change the historical Erie tree/stump and Owego
demolition exclusions. Source-specific robots and publisher terms review
remains necessary before any staged source is activated.
