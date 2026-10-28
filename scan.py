"""Public news-lead discovery. Not a verified bid feed. Python stdlib only."""
import datetime as dt
import email.utils
import hashlib
import json
import pathlib
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

OUT = pathlib.Path(__file__).resolve().parent / 'data' / 'opportunities.json'
AREAS = ['Elmira', 'Horseheads', 'Corning', 'Bath', 'Ithaca', 'Binghamton', 'Owego', 'Waverly', 'Watkins Glen', 'Penn Yan', 'Sayre', 'Towanda', 'Cortland', 'Geneva', 'Hornell', 'Mansfield']
CATEGORIES = {'Tree removal': ['tree removal', 'tree cutting', 'tree felling'], 'Tree trimming': ['tree trimming', 'tree pruning'], 'Land clearing': ['land clearing', 'right of way clearing'], 'Vegetation management': ['vegetation management', 'brush clearing', 'utility clearing'], 'Storm cleanup': ['storm debris', 'storm cleanup']}
QUERIES = ['("tree removal" OR "tree trimming" OR "vegetation management") (bid OR RFP OR contract) (Elmira OR Ithaca OR Binghamton OR Corning)', '("land clearing" OR "brush clearing" OR "storm debris") (bid OR tender OR contract) ("New York" OR Pennsylvania)']

def clean(s):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]*>', ' ', s or '')).strip()

def main():
    now = dt.datetime.now(dt.timezone.utc)
    status, found = {}, {}
    for i, query in enumerate(QUERIES, 1):
        name = f'Google News RSS {i}'
        try:
            url = 'https://news.google.com/rss/search?' + urllib.parse.urlencode({'q': query, 'hl': 'en-US', 'gl': 'US', 'ceid': 'US:en'})
            request = urllib.request.Request(url, headers={'User-Agent': 'ContractRadar/1.0'})
            with urllib.request.urlopen(request, timeout=25) as response:
                raw = response.read(2_000_000)
            root = ET.fromstring(raw)
            for item in root.findall('.//item'):
                title, summary = clean(item.findtext('title')), clean(item.findtext('description'))
                link = item.findtext('link', '').strip()
                if not link.startswith('https://'):
                    continue
                content = (title + ' ' + summary).lower()
                if not any(term in content for terms in CATEGORIES.values() for term in terms):
                    continue
                if not any(a.lower() in content for a in AREAS) and 'new york' not in content and 'pennsylvania' not in content:
                    continue
                category = next((c for c, terms in CATEGORIES.items() if any(term in content for term in terms)), 'Tree removal')
                location = next((a for a in AREAS if a.lower() in content), 'Regional — verify location')
                try:
                    published = email.utils.parsedate_to_datetime(item.findtext('pubDate', '')).date().isoformat()
                except (TypeError, ValueError):
                    published = ''
                if published and (now.date() - dt.date.fromisoformat(published)).days > 45:
                    continue
                uid = hashlib.sha256(link.encode()).hexdigest()[:16]
                found[uid] = {'id': uid, 'title': title, 'summary': summary[:500], 'url': link, 'source': 'Google News RSS', 'location': location, 'category': category, 'published': published, 'status': 'unverified'}
            status[name] = 'ok'
        except Exception as exc:
            status[name] = 'error: ' + type(exc).__name__
    if not found and not any(v == 'ok' for v in status.values()) and OUT.exists():
        previous = json.loads(OUT.read_text())
        found = {x['id']: x for x in previous.get('opportunities', []) if 'id' in x}
    data = {'updated': now.isoformat(timespec='seconds'), 'opportunities': sorted(found.values(), key=lambda x: x['published'], reverse=True)[:150], 'source_status': {**status, 'SAM.gov': 'Deferred'}, 'coverage_note': 'Public news leads only; not verified bids. Travel time, procurement status, and deadlines unverified. Coverage incomplete; SAM.gov deferred.'}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    print('Candidates:', len(found), 'Feed statuses:', status)

if __name__ == '__main__':
    main()
