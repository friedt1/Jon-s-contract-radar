"""Conservative daily probes of staged official procurement entry points.

Never activates a source, changes sources.json, or creates opportunity records.
robots.txt is a necessary gate, not proof of site terms or API authorization.
At most three individual notices per source are fetched to test adapter shape.
"""
import datetime as dt
import json
import pathlib
import re
from urllib.parse import urljoin, urlparse
from urllib.error import HTTPError

import civicplus_bids
import granicus_rfps
import robots_policy
import scan
from source_config import valid_public_https_url

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


def _authentication_landing(html, final):
    """Identify an actual sign-in destination, not an ordinary login link."""
    login_path = bool(re.search(
        r"/(?:log-?in|sign-?in)(?:/|$)", urlparse(final).path, re.I))
    login_form = bool(
        re.search(r"""<input\b[^>]*\btype\s*=\s*['"]?password\b""", html, re.I)
        and re.search(
            r"<(?:title|h[12])\b[^>]*>\s*(?:log\s*in|sign\s*in|login)\b",
            html, re.I))
    return login_path or login_form


def _blocked_redirect_state(exc, scope):
    # The fetcher blocks redirects *before* requesting their destinations.
    # Never imply that an external provider was actually accessed.
    return (f"{scope}_insecure_redirect" if "HTTPS downgrade" in str(exc)
            else f"{scope}_redirect_blocked")


def _safe_link(base, href):
    """Resolve public page links for diagnostics only; never fetch the target.

    Protocol-relative links are common on municipal pages. Reject malformed,
    credentialed, insecure and non-HTTPS destinations before classifying a
    provider redirect or externally hosted bid PDF.
    """
    if not isinstance(href, str) or not href or any(
        ord(ch) < 33 or ord(ch) == 127 or ord(ch) == 92 for ch in href
    ):
        return None
    try:
        resolved = urljoin(base, href)
        parsed = urlparse(resolved)
        # Outbound links are diagnostic evidence, not trusted publisher URLs.
        # Reject encoded controls and private/resolver-alias hosts as well as
        # credentials and unsafe ports. Preserve harmless #page fragments in
        # diagnostics, but validate the actual destination without a fragment.
        if re.search(r"%(?:0[0-9a-f]|1[0-9a-f]|7f)", resolved, re.I):
            return None
        if not valid_public_https_url(parsed._replace(fragment="").geturl()):
            return None
        return parsed
    except ValueError:
        return None


def _sample_priority(record, now):
    """Sample current-looking service bids before unrelated notices.

    Deadline and status evidence always outrank service relevance. This is
    *only* the order for bounded staged adapter probes: it cannot activate a
    source, publish a lead, or establish an open contract. In particular an
    expired tree bid must not leap ahead of a future unrelated bid.
    """
    if record.get("open_status") in civicplus_bids.CLOSED:
        temporal = 3
    elif record.get("listing_status_conflict") or record.get("listing_deadline_conflict"):
        temporal = 2
    else:
        due = record.get("deadline", "")
        temporal = (2 if civicplus_bids.closing_passed(
            due, record.get("deadline_time", ""), now) else 0) if due else 1

    # Only use isolated listing-card text. Page-wide chrome can mention tree
    # work that belongs to a different bid. scan.category() also excludes
    # explicit "tree work by others" and unrelated demolition-only scopes.
    scope = " ".join(str(record.get(key) or "") for key in ("title", "description"))
    service = scan.category(scope)
    service_order = {
        "Tree removal": 0, "Storm cleanup": 1, "Tree trimming": 2,
        "Vegetation management": 3, "Land clearing": 4,
        "Related site prep": 5,
    }
    return temporal, service_order.get(service, 6)


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
    # Staged entries are untrusted configuration. Apply the same public-HTTPS
    # URL hygiene as active source configuration before ANY network request.
    # An invalid entry must not become a generic network error or a live source.
    if not valid_public_https_url(url):
        result["state"] = "listing_invalid_official_url"
        return result
    try:
        html, kind, final = fetch(url)
        # The fetcher normally blocks unsafe redirects, but validate its final
        # URL independently too (including credentialed, malformed, nonstandard
        # port and encoded-control destinations). This protects injected fetchers
        # and future adapter changes from treating an unsafe landing as a bid page.
        if not valid_public_https_url(final):
            result["state"] = (
                "listing_insecure_redirect"
                if isinstance(final, str) and final.lower().startswith("http://")
                else "listing_unsafe_redirect"
            )
            return result
        if urlparse(final).hostname != urlparse(url).hostname:
            # A county may redirect its bids page directly to an external
            # procurement provider. That is not an activated individual-notice
            # adapter, and must not be mistaken for an arbitrary off-site
            # redirect. Host matching is exact/subdomain-only (no lookalikes).
            if scan.provider_link(final):
                result["state"] = "listing_redirected_to_external_provider_access_required"
                result["external_provider_host"] = urlparse(final).hostname
            else:
                result["state"] = "listing_redirected_off_official_host"
            return result
        if "html" not in kind and not html.lstrip().startswith("<"):
            result["state"] = "unsupported_listing_content_type"
            return result
        # Some official bid URLs redirect to a same-host login page (or
        # serve a login form at the original URL). Do not mistake a 200 OK
        # authentication wall for a reachable public bid listing. A mere
        # login link on an otherwise public page is not sufficient.
        if _authentication_landing(html, final):
            result["state"] = "listing_authentication_required"
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
            # Resolve protocol-relative links against the actual official
            # listing URL. These are *diagnostics*, not requests to the
            # destination. A provider lookalike must never match.
            linked = [(label, parsed)
                      for label, href, _ in page.links
                      for parsed in [_safe_link(final, href)]
                      if parsed is not None]
            provider_link = any(
                scan.provider_link(parsed.geturl())
                and re.search(r"\b(?:bids?|rfps?|rfqs?|solicitations?|procurement|proposals?)\b",
                              label, re.I)
                for label, parsed in linked
            )
            # A municipality may publish bid packets on a separate HTTPS
            # document CDN. The official listing alone does not authorize
            # off-host retrieval, establish a deadline, or prove the documents
            # are still open. Report the hosts without fetching them.
            off_host_pdf_hosts = sorted({
                parsed.hostname.lower()
                for _label, parsed in linked
                if parsed.hostname.lower() != urlparse(final).hostname.lower()
                and parsed.path.lower().endswith(".pdf")
            })
            if has_procurement_evidence and off_host_pdf_hosts:
                result["off_host_pdf_hosts_unverified"] = off_host_pdf_hosts
            # An issuer's explicit empty-bids message is useful diagnostic
            # evidence, but only for the visible listing at probe time. Do not
            # infer that other procurement channels are empty. If the page
            # also links to potential individual notices, prefer adapter review
            # rather than treating a stale empty-state banner as authoritative.
            no_open_bids_reported = bool(re.search(
                r"\bno\s+(?:current(?:ly)?\s+)?open\s+bids?\b",
                listing_text, re.I))
            possible_notice_links = any(
                parsed.path.lower().endswith(".pdf")
                or (re.search(
                    r"\b(?:bids?|rfps?|rfqs?|proposals?|solicitations?|"
                    r"quotes?|trees?|stumps?)\b", label, re.I)
                    and parsed.path not in ("", "/", urlparse(final).path))
                for label, parsed in linked
            )
            empty_bids_listing = (
                has_procurement_evidence and no_open_bids_reported
                and not possible_notice_links
                and not (delegated_to_provider or provider_link)
            )
            if empty_bids_listing:
                result["section_note"] = (
                    "Issuer's visible bid listing reports no current open bids "
                    "at probe time; other channels and individual notice "
                    "access remain unverified")
            # Some municipal homepages have an explicit RFP section that
            # currently says "None at this time". This is evidence about that
            # section only, not proof that no bids exist on other pages or
            # portals. Do not confuse it with a missing extraction adapter.
            rfp_section_empty = bool(re.search(
                r"\b(?:Request\s+for\s+Proposals?|RFPs?)\s*:\s*"
                r"None\s+at\s+this\s+time\b", listing_text, re.I))
            if rfp_section_empty:
                result["section_note"] = (
                    "RFP section reports none at probe time; other bid "
                    "channels and individual notice access remain unverified")
            result["state"] = (
                "listing_reachable_external_provider_access_required"
                if delegated_to_provider or provider_link else
                "listing_reachable_rfp_section_reports_none" if rfp_section_empty else
                "listing_reachable_no_open_bids_reported" if empty_bids_listing else
                "listing_reachable_off_host_documents_review_required"
                if has_procurement_evidence and off_host_pdf_hosts else
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
            except scan.UnsafeRedirect as exc:
                failure["state"] = _blocked_redirect_state(exc, "individual_notice")
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
            if "html" not in ctype and not blob.lstrip().startswith(b"<"):
                failure["state"] = "individual_notice_redirect_or_type_mismatch"
                result["individual_sample_failures"].append(failure)
                continue
            detail_html = blob.decode("utf-8", "replace")
            if (urlparse(detail_final).hostname == urlparse(final).hostname
                    and _authentication_landing(detail_html, detail_final)):
                failure["state"] = "individual_notice_authentication_required"
                result["individual_sample_failures"].append(failure)
                continue
            if adapter.individual_url(detail_final, final) != detail_url:
                failure["state"] = "individual_notice_redirect_or_type_mismatch"
                result["individual_sample_failures"].append(failure)
                continue
            body = " ".join(scan.parse_html(detail_html).parts)
            if adapter is civicplus_bids:
                valid_shape = (re.search(r"\bBid\s+(?:Number|Title)\s*:", body, re.I)
                               and re.search(r"\b(?:Description|Closing\s+Date/Time|Status)\s*:", body, re.I))
            else:
                valid_shape = granicus_rfps.detail_shape(body)
            if not valid_shape:
                failure["state"] = "individual_notice_fields_missing"
                result["individual_sample_failures"].append(failure)
                continue
            # A stable bidID URL can serve the wrong solicitation after a
            # publisher migration or caching error. Apply the same explicit
            # bid-number identity gate as the active CivicPlus scanner before
            # claiming that an individual sample was retrieved.
            if adapter is civicplus_bids and record.get("bid_number"):
                detail_number = re.search(
                    r"\\bBid\\s+(?:Number|No\\.?)\\s*:?\\s*([A-Za-z0-9-]+)\\b",
                    body, re.I,
                )
                if (detail_number and detail_number.group(1).casefold()
                        != record["bid_number"].casefold()):
                    failure["state"] = "individual_notice_bid_number_mismatch"
                    result["individual_sample_failures"].append(failure)
                    continue

            result["individual_notice_retrieved"] = True
            result["sample_notice_url"] = detail_url
            detail_status = adapter.status_of(body)
            listed_status = record["open_status"]
            status = detail_status if detail_status != "unknown" else listed_status
            # A publisher's listing and individual notice can disagree after
            # a bid closes or is amended. Neither an "Open" listing nor an
            # "Open" detail should silently override a contradictory status.
            status_conflict = (bool(record.get("listing_status_conflict"))
                               or (detail_status != "unknown"
                                   and listed_status != "unknown"
                                   and ((detail_status in civicplus_bids.CLOSED)
                                        != (listed_status in civicplus_bids.CLOSED))))
            result["sample_notice_status"] = status
            result["sample_notice_listing_status"] = listed_status
            result["sample_notice_status_conflict"] = status_conflict
            result["sample_notice_status_source"] = (
                "individual_notice" if detail_status != "unknown" else "listing_unverified"
            )
            detail_due, detail_time = adapter.detail_closing_of(body)
            listed_due = record["deadline"]
            listed_time = record["deadline_time"]
            conflict = (bool(record.get("listing_deadline_conflict"))
                        or bool(detail_due and listed_due and
                                (detail_due != listed_due or
                                 bool(detail_time and listed_time and
                                      detail_time.replace(" ", "").upper() !=
                                      listed_time.replace(" ", "").upper()))))
            # An explicit but unparseable detail closing field supersedes
            # the listing's possibly stale cutoff. Do not report the old
            # listing date as future submission evidence.
            unparseable_detail_closing = bool(
                adapter is civicplus_bids and not detail_due
                and re.search(
                    r"\\bClosing\\s+Date(?:/Time|\\s+and\\s+Time)?\\s*:",
                    body, re.I,
                )
            )
            due = detail_due or ("" if unparseable_detail_closing else listed_due)
            due_time = (detail_time if detail_due else
                        "" if unparseable_detail_closing else listed_time)
            result["sample_notice_unparseable_detail_closing"] = unparseable_detail_closing
            result["sample_notice_deadline_source"] = (
                "individual_notice" if detail_due else
                "listing" if due else "unknown"
            )
            result["sample_notice_deadline"] = due
            result["sample_notice_deadline_time"] = due_time
            result["sample_notice_deadline_conflict"] = conflict
            result["sample_notice_temporal_evidence"] = (
                "conflicting_status_unverified" if status_conflict else
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
    except scan.UnsafeRedirect as exc:
        result["state"] = _blocked_redirect_state(exc, "listing")
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
        "safe_staged_entrypoints": sum(
            valid_public_https_url(s.get("candidate_official_url")) for s in staged
        ),
        "invalid_staged_entrypoints": sum(
            not valid_public_https_url(s.get("candidate_official_url")) for s in staged
        ),
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
