// Exercise the existing dashboard script without a browser or network dependency.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const elements = new Map();
const element = selector => {
  if (!elements.has(selector)) elements.set(selector, {value: '', textContent: '', innerHTML: '', addEventListener() {}});
  return elements.get(selector);
};
element('#sort').value = 'new';
const feed = JSON.parse(fs.readFileSync('data/opportunities.json', 'utf8'));
const fixture = {title: '<script>unsafe</script> Tree removal bid', summary: 'Tree removal', category: 'Tree removal', source: 'Chemung', location: 'Elmira', published: '2026-10-28', url: 'https://example.org/bid'};
const context = vm.createContext({document: {querySelector: element}, fetch: async () => ({ok: true, json: async () => ({...feed, source_coverage: {direct_fetched: 3, pending_direct: 84}, opportunities: [fixture]})})});
const html = fs.readFileSync('index.html', 'utf8');
vm.runInContext(html.split('<script>')[1].split('</script>')[0], context);
setImmediate(() => {
  assert.equal(element('#count').textContent, 1);
  assert.ok(element('#cards').innerHTML.includes('&lt;script&gt;'));
  assert.ok(!element('#cards').innerHTML.includes('<script>'));
  assert.equal(element('#sources').textContent, 3);
  assert.equal(element('#pending').textContent, 84);
  assert.notEqual(element('#sources').textContent, Object.values(feed.source_status).filter(x => /direct fetched|indirect RSS ok/.test(x)).length);
  element('#type').value = 'Storm cleanup';
  vm.runInContext('render()', context);
  assert.equal(element('#count').textContent, 0);
  element('#type').value = '';
  element('#q').value = 'elmira';
  vm.runInContext('render()', context);
  assert.equal(element('#count').textContent, 1);
  element('#q').value = 'unrelated';
  vm.runInContext('render()', context);
  assert.equal(element('#count').textContent, 0);
  console.log('Dashboard feed, escaping, service filter, search, and source count passed');
});
