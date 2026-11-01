"""Validate the dashboard feed without requiring network access."""
import json
import datetime as dt
from pathlib import Path
import scan
import notice_identity
from source_config import direct_configured, valid_public_https_url
import source_health
from publisher_status import publisher_closed
from submission_deadlines import eastern_deadline_timezone


def validate_active_notice(lead, now):
    """Fail closed on publisher closure or a known elapsed submission cutoff.

    This validates an existing feed; it never establishes that a bid is open.
    A date-only notice or a non-Eastern timezone cannot be given an invented
    same-day closing time. Synthetic tests exercise this safety boundary.
    """
    if publisher_closed(lead) or lead.get('review_priority') == 'expired_check':
        raise ValueError('Closed/expired notice in active feed: ' + str(lead.get('id', '')))
    due = lead.get('deadline')
    clock = lead.get('deadline_time')
    if (due and clock and eastern_deadline_timezone(lead.get('deadline_timezone'))
            and scan.civicplus_bids.closing_passed(due, str(clock), now)):
        raise ValueError('Elapsed submission cutoff in active feed: ' + str(lead.get('id', '')))


def _staged_after_published_scan(source, published_row, feed_updated, status):
    """Allow only documented post-scan staging metadata to lag in old feeds.

    This never permits an active direct source, altered bid record, or changed
    scan status to be silently treated as a newly scanned publisher.
    """
    if (source.get("mode") != "discovery_pending"
            or source.get("url") or source.get("verified_url") is not False
            or not valid_public_https_url(source.get("candidate_official_url"))
            or published_row.get("direct_state") != "not_configured"
            or published_row.get("staged_official_url")
            or published_row.get("direct_url")
            or "direct fetched" in status or "direct error" in status):
        return False
    checked = source.get("official_url_checked_at")
    if not isinstance(checked, str) or not isinstance(feed_updated, str):
        return False
    try:
        checked_at = dt.datetime.fromisoformat(checked.replace("Z", "+00:00"))
        scanned_at = dt.datetime.fromisoformat(feed_updated.replace("Z", "+00:00"))
        return (checked_at.tzinfo is not None and scanned_at.tzinfo is not None
                and checked_at > scanned_at)
    except ValueError:
        return False


def validate(root=scan.ROOT):
    sources = json.loads((root / 'sources.json').read_text())
    data = json.loads((root / 'data/opportunities.json').read_text())
    history = json.loads((root / 'data/history.json').read_text())
    # A 102-row file can still represent only 101 agencies if a name is
    # duplicated. A set-based feed comparison alone cannot detect this when
    # both the scanner and the health report inherit the same duplicate.
    names = [s['name'] for s in sources]
    if len(names) != 102 or len(set(names)) != len(names):
        raise ValueError('Source inventory must contain 102 distinct named targets')
    expected = set(names) | {'SAM.gov'}
    if set(data['source_status']) != expected:
        raise ValueError('Feed must report all 102 targets and deferred SAM.gov')
    if data['source_status']['SAM.gov'] != 'deferred':
        raise ValueError('SAM.gov must remain deferred')
    coverage = data.get('source_coverage')
    if coverage is not None:
        direct = {s['name'] for s in sources if s.get('mode') == 'direct_page'
                  and direct_configured(s)}
        fetched = sum('direct fetched' in data['source_status'][name] for name in direct)
        checks = {
            'total_targets': len(sources),
            'direct_configured': len(direct),
            'pending_direct': len(sources) - len(direct),
            'direct_fetched': fetched,
            'direct_not_fetched': len(direct) - fetched,
            'indirect_rss_succeeded': sum('indirect RSS ok' in status
                                          for status in data['source_status'].values()),
            'verified_open_contracts': sum(lead.get('status') == 'verified'
                                           and lead.get('open_status') == 'verified_open'
                                           for lead in data['opportunities']),
        }
        if any(coverage.get(key) != expected for key, expected in checks.items()):
            raise ValueError('Inconsistent direct source coverage metrics')
        # A count of 102 is insufficient if a named source was silently
        # replaced or omitted. Old feeds without this field remain readable.
        inventory = coverage.get('expected_source_names')
        if inventory is not None and inventory != sorted(s['name'] for s in sources):
            raise ValueError('Expected source inventory disagrees with sources.json')
    health = data.get('source_health')
    if health is not None:
        rows = health.get('sources', [])
        counts = health.get('counts', {})
        if len(rows) != len(sources) or {row.get('name') for row in rows} != {s['name'] for s in sources}:
            raise ValueError('Source health must report all 102 named targets')
        if counts.get('configured_direct') != coverage['direct_configured']:
            raise ValueError('Source health direct configuration disagrees with coverage')
        states = ('fetched_unverified', 'robots_blocked', 'access_required',
                  'adapter_not_implemented',
                  'http_blocked', 'redirect_blocked', 'rate_limited',
                  'unsupported_content', 'fetch_error', 'not_fetched',
                  'staged_official_url', 'not_configured')
        if sum(counts.get(key, 0) for key in states) != len(sources):
            raise ValueError('Source health states do not account for all targets')
        # Totals alone cannot detect two sources with swapped states, or
        # misreported counts that still sum to 102. Reconcile against the
        # publisher configuration and actual scan status, not the dashboard's
        # own potentially stale/altered summary.
        expected_health = source_health.summarize(sources, data['source_status'])
        expected_rows = {row['name']: row for row in expected_health['sources']}
        source_by_name = {source['name']: source for source in sources}
        stale_staging_names = set()
        for row in rows:
            reference = expected_rows[row['name']]
            stale_staging = _staged_after_published_scan(
                source_by_name[row['name']], row, data.get('updated'),
                data['source_status'][row['name']])
            if stale_staging:
                stale_staging_names.add(row['name'])
            for field in ('direct_state', 'indirect_state',
                          'provider_access_required', 'direct_url',
                          'staged_official_url', 'staged_provider_access_required'):
                if (stale_staging and field in (
                        'direct_state', 'staged_official_url',
                        'staged_provider_access_required')):
                    continue
                if row.get(field) != reference[field]:
                    raise ValueError('Source health state disagrees with scanner: '
                                     + row['name'] + ' / ' + field)
            # A successful homepage fetch can coexist with blocked individual
            # notices. Validate the underlying error evidence, not just the
            # single primary direct_state displayed by older dashboards.
            for field in ('detail_errors', 'pagination_errors',
                          'detail_access_state', 'pagination_access_state'):
                if row.get(field) != reference[field]:
                    raise ValueError('Source health diagnostic disagrees with scanner: '
                                     + row['name'] + ' / ' + field)
            # Extraction counts in a health row must agree with the raw
            # scanner evidence, including on staged, blocked and provider-
            # access-required sources. Otherwise a forged row can claim
            # individual-bid retrieval simply by increasing both attempted
            # and fetched counters (and the matching aggregate total).
            # Keep older feeds readable when a newer metric is absent.
            for field in ('individual_bid_records_found',
                          'detail_fetches_attempted', 'detail_budget_deferred',
                          'detail_candidates_deferred',
                          'individual_bid_details_fetched',
                          'pdf_fetch_attempts', 'pdf_budget_skips',
                          'result_award_links_excluded',
                          'external_provider_links_skipped',
                          'unverified_candidates'):
                if field in row and row[field] != reference[field]:
                    raise ValueError('Source health extraction disagrees with scanner: '
                                     + row['name'] + ' / ' + field)
            # PR #179 introduced non-exclusive failure reasons. Accept older
            # published feeds without these arrays, but never trust a supplied
            # array that contradicts the source's actual scan status.
            for field in ('detail_error_types', 'pagination_error_types'):
                if field in row and row[field] != reference[field]:
                    raise ValueError('Source health diagnostic disagrees with scanner: '
                                     + row['name'] + ' / ' + field)
        access_reasons = ('robots_blocked', 'http_blocked',
                          'redirect_blocked', 'rate_limited')
        diagnostic_counts = (
            'detail_errors', 'pagination_errors',
            'pagination_incomplete_sources',
            'detail_budget_deferred', 'detail_budget_incomplete_sources',
            'detail_candidates_deferred', 'detail_candidate_incomplete_sources',
        ) + tuple(
            kind + '_' + reason + '_sources'
            for kind in ('detail', 'pagination') for reason in access_reasons
        )
        # A source can be staged after the published scan. Reconcile only
        # the corresponding metadata counts, never direct fetches or leads.
        expected_counts = dict(expected_health['counts'])
        for name in stale_staging_names:
            expected_counts['staged_official_url'] -= 1
            expected_counts['not_configured'] += 1
            src = source_by_name[name]
            if src.get('provider_access_required') is True or src.get('delegated_provider'):
                expected_counts['staged_provider_access_required'] -= 1
        for field in states + ('configured_direct', 'configured_fetch_targets',
                               'configured_access_required',
                               'staged_provider_access_required',
                               'configured_unimplemented_adapters') + diagnostic_counts:
            if counts.get(field) != expected_counts[field]:
                raise ValueError('Source health count disagrees with scanner: ' + field)
        if counts.get('individual_bid_details_fetched', 0) != sum(
                row.get('individual_bid_details_fetched', 0) for row in rows):
            raise ValueError('Individual bid detail count disagrees with source health rows')
        for row in rows:
            fetched = row.get('individual_bid_details_fetched', 0)
            if not isinstance(fetched, int) or fetched < 0 or fetched > row.get('detail_fetches_attempted', 0):
                raise ValueError('Individual bid detail count exceeds attempted fetches')
            # Generic same-host notice extraction may fetch detail pages
            # without CivicPlus bidID listing cards. These counters describe
            # different extraction paths and must not be compared.
            if row['direct_state'] == 'staged_official_url' and row.get('direct_url'):
                raise ValueError('Staged official URLs cannot count as active monitoring')
    if not isinstance(data['opportunities'], list) or not isinstance(history['opportunities'], dict):
        raise ValueError('Invalid opportunity/history containers')
    ids = set()
    for lead in data['opportunities']:
        validate_active_notice(lead, scan.NOW)
        required = {'id', 'title', 'summary', 'url', 'source', 'location', 'category', 'published', 'status', 'lead_type', 'deadline', 'deadline_status'}
        if not required <= lead.keys() or lead['id'] in ids:
            raise ValueError('Invalid or duplicate lead')
        if not scan.eligible(lead['title'] + ' ' + lead['summary'], lead['source']):
            raise ValueError('Ineligible lead: ' + lead['id'])
        # Do not trust a URL merely because it starts with http(s):
        # malformed ports, embedded credentials and control characters can
        # otherwise survive the final publication gate if upstream regresses.
        if not notice_identity.canonical_url(lead['url']) or lead['id'] not in history['opportunities']:
            raise ValueError('Invalid URL or missing history')
        if lead['deadline'] and lead['deadline'] < scan.NOW.astimezone(scan.ZoneInfo('America/New_York')).date().isoformat():
            raise ValueError('Expired deadline: ' + lead['id'])
        ids.add(lead['id'])
    print(f'Validated {len(ids)} leads and {len(expected)-1} discovery targets')


if __name__ == '__main__':
    validate()
