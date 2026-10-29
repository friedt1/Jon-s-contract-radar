"""Conservative daily probes of staged official procurement entry points.

Never activates a source, changes sources.json, or creates opportunity records.
robots.txt is a necessary gate, not proof of site terms or API authorization.
Only one individual CivicPlus notice per source is fetched to test adapter shape.
"""
import datetime as dt
import json
import pathlib
import re
from urllib.parse import urlparse

import civicplus_bids
import granicus_rfps
import robots_policy
import scan

ROOT = pathlib.Path(__file__).resolve().parent
SOURCES = ROOT / "sources.json"
OUT = ROOT / "data" / "staged_probes.json"


def _error(exc):
    return type(exc).__name__


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
            result["state"] = "listing_reachable_adapter_required"
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
        # A single existing notice, including an old/closed notice, is enough
        # to test parser shape. It is NEVER a verified open opportunity.
        detail_url = records[0]["url"]
        try:
            blob, ctype, detail_final = fetch(detail_url, binary=True)
        except robots_policy.RobotsDenied:
            result["state"] = "individual_notice_robots_blocked"
            return result
        except Exception as exc:
            result["state"] = "individual_notice_fetch_error"
            result["error_type"] = _error(exc)
            return result
        if (adapter.individual_url(detail_final, final) != detail_url
                or ("html" not in ctype and not blob.lstrip().startswith(b"<"))):
            result["state"] = "individual_notice_redirect_or_type_mismatch"
            return result
        body = " ".join(scan.parse_html(blob.decode("utf-8", "replace")).parts)
        if adapter is civicplus_bids:
            valid_shape = (re.search(r"\bBid\s+(?:Number|Title)\s*:", body, re.I)
                           and re.search(r"\b(?:Description|Closing\s+Date/Time|Status)\s*:", body, re.I))
        else:
            valid_shape = granicus_rfps.detail_shape(body)
        if not valid_shape:
            result["state"] = "individual_notice_fields_missing"
            return result
        result["individual_notice_retrieved"] = True
        result["sample_notice_url"] = detail_url
        detail_status = adapter.status_of(body)
        status = detail_status if detail_status != "unknown" else records[0]["open_status"]
        result["sample_notice_status"] = status
        result["sample_notice_status_source"] = (
            "individual_notice" if detail_status != "unknown" else "listing_unverified"
        )
        detail_due, detail_time = adapter.detail_closing_of(body)
        listed_due = records[0]["deadline"]
        listed_time = records[0]["deadline_time"]
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
    except robots_policy.RobotsDenied:
        result["state"] = "listing_robots_blocked"
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
