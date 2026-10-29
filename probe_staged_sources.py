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
        if source["name"] not in civicplus_bids.SOURCES:
            result["state"] = "listing_reachable_adapter_required"
            return result
        records = civicplus_bids.listing_records(scan.parse_html(html), final)
        result["individual_records_discovered"] = len(records)
        if not records:
            listing_text = " ".join(scan.parse_html(html).parts)
            if re.search(r"\b(?:there are )?no (?:currently )?open bids?(?: postings)?(?: at this time)?\b", listing_text, re.I):
                result["state"] = "listing_reachable_no_open_bids"
            else:
                result["state"] = "listing_reachable_no_bidid_records"
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
        if (civicplus_bids.individual_url(detail_final, final) != detail_url
                or "html" not in ctype and not blob.lstrip().startswith(b"<")):
            result["state"] = "individual_notice_redirect_or_type_mismatch"
            return result
        body = " ".join(scan.parse_html(blob.decode("utf-8", "replace")).parts)
        if (not re.search(r"\bBid\s+(?:Number|Title)\s*:", body, re.I)
                or not re.search(r"\b(?:Description|Closing\s+Date/Time|Status)\s*:", body, re.I)):
            result["state"] = "individual_notice_fields_missing"
            return result
        result["individual_notice_retrieved"] = True
        result["sample_notice_url"] = detail_url
        status = civicplus_bids.status_of(body)
        result["sample_notice_status"] = status
        detail_due, detail_time = civicplus_bids.detail_closing_of(body)
        due = detail_due or records[0]["deadline"]
        due_time = detail_time if detail_due else records[0]["deadline_time"]
        result["sample_notice_deadline"] = due
        result["sample_notice_deadline_time"] = due_time
        result["sample_notice_temporal_evidence"] = (
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
