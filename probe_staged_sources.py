"""Conservative daily probes of staged official procurement entry points.

Never activates a source, changes sources.json, or creates opportunity records.
robots.txt is a necessary gate, not proof of site terms or API authorization.
At most three individual notices per source are fetched to test adapter shape.
"""
import datetime as dt
import json
import pathlib
import re
from urllib.parse import urlparse
from urllib.error import HTTPError

import civicplus_bids
import granicus_rfps
import robots_policy
import scan

ROOT = pathlib.Path(__file__).resolve().parent
SOURCES = ROOT / "sources.json"
OUT = ROOT / "data" / "staged_probes.json"
MAX_SAMPLE_DETAILS = 3  # A broken historical notice must not condemn a whole source.


def _error(exc):
    return type(exc).__name__


def _http_failure(code, scope):
    # A 403 may be a firewall/permission denial, not proof that login is
    # possible. Preserve the distinction instead of reporting a generic error.
    if code == 401:
        return f"{scope}_authentication_required"
    if code == 403:
        return f"{scope}_access_forbidden"
    if code in (404, 410):
        return f"{scope}_not_found"
    if code == 429:
        return f"{scope}_rate_limited"
    if 500 <= code < 600:
        return f"{scope}_server_error"
    return f"{scope}_http_error"


def _sample_priority(record, now):
    # Prefer a listing with a future closing date over a stale "Open" label.
    # A sampled notice is NEVER an actionable or verified contract.
    if record.get("open_status") in civicplus_bids.CLOSED:
        return 3
    due = record.get("deadline", "")
    if due:
        return 2 if civicplus_bids.closing_passed(
            due, record.get("deadline_time", ""), now) else 0
    return 1


def probe(source, fetch=scan.fetch, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    url = source["candidate_official_url"]
    result = {
        "name": source["name"],
        "official_entrypoint": url,
        "state": "not_checked",
        "listing_retrieved": False,
        "individual_notice_retrieved": False,
        "individual_records_discovered": 0,
        "individual_samples_attempted": 0,
        "individual_sample_failures": [],
        "activation_gate": source.get("activation_gate", ""),
        "terms_review": "required; robots allowance alone is not authorization",
        "direct_monitoring_activated": False,
    }
    try:
        html, kind, final = fetch(url)
        if urlparse(final).hostname != urlparse(url).hostname:
            result["state"] = "listing_redirected_off_official_host"
            return result
        if "html" not in kind and not html.lstrip().startswith("<"):
            result["state"] = "unsupported_listing_content_type"
            return result
        result["listing_retrieved"] = True
        if source["name"] in civicplus_bids.SOURCES:
            adapter = civicplus_bids
        elif source["name"] in granicus_rfps.SOURCES:
            adapter = granicus_rfps
        else:
            # An official homepage is not necessarily a procurement listing.
            # Report whether there is even visible bid/RFP/RFQ evidence before
            # claiming that a notice adapter is the only missing piece.
            page = scan.parse_html(html)
            listing_text = " ".join(page.parts)
            has_procurement_evidence = bool(re.search(
                r"\b(?:bids?|rfps?|rfqs?|procurement|solicitations?|"
                r"request\s+for\s+(?:proposals?|qualifications?))\b",
                listing_text, re.I))
            # A public agency may only link to a registration-gated bid
            # platform. Reading its announcement page is not direct access
            # to individual solicitations on that platform.
            delegated_to_provider = bool(re.search(
                r"\b(?:BidNet|Empire State Purchasing Group|OpenGov|Bonfire|PennBid|Public Purchase)\b", listing_text, re.I)
                and re.search(r"\b(?:bid|rfp|rfq|solicitation|packet)s?\b",
                              listing_text, re.I))
            # Many agencies label the outbound link "View Bids" without
            # spelling out OpenGov/BidNet in visible page text. Inspect only
            # links explicitly labeled as procurement, never follow them.
            provider_link = any(
                re.search(r"(?:^|\\.)(?:opengov\\.com|bonfirehub\\.com|bidnetdirect\\.com|pennbid\\.net|publicpurchase\\.com)$",
                          (urlparse(href).hostname or "").lower())
                and re.search(r"\\b(?:bids?|rfps?|rfqs?|solicitations?|procurement|proposals?)\\b",
                              label, re.I)
                for label, href, _ in page.links
            )
            result["state"] = (
                "listing_reachable_external_provider_access_required"
                if delegated_to_provider or provider_link else
                "listing_reachable_adapter_required" if has_procurement_evidence else
                "official_page_reachable_no_procurement_evidence"
            )
            return result
        records = adapter.listing_records(scan.parse_html(html), final)
        result["individual_records_discovered"] = len(records)
        if not records:
            listing_text = " ".join(scan.parse_html(html).parts)
            if re.search(r"\b(?:there are )?no (?:currently )?open bids?(?: postings)?(?: at this time)?\b", listing_text, re.I):
                result["state"] = "listing_reachable_no_open_bids"
            else:
                result["state"] = ("listing_reachable_no_bidid_records"
                                   if adapter is civicplus_bids else
                                   "listing_reachable_no_individual_records")
            return result
        # Stale or broken notices are common. Prefer listings with a future
        # deadline, then unknown deadlines, then expired/closed listings.
        # Probe at most three distinct public URLs, stopping at the first
        # well-shaped record. A sample is diagnostic evidence only:
        # no candidate is emitted and no source is activated.
        for record in sorted(records, key=lambda record: _sample_priority(record, now))[:MAX_SAMPLE_DETAILS]:
            detail_url = record["url"]
            result["individual_samples_attempted"] += 1
            failure = {"url": detail_url}
            try:
                blob, ctype, detail_final = fetch(detail_url, binary=True)
            except robots_policy.RobotsDenied:
                failure["state"] = "individual_notice_robots_blocked"
                result["individual_sample_failures"].append(failure)
                continue
            except HTTPError as exc:
                failure["state"] = _http_failure(exc.code, "individual_notice")
                failure["http_status"] = exc.code
                result["individual_sample_failures"].append(failure)
                continue
            except Exception as exc:
                failure["state"] = "individual_notice_fetch_error"
                failure["error_type"] = _error(exc)
                result["individual_sample_failures"].append(failure)
                continue
            if (adapter.individual_url(detail_final, final) != detail_url
                    or ("html" not in ctype and not blob.lstrip().startswith(b"<"))):
                failure["state"] = "individual_notice_redirect_or_type_mismatch"
                result["individual_sample_failures"].append(failure)
                continue
            body = " ".join(scan.parse_html(blob.decode("utf-8", "replace")).parts)
            if adapter is civicplus_bids:
                valid_shape = (re.search(r"\bBid\s+(?:Number|Title)\s*:", body, re.I)
                               and re.search(r"\b(?:Description|Closing\s+Date/Time|Status)\s*:", body, re.I))
            else:
                valid_shape = granicus_rfps.detail_shape(body)
            if not valid_shape:
                failure["state"] = "individual_notice_fields_missing"
                result["individual_sample_failures"].append(failure)
                continue

            result["individual_notice_retrieved"] = True
            result["sample_notice_url"] = detail_url
            detail_status = adapter.status_of(body)
            status = detail_status if detail_status != "unknown" else record["open_status"]
            result["sample_notice_status"] = status
            result["sample_notice_status_source"] = (
                "individual_notice" if detail_status != "unknown" else "listing_unverified"
            )
            detail_due, detail_time = adapter.detail_closing_of(body)
            listed_due = record["deadline"]
            listed_time = record["deadline_time"]
            conflict = bool(detail_due and listed_due and
                            (detail_due != listed_due or
                             bool(detail_time and listed_time and
                                  detail_time.replace(" ", "").upper() !=
                                  listed_time.replace(" ", "").upper())))
            due = detail_due or listed_due
            due_time = detail_time if detail_due else listed_time
            result["sample_notice_deadline"] = due
            result["sample_notice_deadline_time"] = due_time
            result["sample_notice_deadline_conflict"] = conflict
            result["sample_notice_temporal_evidence"] = (
                "conflicting_deadlines_unverified" if conflict else
                "closed_or_awarded" if status in civicplus_bids.CLOSED else
                "deadline_passed" if due and civicplus_bids.closing_passed(due, due_time, now) else
                "deadline_not_passed_unverified" if due else "deadline_unknown"
            )
            result["state"] = "notice_format_confirmed_terms_review_required"
            return result

        failures = result["individual_sample_failures"]
        distinct_states = {failure["state"] for failure in failures}
        result["state"] = (next(iter(distinct_states)) if len(distinct_states) == 1
                           else "individual_notice_samples_failed")
        if len(failures) == 1 and "error_type" in failures[0]:
            result["error_type"] = failures[0]["error_type"]
        return result
    except robots_policy.RobotsDenied:
        result["state"] = "listing_robots_blocked"
    except HTTPError as exc:
        result["state"] = _http_failure(exc.code, "listing")
        result["http_status"] = exc.code
    except Exception as exc:
        result["state"] = "listing_fetch_error"
        result["error_type"] = _error(exc)
    return result


def build(sources, fetch=scan.fetch, now=None):
    staged = [s for s in sources if s.get("mode") == "discovery_pending"
              and s.get("candidate_official_url")]
    rows = [probe(source, fetch=fetch, now=now) for source in staged]
    return {
        "updated": (now or dt.datetime.now(dt.timezone.utc)).isoformat(),
        "configured_targets": len(sources),
        "staged_entrypoints": len(staged),
        "probes": rows,
        "warning": ("Diagnostic only: no source is activated by these probes. "
                    "A fetched page or parsed historical notice is not an open bid. "
                    "Sample 'Open' labels can be stale; inspect temporal evidence. "
                    "Review publisher terms, individual extraction, and live scan "
                    "before changing discovery_pending."),
    }


def main():
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))
    if len(sources) != 102 or len({s["name"] for s in sources}) != 102:
        raise ValueError("Expected 102 unique targets")
    data = build(sources)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print("Staged official entrypoints:", data["staged_entrypoints"])
    for row in data["probes"]:
        print(row["name"], row["state"])


if __name__ == "__main__":
    main()
