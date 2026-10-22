import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../oreo/web.html', import.meta.url), 'utf8');
const models = { sonnet: 'sonnet-id', haiku: 'haiku-id' };
function fill(value, labels) {
  const sandbox = { state: { models, modelLabels: labels, settings: { model: 'sonnet-id' } }, esc: s => String(s).replaceAll('<', '&lt;') };
  vm.createContext(sandbox);
  vm.runInContext(source.slice(source.indexOf('function fillModels('), source.indexOf('function openSettings(')), sandbox);
  const select = {};
  sandbox.fillModels(select, value);
  return select;
}
test('model picker keeps IDs for requests while displaying readable labels', () => {
  const select = fill('haiku-id', { sonnet: 'Claude Sonnet · Balanced', haiku: 'Claude Haiku · Fast' });
  assert.equal(select.value, 'haiku-id');
  assert.match(select.innerHTML, /value="haiku-id">Claude Haiku · Fast/);
});
test('retired remembered models fall back to the configured default', () => {
  assert.equal(fill('retired-id').value, 'sonnet-id');
});
test('picker works with older servers and escapes labels', () => {
  assert.match(fill('sonnet-id').innerHTML, />sonnet<\/option>/);
  assert.match(fill('sonnet-id', { sonnet: '<unsafe>' }).innerHTML, /&lt;unsafe>/);
});

test('hosted picker recovers from a retired saved model instead of appearing blank', () => {
  const hosted = readFileSync(new URL('../public/chat.js', import.meta.url), 'utf8');
  let selected;
  const select = { get value() { return selected; }, set value(value) { selected = ['haiku-id', 'sonnet-id'].includes(value) ? value : ''; } };
  const sandbox = { $: () => select, defaultModel: 'haiku-id' };
  vm.createContext(sandbox);
  vm.runInContext(hosted.slice(hosted.indexOf('function selectModel('), hosted.indexOf('async function show(')), sandbox);
  sandbox.selectModel('retired-id');
  assert.equal(selected, 'haiku-id');
  sandbox.selectModel('sonnet-id');
  assert.equal(selected, 'sonnet-id');
});
