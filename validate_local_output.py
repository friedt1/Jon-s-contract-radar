"""Validate local public artifacts without touching contract data."""
import argparse
import json
import pathlib
from local_scan import ROOT, SERVICES, canonical, date


def validate(data_dir, sources_path=ROOT / 'local_sources.json'):
    feed = json.loads((data_dir / 'local_leads.json').read_text())
    history = json.loads((data_dir / 'local_history.json').read_text())
    sources = json.loads(sources_path.read_text())
    assert set(feed['source_status']) == {s['name'] for s in sources}, 'Missing local source status'
    assert feed['updated'] == history['updated'], 'Mismatched feed/history run'
    assert feed['request_sources_ok'] == sum(s['state'] == 'ok' and s['kind'] != 'news' for s in feed['source_status'].values())
    assert isinstance(history['leads'], dict)
    assert len(feed['leads']) == len({lead['id'] for lead in feed['leads']}), 'Duplicate current IDs'
    if feed['updated'] is None:
        assert not feed['leads'] and not history['leads'], 'Unscanned data cannot contain leads'
    else:
        assert date(feed['updated']), 'Invalid scan date'
        assert any(s['state'] == 'ok' for s in feed['source_status'].values()), 'No successful sources'
    if feed.get('schema_version') == 2:
        metrics = feed['metrics']
        assert metrics['verified_requests'] == metrics['qualified_leads'] == 0
        assert metrics['request_candidates'] == sum(x['lead_type'] == 'service_request' for x in feed['leads'])
        assert metrics['news_context'] == sum(x['lead_type'] == 'news_context' for x in feed['leads'])
        assert metrics['failed_sources'] == sum(x['state'] == 'error' for x in feed['source_status'].values())
        assert metrics['records_inspected'] == sum(x.get('records_inspected', 0) for x in feed['source_status'].values())
        for status in feed['source_status'].values():
            assert status['checked_at'] == feed['updated']
            if status['state'] == 'ok':
                assert status['records_inspected'] == status['requests'] + status['articles'] + sum(status['rejected'].values())
    for uid, lead in history['leads'].items():
        assert uid == lead['id']
        assert lead['lead_type'] in ('service_request', 'news_context')
        assert lead['services'] and set(lead['services']) <= set(SERVICES)
        assert lead['customer_type'] in ('homeowner', 'commercial', 'unspecified')
        assert 0 <= lead['score'] <= 100
        assert (lead['score'] < 50) == (lead['lead_type'] == 'news_context'), 'News/request score separation'
        assert lead['location'].endswith((', NY', ', PA'))
        assert canonical(lead['url']) == lead['url']
        assert lead['source_links'] and all(canonical(link['url']) == link['url'] for link in lead['source_links'])
        if feed.get('schema_version') == 2 and uid in {x['id'] for x in feed['leads']}:
            assert lead['evidence_snippet'] and lead['limitations']
            assert lead['duplicate_key'] == lead['fingerprint']
            assert lead['verification_state'] == ('unverified_candidate' if lead['lead_type'] == 'service_request' else 'not_a_request')
            assert lead['confidence']
        assert date(lead['published']) <= date(lead['last_seen'])
        assert date(lead['first_seen']) <= date(lead['last_seen'])
    for lead in feed['leads']:
        assert history['leads'][lead['id']] == lead, 'Current lead missing from history'
        assert lead['last_seen'] == feed['updated']
        assert 0 <= (date(feed['updated']) - date(lead['published'])).total_seconds() <= 30 * 86400
    print(f"Validated {len(feed['leads'])} local discoveries, {len(history['leads'])} historical entries, {len(sources)} source statuses")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=pathlib.Path, default=ROOT / 'data')
    parser.add_argument('--sources', type=pathlib.Path, default=ROOT / 'local_sources.json')
    args = parser.parse_args()
    validate(args.data_dir, args.sources)
