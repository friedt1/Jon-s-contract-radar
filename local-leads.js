'use strict';
const localElement = selector => document.querySelector(selector);
const escapeLocal = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[char]));
function publicLink(url) {
  try { const parsed = new URL(url); return parsed.protocol === 'https:' && !parsed.username && !parsed.password ? parsed.href : ''; }
  catch { return ''; }
}
let scanWarning = '';
let currentLocal = [], historyLocal = [], localLoadError = '', historyLoadError = '';
function renderLocal() {
  const value = id => localElement('#local-' + id).value;
  const historical = value('view') === 'history';
  const query = value('query').toLowerCase();
  const rows = (historical ? historyLocal : currentLocal).filter(lead =>
    (!value('kind') || lead.lead_type === value('kind')) &&
    (!value('service') || lead.services.includes(value('service'))) &&
    (!value('customer') || lead.customer_type === value('customer')) &&
    (!value('state') || lead.location.endsWith(', ' + value('state'))) &&
    lead.score >= Number(value('score')) &&
    [lead.title, lead.summary, lead.location, lead.source].join(' ').toLowerCase().includes(query));
  rows.sort((a, b) => value('sort') === 'score' ? b.score - a.score : String(b[value('sort') === 'new' ? 'first_seen' : 'published']).localeCompare(String(a[value('sort') === 'new' ? 'first_seen' : 'published'])));
  localElement('#local-count').textContent = rows.length;
  localElement('#local-status').textContent = localLoadError || (!historical && scanWarning) || (historical && historyLoadError) || (historical ? 'Discovery history — availability is unverified; these are not necessarily current requests.' : 'Latest successful scan. Request candidates are unverified; news is context only.');
  localElement('#local-cards').innerHTML = rows.map(lead => {
    const request = lead.lead_type === 'service_request';
    const links = lead.source_links.map(link => {
      const href = publicLink(link.url);
      return href ? '<a target="_blank" rel="noopener noreferrer" href="' + escapeLocal(href) + '">' + escapeLocal(link.source) + ' · original source</a>' : 'Source link unavailable';
    }).join(' · ');
    return '<article class="card ' + (request ? 'request' : 'news') + '"><span class="badge">' + (request ? 'Public service request · unverified' : 'News context · not a customer request') + '</span><span class="badge">Relevance ' + escapeLocal(lead.score) + '/100</span><h2>' + escapeLocal(lead.title) + '</h2><small>' + escapeLocal(lead.location) + ' · ' + escapeLocal(lead.customer_type) + ' · Posted ' + escapeLocal(lead.published.slice(0, 10)) + '</small><p>' + escapeLocal(lead.evidence_snippet || lead.summary) + '</p><p>' + escapeLocal(lead.confidence || 'Heuristic match; unverified') + ' · ' + escapeLocal(lead.verification_state || 'Unverified discovery') + '</p><p>' + escapeLocal((lead.limitations || []).join(' · ')) + '</p><p>' + lead.services.map(service => '<span class="badge">' + escapeLocal(service) + '</span>').join('') + '</p><p>' + escapeLocal(lead.geography_note) + '</p><small>Discovered ' + escapeLocal(lead.first_seen.slice(0, 10)) + ' · Last observed ' + escapeLocal(lead.last_seen.slice(0, 10)) + '</small><p>' + escapeLocal(lead.score_reasons.join(' · ')) + '</p><p>' + links + '</p></article>';
  }).join('') || '<p>No matching discoveries. Limited coverage and source failures can produce an empty scan. Try the history or news filters; no leads are fabricated.</p>';
}
['query','service','kind','customer','state','score','view','sort'].forEach(id => localElement('#local-' + id).addEventListener(id === 'query' ? 'input' : 'change', renderLocal));
async function loadLocalFeed(path) {
  const response = await fetch(path + '?ts=' + Date.now());
  if (!response.ok) throw Error('Feed unavailable');
  return response.json();
}
async function loadLocal() {
  const [feed, history] = await Promise.allSettled([loadLocalFeed('./data/local_leads.json'), loadLocalFeed('./data/local_history.json')]);
  if (feed.status === 'fulfilled') {
    const data = feed.value;
    const age = data.updated ? Date.now() - Date.parse(data.updated) : Infinity;
    // Do not present expired posts as active when scheduled scanning stalls.
    currentLocal = (data.leads || []).filter(lead => {
      const postAge = Date.now() - Date.parse(lead.published);
      return Number.isFinite(postAge) && postAge >= 0 && postAge <= 30 * 86400000;
    });
    if (age > 12 * 3600000) scanWarning = 'Scan is stale (over 12 hours). Source health below describes the last successful scan; current coverage is unknown.';
    const metrics = data.metrics;
    localElement('#local-metrics').textContent = metrics
      ? metrics.records_inspected + ' records inspected · ' + metrics.request_candidates + ' request candidates · ' + metrics.news_context + ' news items · ' + metrics.verified_requests + ' verified requests · ' + metrics.qualified_leads + ' qualified leads. Automated candidates require manual review.'
      : 'Detailed source-quality metrics unavailable for this older scan; no requests have been verified.';
    localElement('#local-updated').textContent = data.updated ? data.updated.replace('T', ' ').slice(0, 16) : 'Not run';
    localElement('#local-sources').textContent = data.updated ? data.request_sources_ok : 'Not run';
    localElement('#local-coverage').textContent = data.coverage_note;
    localElement('#local-health').innerHTML = Object.entries(data.source_status || {}).map(([name, status]) => '<li class="' + (status.state === 'error' ? 'error' : '') + '">' + escapeLocal(name) + ': ' + escapeLocal(status.state === 'ok' ? 'accessible at last scan · ' + status.candidates + ' candidates' + (status.records_inspected === undefined ? '' : ' / ' + status.records_inspected + ' inspected · rejected: ' + JSON.stringify(status.rejected || {})) : 'unavailable · ' + (status.error || 'not run')) + '</li>').join('');
    if (!data.updated) localLoadError = 'Local scanning has not run yet. No customer requests have been verified.';
    else if (!data.request_sources_ok) localLoadError = 'Customer-request sources unavailable. Only news context was scanned; customer coverage is unknown.';
  } else localLoadError = 'Local feed unavailable. Contract Radar is independent and remains accessible.';
  if (history.status === 'fulfilled') historyLocal = Object.values(history.value.leads || {});
  else historyLoadError = 'Discovery history unavailable; try the latest scan.';
  renderLocal();
}
loadLocal();
