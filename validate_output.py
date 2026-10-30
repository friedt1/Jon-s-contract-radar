"""Validate the dashboard feed without requiring network access."""
import json
from pathlib import Path
import scan
from source_config import direct_configured
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


def validate(root=scan.ROOT):
    sources = json.loads((root / 'sources.json').read_text())
    data = json.loads((root / 'data/opportunities.json').read_text())
    history = json.loads((root / 'data/history.json').read_text())
    expected = {s['name'] for s in sources} | {'SAM.gov'}
    if len(sources) != 102 or set(data['source_status']) != expected:
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
        if not lead['url'].startswith(('https://', 'http://')) or lead['id'] not in history['opportunities']:
            raise ValueError('Invalid URL or missing history')
        if lead['deadline'] and lead['deadline'] < scan.NOW.astimezone(scan.ZoneInfo('America/New_York')).date().isoformat():
            raise ValueError('Expired deadline: ' + lead['id'])
        ids.add(lead['id'])
    print(f'Validated {len(ids)} leads and {len(expected)-1} discovery targets')


if __name__ == '__main__':
    validate()
