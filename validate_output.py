"""Validate the dashboard feed without requiring network access."""
import json
from pathlib import Path
import scan


def validate(root=scan.ROOT):
    sources = json.loads((root / 'sources.json').read_text())
    data = json.loads((root / 'data/opportunities.json').read_text())
    history = json.loads((root / 'data/history.json').read_text())
    expected = {s['name'] for s in sources} | {'SAM.gov'}
    if len(sources) != 102 or set(data['source_status']) != expected:
        raise ValueError('Feed must report all 102 targets and deferred SAM.gov')
    if data['source_status']['SAM.gov'] != 'deferred':
        raise ValueError('SAM.gov must remain deferred')
    if not isinstance(data['opportunities'], list) or not isinstance(history['opportunities'], dict):
        raise ValueError('Invalid opportunity/history containers')
    ids = set()
    for lead in data['opportunities']:
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
