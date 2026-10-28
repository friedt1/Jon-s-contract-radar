"""Bounded public customer-request discovery. No account, private scraping or contacts.
Independent of scan.py and its procurement files; Python standard library only.
"""
import argparse
import datetime as dt
import email.utils
import hashlib
from html.parser import HTMLParser
import ipaddress
import json
import pathlib
import re
import tempfile
import time
import urllib.parse as up
import urllib.request as ur
import urllib.robotparser
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parent
USER_AGENT = 'LocalCustomerLeadRadar/1.0'
MAX_BYTES = 1_000_000
SERVICES = {
    'Tree removal': r'\b(?:tree removal|remove (?:a |the |my |our |\d+ )?trees?|trees? (?:removed|cut down)|cut down (?:a |the |my |our )?trees?)\b',
    'Tree trimming': r'\b(?:tree (?:trimming|pruning)|trim (?:a |the |my |our )?trees?|trees? trimmed)\b',
    'Stump grinding': r'\b(?:stump (?:grinding|removal)|stumps? (?:ground|removed)|grind (?:a |the |my |our )?stumps?)\b',
    'Storm cleanup': r'\b(?:storm (?:cleanup|clean-up|debris)|fallen tree removal|emergency tree removal)\b',
    'Land clearing': r'\b(?:land clearing|lot clearing|forestry mulching|clear (?:a |the |my |our )?(?:lot|land))\b',
}
# Conservative town screen, not a road-routing service. Ambiguous names require state evidence.
PLACES = {
    'Elmira': ('NY', False), 'Horseheads': ('NY', False), 'Big Flats': ('NY', True),
    'Corning': ('NY', True), 'Watkins Glen': ('NY', False), 'Ithaca': ('NY', True),
    'Binghamton': ('NY', False), 'Owego': ('NY', False), 'Waverly': ('NY', True),
    'Bath': ('NY', True), 'Hornell': ('NY', False), 'Cortland': ('NY', True),
    'Sayre': ('PA', True), 'Athens': ('PA', True), 'Towanda': ('PA', False),
    'Wellsboro': ('PA', False), 'Mansfield': ('PA', True), 'Troy': ('PA', True),
    'Williamsport': ('PA', True), 'Montoursville': ('PA', False), 'Tunkhannock': ('PA', False),
}
REQUEST = re.compile(r"\b(?:need(?:s|ing)?|looking for|seeking|iso|in search of|can (?:anyone|someone)|recommend(?:ation)?s?|wanted|request(?:ing)? (?:a )?quote|who (?:can|does))\b", re.I)
EXCLUDE = re.compile(r'\b(?:we (?:offer|provide)|our services|call us|free estimates|now hiring|help wanted|job opening|for sale|no longer need|already (?:found|hired)|all sorted|request (?:closed|fulfilled)|work completed|no (?:longer )?(?:need|request)|looking for (?:work|customers)|services available|book (?:now|today))\b', re.I)
NEWS = re.compile(r'\b(?:reported|according to|press release|news release|city council|study finds|breaking news)\b', re.I)


class Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.skip += 1
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.skip = max(0, self.skip - 1)
    def handle_data(self, value):
        if not self.skip: self.parts.append(value)


def text(value):
    parser = Text(); parser.feed(value or '')
    return re.sub(r'\s+', ' ', ' '.join(parser.parts)).strip()


def safe_url(url):
    try:
        parsed = up.urlsplit(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None, 443): return False
        host = parsed.hostname.lower()
        if host == 'localhost' or '.' not in host or host.endswith(('.local', '.internal', '.localhost')): return False
        try: return ipaddress.ip_address(host).is_global
        except ValueError: return True
    except (ValueError, TypeError): return False


def canonical(url):
    if not safe_url(url): return ''
    p = up.urlsplit(url)
    query = [(k, v) for k, v in up.parse_qsl(p.query) if not k.lower().startswith('utm_') and k.lower() not in ('fbclid', 'gclid')]
    return up.urlunsplit(('https', p.netloc.lower(), p.path.rstrip('/') or '/', up.urlencode(sorted(query)), ''))


class NoRedirect(ur.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never follow unexpected login, private-network or unapproved destinations.
        raise ValueError('redirect refused; review source URL')


def fetch(url):
    if not safe_url(url): raise ValueError('public HTTPS URL required')
    request = ur.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': 'application/json,application/rss+xml,application/atom+xml,application/xml,text/plain'})
    with ur.build_opener(NoRedirect).open(request, timeout=20) as response:
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES: raise ValueError('response exceeds limit')
        return data.decode('utf-8')


def date(value):
    try:
        result = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        try: result = email.utils.parsedate_to_datetime(value)
        except (ValueError, TypeError, OverflowError): return None
    return result.astimezone(dt.timezone.utc) if result.tzinfo else result.replace(tzinfo=dt.timezone.utc)


def location(body):
    if re.search(r'\b(?:Ontario|Canada|California|Michigan|Ohio|Georgia|Texas|Massachusetts|Connecticut)\b', body, re.I): return None
    for town, (state, ambiguous) in sorted(PLACES.items(), key=lambda pair: -len(pair[0])):
        match = re.search(r'\b' + re.escape(town) + r'\b', body, re.I)
        if not match: continue
        state_pattern = r'\b(?:NY|New York)\b' if state == 'NY' else r'\b(?:PA|Pennsylvania)\b'
        # An explicit conflicting state next to the town always excludes it.
        if re.search(r'\b' + re.escape(town) + r'[,\s]+(?:[A-Z]{2})\b', body):
            if not re.search(r'\b' + re.escape(town) + r'[,\s]+' + state + r'\b', body): continue
        if ambiguous and not re.search(state_pattern, body, re.I): continue
        return f'{town}, {state}'
    return None


def candidate(record, source, now):
    title = text(record.get('title', '')); body = text(record.get('body', ''))
    combined = title + ' ' + body
    published = date(record.get('published', ''))
    if published is None or not 0 <= (now - published).total_seconds() <= 30 * 86400: return None
    url = canonical(record.get('url', ''))
    place = location(combined)
    services = [name for name, pattern in SERVICES.items() if re.search(pattern, combined, re.I)]
    if not url or not place or not services: return None
    is_request = source['kind'] != 'news' and bool(REQUEST.search(combined)) and not EXCLUDE.search(combined) and not NEWS.search(combined)
    # Public social/feed advertisements and chatter are not useful customer leads.
    if source['kind'] != 'news' and not is_request: return None
    kind = 'service_request' if is_request else 'news_context'
    customer = ('commercial' if re.search(r'\b(?:our business|my business|commercial property|our office|our store|our restaurant|our parking lot)\b', combined, re.I)
                else 'homeowner' if re.search(r'\b(?:my yard|our yard|my home|our home|my house|our house|my backyard|our backyard)\b', combined, re.I) else 'unspecified')
    # Do not republish incidental phone numbers/emails; source is the contact route.
    def redact(s):
        s = re.sub(r'\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b', '[contact on source]', s)
        return re.sub(r'(?<!\w)(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}(?!\w)', '[contact on source]', s)
    title = redact(title or body[:160]); body = redact(body)
    age = (now - published).days
    score = min(100, (65 if is_request else 10) + (15 if age <= 7 else 5) + (10 if customer != 'unspecified' else 0) + min(10, 5 * len(services)))
    # Same title, town and day cross-posts are intentionally conservative matches.
    fingerprint = hashlib.sha256((re.sub(r'\W+', ' ', title.lower()).strip() + '|' + place + '|' + published.date().isoformat()).encode()).hexdigest()[:20]
    return {'id': hashlib.sha256(url.encode()).hexdigest()[:20], 'fingerprint': fingerprint,
            'title': title[:220], 'summary': body[:550], 'url': url, 'source': source['name'],
            'source_links': [{'source': source['name'], 'url': url}], 'location': place,
            'geography_note': 'Nearby town screen; actual job site and two-hour driving time unverified',
            'published': published.isoformat(timespec='seconds'), 'services': services, 'customer_type': customer,
            'lead_type': kind, 'verification': 'Public request candidate; confirm need and availability at source' if is_request else 'News context only — not a customer request',
            'score': score, 'score_reasons': ['Service and nearby town mentioned', 'Explicit request language' if is_request else 'Indirect news; no verified customer request', f'Published {age} days ago']}


def records(source, getter=None):
    getter = getter or fetch
    kind = source['kind']; url = source['url']
    if kind == 'rss':
        # Only operator-reviewed public feeds; honor robots and fail closed.
        if source.get('public_feed_reviewed') is not True: raise ValueError('review public feed terms before enabling')
        root = up.urlsplit(url)
        robots = urllib.robotparser.RobotFileParser()
        robots.parse(getter(f'{root.scheme}://{root.netloc}/robots.txt').splitlines())
        if not robots.can_fetch(USER_AGENT, url): raise ValueError('robots disallows feed')
    payload = getter(url)
    if kind == 'mastodon':
        entries = json.loads(payload)
        if not isinstance(entries, list): raise ValueError('public timeline expected')
        for item in entries[:40]:
            if item.get('visibility') != 'public' or item.get('reblog'): continue
            body = item.get('content', '')
            yield {'title': '', 'body': body, 'url': item.get('url', ''), 'published': item.get('created_at', '')}
    else:
        root = ET.fromstring(payload)
        atom = '{http://www.w3.org/2005/Atom}'
        for item in (root.findall('.//item') + root.findall(f'{atom}entry'))[:100]:
            link = item.findtext('link', '')
            if not link:
                link = next((x.get('href', '') for x in item.findall(f'{atom}link') if x.get('rel', 'alternate') == 'alternate'), '')
            yield {'title': item.findtext('title') or item.findtext(f'{atom}title', ''),
                   'body': item.findtext('description') or item.findtext(f'{atom}content') or item.findtext(f'{atom}summary', ''),
                   'url': link, 'published': item.findtext('pubDate') or item.findtext(f'{atom}published') or item.findtext(f'{atom}updated', '')}


def validate_sources(sources):
    if not sources or len(sources) > 30: raise ValueError('1–30 sources required')
    names = set()
    for source in sources:
        if source['name'] in names: raise ValueError('duplicate source name')
        names.add(source['name'])
        if not safe_url(source['url']) or source['kind'] not in ('mastodon', 'rss', 'news'): raise ValueError('invalid public source')
        host = up.urlsplit(source['url']).hostname
        if any(host == h or host.endswith('.' + h) for h in ('facebook.com', 'nextdoor.com', 'reddit.com')): raise ValueError('restricted social sources unsupported')


def assemble(sources, previous, now, getter=None, pause=None):
    getter = getter or fetch
    pause = pause or time.sleep
    validate_sources(sources)
    found = {}; status = {}; successful = 0; request_successful = 0
    old = previous.get('leads', {})
    # Fail rather than overwrite corrupt history.
    if not isinstance(old, dict): raise ValueError('invalid history')
    alias = {}
    for uid, item in old.items():
        alias[item['fingerprint']] = uid
        for link in item['source_links']: alias[canonical(link['url'])] = uid
    for source in sources:
        staged = []
        try:
            for record in records(source, getter):
                lead = candidate(record, source, now)
                if lead: staged.append(lead)
            successful += 1
            if source['kind'] != 'news': request_successful += 1
            status[source['name']] = {'state': 'ok', 'candidates': len(staged), 'kind': source['kind']}
        except Exception as error:
            status[source['name']] = {'state': 'error', 'error': type(error).__name__ + (f' HTTP {error.code}' if hasattr(error, 'code') else ''), 'kind': source['kind']}
            continue
        finally:
            pause(1)  # Sequential, bounded, no retries, no credentials or destination crawling.
        for lead in staged:
            uid = alias.get(lead['url']) or alias.get(lead['fingerprint']) or lead['id']
            alias[lead['url']] = alias[lead['fingerprint']] = uid
            lead['id'] = uid
            existing = found.get(uid, old.get(uid, {}))
            links = {x['url']: x for x in existing.get('source_links', []) + lead['source_links']}
            # A news duplicate must never downgrade an explicitly observed request.
            if uid in found and found[uid]['lead_type'] == 'service_request' and lead['lead_type'] == 'news_context': lead = dict(found[uid])
            lead.update(source_links=list(links.values()), first_seen=existing.get('first_seen', now.isoformat(timespec='seconds')), last_seen=now.isoformat(timespec='seconds'))
            found[uid] = lead
    if not successful: raise RuntimeError('All local sources failed; previous feed and history preserved: ' + json.dumps(status))
    historical = dict(old)
    historical.update(found)
    historical = dict(sorted(historical.items(), key=lambda pair: pair[1]['last_seen'], reverse=True)[:2000])
    feed = {'updated': now.isoformat(timespec='seconds'), 'request_sources_ok': request_successful,
            'source_status': status, 'leads': sorted(found.values(), key=lambda x: (-x['score'], x['id'])),
            'coverage_note': 'Public hashtag timelines and reviewed feeds only; sparse coverage, not all local requests. News is context only. Town screen approximates the Elmira NY / northern PA service area; verify driving time. Failed sources are not evidence of no requests.'}
    history = {'updated': feed['updated'], 'leads': historical}
    return feed, history


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w', dir=path.parent, delete=False, encoding='utf-8') as tmp:
        json.dump(data, tmp, indent=2, ensure_ascii=False); tmp.write('\n')
        name = tmp.name
    pathlib.Path(name).replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=pathlib.Path, default=ROOT / 'data')
    args = parser.parse_args()
    sources = json.loads((ROOT / 'local_sources.json').read_text())
    history_path = args.data_dir / 'local_history.json'
    previous = json.loads(history_path.read_text()) if history_path.exists() else {'leads': {}}
    feed, history = assemble(sources, previous, dt.datetime.now(dt.timezone.utc))
    write_json(history_path, history)
    write_json(args.data_dir / 'local_leads.json', feed)
    print(f"Local scan: {len(feed['leads'])} candidates; {feed['request_sources_ok']} request feeds accessible; inspect source_status for partial failures")


if __name__ == '__main__': main()
