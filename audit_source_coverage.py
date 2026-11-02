"""Audit configured source monitoring: indirect news is not direct bid monitoring.

Run: python audit_source_coverage.py
Use --strict to enforce the 102-target inventory and configured direct-access gates.
Passing this structural audit does not prove live, permitted bid extraction.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from notice_identity import canonical_url

EXPECTED_NAMED_TARGETS = 102

from source_config import (DIRECT_MODES, UNCONNECTED_PLATFORMS,
                           direct_configured, direct_fetch_target,
                           valid_public_https_url)


def audit(sources):
    results = []
    for source in sources:
        raw_name = source.get("name", "")
        # Agency labels are inventory identities, not display-only strings.
        # Whitespace/case variants must not silently count as distinct targets.
        name = " ".join(raw_name.split()) if isinstance(raw_name, str) else ""
        mode = source.get("mode", "missing")
        url = source.get("url", "")
        direct = direct_configured(source)
        access_required = direct and (name in UNCONNECTED_PLATFORMS
                                      or source.get("provider_access_required") is True
                                      or bool(source.get("delegated_provider")))
        adapter_missing = direct and not direct_fetch_target(source)
        staged = (not direct and mode == "discovery_pending"
                  and valid_public_https_url(source.get("candidate_official_url")))
        invalid_direct = mode in DIRECT_MODES and not direct
        # An official agency homepage is not an identified procurement index.
        # Keep it in staged coverage, but expose the separate discovery gate.
        publisher_only = staged and source.get("official_page_role") == "publisher_entrypoint_only"
        staged_access_required = staged and (
            source.get("provider_access_required") is True
            or bool(source.get("delegated_provider")))
        results.append({
            "source": name,
            "mode": mode,
            "direct_configured": direct,
            "direct_fetch_target": direct_fetch_target(source) and not access_required,
            "adapter_not_implemented": adapter_missing,
            "provider_access_required": access_required,
            "staged_provider_access_required": staged_access_required,
            "official_url_staged": staged,
            "staged_publisher_entrypoint_only": publisher_only,
            "invalid_direct_configuration": invalid_direct,
            "candidate_official_url": source.get("candidate_official_url") if staged else None,
            "activation_gate": source.get("activation_gate", "") if staged else "",
            "official_page_role": source.get("official_page_role", "") if staged else "",
            "target_url": url if direct else None,
            "status": ("configured URL only; provider-approved individual-listing ingestion not connected"
                       if access_required else
                       "configured URL only; direct adapter not implemented" if adapter_missing else
                       "configured; live ingestion not independently verified" if direct else
                       "official supplier gateway staged; registration/authorization required, "
                       "individual-notice ingestion not connected" if staged_access_required else
                       "official publisher entrypoint only; current bid index not identified or monitored" if publisher_only else
                       "official URL staged; individual-notice extraction and permissions not verified" if staged else
                       "invalid direct configuration; verified HTTPS URL required" if invalid_direct else
                       "not directly monitored; official source discovery required"),
        })
    # A duplicated name can masquerade as a second one of the 102 targets.
    # Preserve raw row counts for investigation, but report distinct agencies
    # separately and never interpret duplicate rows as a shared publisher.
    unnamed_source_rows = sum(not row["source"] for row in results)
    name_counts = Counter(row["source"].casefold() for row in results if row["source"])
    display_names = {}
    for row in results:
        if row["source"]:
            display_names.setdefault(row["source"].casefold(), row["source"])
    duplicate_keys = {key for key, count in name_counts.items() if count > 1}
    duplicate_names = sorted(display_names[key] for key in duplicate_keys)
    for row in results:
        row["duplicate_source_name"] = row["source"].casefold() in duplicate_keys

    # A single official procurement gateway may represent multiple named
    # agencies. Report those overlaps without treating a shared landing page
    # as independent individual-bid ingestion for every named target.
    by_entrypoint = {}
    for row in results:
        candidate = (row["target_url"] if row["direct_configured"] else
                     row["candidate_official_url"] if row["official_url_staged"] else None)
        if candidate:
            normalized = canonical_url(candidate)
            if normalized:
                by_entrypoint.setdefault(normalized, []).append(row["source"])
    shared = {url: sorted(set(names)) for url, names in sorted(by_entrypoint.items())
              if len(set(names)) > 1}
    for row in results:
        candidate = (row["target_url"] if row["direct_configured"] else
                     row["candidate_official_url"] if row["official_url_staged"] else None)
        row["shared_official_entrypoint"] = bool(
            candidate and canonical_url(candidate) in shared)

    return {
        "distinct_official_entrypoints": len(by_entrypoint),
        "shared_official_entrypoint_groups": shared,
        "shared_official_entrypoint_targets": sum(len(names) for names in shared.values()),
        "total": len(results),
        "unique_named_targets": len(name_counts),
        "duplicate_source_names": duplicate_names,
        "unnamed_source_rows": unnamed_source_rows,
        "duplicate_source_rows": sum(count - 1 for count in name_counts.values() if count > 1),
        "inventory_integrity_ok": not duplicate_names and not unnamed_source_rows,
        "direct_configured": sum(x["direct_configured"] for x in results),
        "direct_fetch_targets": sum(x["direct_fetch_target"] for x in results),
        "configured_provider_access_required": sum(x["provider_access_required"] for x in results),
        "staged_provider_access_required": sum(x["staged_provider_access_required"] for x in results),
        "configured_unimplemented_adapters": sum(x["adapter_not_implemented"] for x in results),
        "not_directly_monitored": sum(not x["direct_configured"] for x in results),
        "official_urls_staged": sum(x["official_url_staged"] for x in results),
        "staged_publisher_entrypoints_only": sum(
            x["staged_publisher_entrypoint_only"] for x in results),
        "invalid_direct_configurations": sum(x["invalid_direct_configuration"] for x in results),
        "discovery_required": sum(not x["direct_configured"] and not x["official_url_staged"]
                                  and not x["invalid_direct_configuration"] for x in results),
        "sources": results,
        "warning": ("Direct configuration is not operational monitoring. Feed/API modes without "
                    "an implemented adapter are not fetch targets. Provider landing URLs "
                    "without approved individual-listing ingestion are access-required, not fetch targets. "
                    "Even other fetch targets do not prove permitted or successful bid extraction. "
                    "Malformed, insecure, or unverified URLs do not count as direct "
                    "configuration; staged URLs are not active monitoring. Staged "
                    "publisher-only homepages still need a real bid index; "
                    "supplier-registration gateways require authorization and are not "
                    "public individual-bid feeds. Shared official entrypoints do not "
                    "represent independent operational bid feeds. Duplicate named "
                    "source rows and unnamed targets are inventory defects, not additional monitored targets.")
    }


def strict_failures(report, expected_targets=EXPECTED_NAMED_TARGETS):
    """Structural blockers for a complete named-source configuration.

    This deliberately does not certify robots/terms permission, current bid
    retrieval, or individual-notice verification; those require live evidence.
    """
    failures = []
    if report["total"] != expected_targets:
        failures.append(f"inventory rows: {report['total']} (expected {expected_targets})")
    if report["unique_named_targets"] != expected_targets:
        failures.append(
            f"unique named targets: {report['unique_named_targets']} "
            f"(expected {expected_targets})")
    if not report["inventory_integrity_ok"]:
        failures.append(
            f"inventory names invalid: {report['duplicate_source_rows']} duplicate rows, "
            f"{report['unnamed_source_rows']} unnamed rows")
    for key, label in (
        ("not_directly_monitored", "not directly configured"),
        ("configured_provider_access_required", "provider access required"),
        ("configured_unimplemented_adapters", "adapter not implemented"),
        ("invalid_direct_configurations", "invalid direct configurations"),
    ):
        if report[key]:
            failures.append(f"{label}: {report[key]}")
    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--sources", default="sources.json")
    parser.add_argument("--expected-targets", type=int, default=EXPECTED_NAMED_TARGETS,
                        help="Required distinct named sources (default: 102)")
    args = parser.parse_args()
    if args.expected_targets < 1:
        parser.error("--expected-targets must be a positive integer")
    results = audit(json.loads(Path(args.sources).read_text(encoding="utf-8")))
    results["strict_blockers"] = strict_failures(results, args.expected_targets)
    print(json.dumps(results, indent=2))
    return 1 if args.strict and results["strict_blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
