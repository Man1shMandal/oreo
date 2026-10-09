import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../public/chat.js', import.meta.url), 'utf8');

function harness(events) {
  let writes = 0;
  let streamed = '', html = '';
  const body = { classList: { add() {}, remove() {} }, append() {}, set innerHTML(value) { writes++; html = value; }, get innerHTML() { return html; } };
  const node = () => ({ classList: { add() {}, remove() {}, toggle() {} }, append() {}, remove() {}, querySelector: () => body });
  const elements = new Map();
  const requests = [];
  const timers = new Map();
  const sandbox = {
    $, epoch: 1, chatId: null, pending: [], preferences: { web: false }, web: false, stopListening: null,
    rows: [], conversations: [], busy: false, ready: true,
    composer: { value: 'Remember Cedar', style: {}, focus() {}, dispatchEvent() {} },
    timeline: { querySelector: () => null, append() {} },
    stage: { scrollHeight: 100, scrollTop: 0, clientHeight: 100 },
    document: { createTextNode() { return { appendData(value) { streamed += value; } }; } },
    controls() {}, tray() {}, notify() {}, micState() {}, message: node, markdown: text => text,
    sourceLinks() {}, renderSidebar() {}, render() {}, Event: class {},
    TextDecoder, Uint8Array, Date,
    setTimeout(callback) { const id = timers.size + 1; timers.set(id, callback); return id; },
    clearTimeout(id) { timers.delete(id); },
    async account() { requests.push('account'); },
    async request(path) {
      requests.push(path);
      const bytes = new TextEncoder().encode(events.map(e => 'data: ' + JSON.stringify(e) + '\n\n').join(''));
      let read = false;
      return { ok: true, headers: { get: () => 'text/event-stream' }, body: { getReader: () => ({
        async read() { if (read) return { done: true }; read = true; return { done: false, value: bytes }; },
      }) } };
    },
  };
  function $(selector) {
    if (!elements.has(selector)) elements.set(selector, { disabled: false, value: 'haiku', classList: { toggle() {} }, setAttribute() {} });
    return elements.get(selector);
  }
  vm.createContext(sandbox);
  vm.runInContext(source.slice(source.indexOf('async function send()'), source.indexOf("$('#send').onclick")), sandbox);
  return { sandbox, requests, timers, writes: () => writes, streamed: () => streamed, html: () => body.innerHTML };
}

test('stream batches rendering and unlocks send without account round trips', async () => {
  const h = harness([
    { conversation_id: 'chat-1' },
    ...Array.from({ length: 100 }, () => ({ text: 'hello ' })),
    { done: true, conversation_id: 'chat-1', reply: 'Final reply', model: 'haiku' },
  ]);
  await h.sandbox.send();
  assert.deepEqual(h.requests, ['/api/chat']);
  assert.equal(h.sandbox.busy, false);
  assert.equal(h.sandbox.rows.length, 2);
  assert.equal(h.sandbox.conversations[0].title, 'Remember Cedar');
  assert.equal(h.sandbox.chatId, 'chat-1');
  assert.equal(h.timers.size, 0);
  assert.equal(h.writes(), 1);
  assert.equal(h.streamed(), 'Final reply');
  assert.equal(h.html(), 'Final reply');
});

test('stream errors restore the draft and cancel pending paints', async () => {
  const h = harness([{ text: 'partial' }, { error: 'Save failed' }]);
  await h.sandbox.send();
  assert.equal(h.sandbox.composer.value, 'Remember Cedar');
  assert.equal(h.sandbox.busy, false);
  assert.equal(h.sandbox.rows.length, 0);
  assert.equal(h.timers.size, 0);
});

test('account initialization uses one authenticated history request', async () => {
  const requests = [];
  const scope = { epoch: 1, ready: false, renderSidebar() {}, async api(path) { requests.push(path); return { conversations: [] }; } };
  vm.createContext(scope);
  vm.runInContext(source.slice(source.indexOf('async function account('), source.indexOf('function clearFiles')), scope);
  await scope.account();
  assert.deepEqual(requests, ['/api/conversations']);
  assert.equal(scope.ready, true);
});

test('web search clearly reports its current state to sighted and assistive users', () => {
  const classes = new Set();
  const attrs = {};
  const label = { textContent: '' };
  const button = {
    classList: { toggle(name, enabled) { if (enabled) classes.add(name); else classes.delete(name); } },
    setAttribute(name, value) { attrs[name] = value; },
    querySelector() { return label; },
  };
  const scope = { web: false, $(selector) { assert.equal(selector, '#web'); return button; } };
  vm.createContext(scope);
  const start = source.indexOf('function syncWebButton()');
  const end = source.indexOf('async function deleteConversation(', start);
  vm.runInContext(source.slice(start, end), scope);
  scope.syncWebButton();
  assert.equal(label.textContent, 'Web: Off');
  assert.equal(attrs['aria-pressed'], 'false');
  assert.equal(attrs['aria-label'], 'Web search off');
  scope.web = true;
  scope.syncWebButton();
  assert.equal(label.textContent, 'Web: On');
  assert.equal(attrs['aria-pressed'], 'true');
  assert.equal(attrs['aria-label'], 'Web search on');
  assert.equal(classes.has('on'), true);
});
