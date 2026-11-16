"""Conservative, offline Tioga DPW bid-section isolation.

This parser is deliberately NOT a live-source adapter. It provides bounded
notice blocks for a future adapter, without inferring that any bid is open.
"""
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
import re

# Explicitly pinned official index; caller-supplied hosts are not trusted.
OFFICIAL_INDEX_URL = 'https://tiogacountyny.com/departments/public-works/'


class _Sections(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.sections = []
        self.current = None
        self.heading = None
        self.heading_parts = []
        self.link = None
        self.skip = 0
        self.in_bids = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'style', 'noscript'):
            self.skip += 1
        if self.skip:
            return
        if tag in ('h1', 'h2', 'h3', 'h4'):
            self.heading = tag
            self.heading_parts = []
        if tag == 'a' and self.current is not None:
            self.link = [attrs.get('href', ''), []]

    def handle_data(self, data):
        if self.skip:
            return
        if self.heading:
            self.heading_parts.append(data)
        elif self.link is not None:
            self.link[1].append(data)
        if self.current is not None and self.heading is None and self.link is None:
            # Attachment labels are metadata, not notice scope or deadline text.
            self.current['text'].append(data)

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript'):
            self.skip = max(0, self.skip - 1)
            return
        if tag == self.heading:
            title = ' '.join(' '.join(self.heading_parts).split())
            if tag == 'h2' and re.search(r'\bbids?\s*(?:&|and)\s*rfps?\b', title, re.I):
                self.in_bids = True
                self.current = None
            elif (tag == 'h1' and self.in_bids and self.current is not None
                  and re.fullmatch(r'NOTICE TO BIDDERS', title, re.I)):
                # The official demolition rebid embeds this heading inside
                # its H3 notice. Keep the notice, not a new bid section.
                pass
            elif tag in ('h1', 'h2'):
                self.in_bids = False
                self.current = None
            elif self.in_bids and re.match(r'^(?:bid|rfp|rfq)\s*:', title, re.I):
                self.current = {'title': title, 'text': [], 'links': []}
                self.sections.append(self.current)
            elif self.current is not None and tag in ('h2', 'h3', 'h4'):
                self.current = None
            self.heading = None
        if tag == 'a' and self.link is not None:
            if self.current is not None:
                self.current['links'].append((self.link[0], ' '.join(' '.join(self.link[1]).split())))
            self.link = None


def notice_sections(html, page_url, diagnostics=None):
    """Return independent notice blocks with same-host HTTPS attachment URLs.

    Never synthesize notice URLs; a section without a real link is not a
    publishable solicitation. Exclude results/awards before adapter handling.
    """
    # Validate the trusted index before parsing any untrusted page content.
    try:
        index = urlsplit(page_url)
        host = index.hostname
        allowed_index_port = index.port in (None, 443)
    except ValueError:
        return []
    # Only the explicitly configured official index may authorize attachments.
    # A caller-controlled HTTPS host is never evidence of county ownership.
    if page_url != OFFICIAL_INDEX_URL:
        return []
    # Only a canonical HTTPS index may authorize official attachments.
    # Reject userinfo, alternate ports and query/fragment variants.
    if (not host or index.scheme != 'https' or not allowed_index_port
            or index.username is not None or index.password is not None
            or index.query or index.fragment):
        return []
    parser = _Sections()
    parser.feed(html)
    if diagnostics is not None:
        diagnostics['total_sections'] = len(parser.sections)
        diagnostics['sections_truncated'] = max(0, len(parser.sections) - 1000)
        diagnostics['attachments_truncated'] = 0
    output = []
    for section in parser.sections[:1000]:
        title = section['title']
        if re.search(r'\b(?:results?|awards?|tabulations?)\b', title, re.I):
            continue
        links = []
        seen_urls = set()
        for href, label in section['links']:
            # Empty and fragment-only hrefs point back to the index, not a bid document.
            if not href or not href.strip() or href.strip().startswith(('#', '?')):
                continue
            # Historical result/award attachments must never be offered as bid documents.
            try:
                href_path = urlsplit(href).path
            except ValueError:
                continue
            if re.search(r'\b(?:results?|awards?|tabulations?)\b', label, re.I) or re.search(r'\b(?:results?|awards?|tabulations?)\b', href_path, re.I):
                continue
            # Invalid IPv6 authorities can fail during urljoin or hostname
            # parsing, not just when reading .port. Skip the malformed link.
            try:
                url = urljoin(page_url, href)
                parts = urlsplit(url)
                allowed_port = parts.port in (None, 443)
                attachment_host = parts.hostname
            except ValueError:
                continue
            if (parts.scheme == 'https' and attachment_host == host
                    and allowed_port
                    and not parts.username and not parts.password
                    and parts.path != urlsplit(page_url).path
                    and not parts.fragment and url not in seen_urls):
                seen_urls.add(url)
                links.append({'url': url, 'label': label})
                if len(links) >= 30:
                    if diagnostics is not None:
                        diagnostics['attachments_truncated'] += 1
                    break
        output.append({'title': title, 'text': ' '.join(' '.join(section['text']).split()), 'links': links})
    return output


def deadline_evidence_status(index_deadline, document_deadline):
    """Compare independently verified ISO-8601 deadline strings, without guessing.

    This is a diagnostic only: agreement does not prove that a bid is open.
    A missing deadline or a disagreement requires manual verification before
    any future adapter may publish a notice.
    """
    from datetime import datetime

    def parse(value):
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        # Offset-aware timestamps are required to avoid local-time ambiguity.
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return parsed

    index = parse(index_deadline)
    document = parse(document_deadline)
    if index is None or document is None:
        return 'verification_required'
    return 'consistent' if index == document else 'conflict'
