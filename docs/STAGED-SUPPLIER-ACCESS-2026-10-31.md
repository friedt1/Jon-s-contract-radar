# Staged supplier-access diagnostics (2026-10-31)

## Problem
A verified official supplier entrypoint can be staged while the actual bid feed requires provider registration or invitations. The existing source-health report only marked `provider_access_required` when a source was already directly configured, so a staged gateway (for example, NYPA/SAP Ariba or FirstEnergy/Coupa) appeared as an ordinary staged URL with no explicit access warning. That hid a material reason the 84 pending targets are not live.

## Change
- Report `staged_provider_access_required` only for a `discovery_pending` source with a syntactically valid staged official HTTPS URL and explicit `provider_access_required` or `delegated_provider` evidence.
- Keep `configured_access_required`, `configured_direct`, `configured_fetch_targets`, and direct state unchanged. No source is promoted to direct monitoring.
- Display a separate count, warning badge, and filter on the dashboard.
- Include staged access gates in CLI diagnostics without treating them as a fetch error or verified open opportunity.

## Verification and limits
Synthetic Python and Node regression tests cover staged-vs-configured separation, no URL promotion, dashboard filter and badge, and zero fabricated leads. GitHub Actions results must be checked before merge. These tests do not establish publisher permission, individual-notice ingestion, or live contract availability.

## Outstanding work
For all 102 named sources, identify permitted individual-notice endpoints and review robots/terms and publisher registration. Staged gateways remain `discovery_pending`; FirstEnergy's invitation-only procurement cannot be activated from a public supplier landing page. Erie tree/stump removal and Owego demolition remain regression-only cases, never live seed records.
