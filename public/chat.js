import { createClient } from 'https://esm.sh/@supabase/supabase-js@2';
import { markdown } from './markdown.js';
import { preferences, loadPreferences, installSettings } from './preferences.js';

const $ = s => document.querySelector(s);
const composer = $('#message'), timeline = $('#answer'), stage = $('#chat');
let defaultModel = '';
let supabase, user = null, epoch = 0, chatId = null, rows = [], conversations = [];
const previewUrls = new Set();
let pending = [], busy = false, loading = false, reading = false, ready = false, web = false;
const welcome = '<div class="welcome"><h1>What can I help you with?</h1><p>Ask a question or start with a file.</p></div>';
const notify = text => { $('#status').textContent = text; $('#auth-status').textContent = text; };
const controls = () => {
  const blocked = busy || loading || reading || !ready;
  const eye = $('#oreo-eye'), active = busy || loading || reading;
  eye.classList.toggle('working', active);
  eye.classList.toggle('attentive', !active && ready && Boolean(composer.value.trim()));
  $('#send').disabled = blocked || (!composer.value.trim() && !pending.length);
  composer.disabled = busy || loading || !ready;
  for (const id of ['attach', 'web', 'model', 'new-chat', 'open-settings']) $('#' + id).disabled = blocked;
  $('#sign-out').disabled = busy;
  for (const button of $('#history').querySelectorAll('button')) button.disabled = busy || loading;
};
const token = async () => {
  const { data, error } = await supabase.auth.getSession();
  if (error || !data.session || data.session.user.id !== user) throw new Error('Please sign in again.');
  return data.session.access_token;
};
const request = async (path, options = {}) => {
  const bearer = await token();
  return fetch(path, { ...options, headers: { 'Authorization': 'Bearer ' + bearer, 'Content-Type': 'application/json', ...options.headers } });
};
const api = async (path, options) => {
  const response = await request(path, options);
  const data = await response.json();
  if (!response.ok || data.error) throw new Error(data.error || 'Could not complete the request. Please retry.');
  return data;
};
function unpack(content) {
  if (content.startsWith('oreo-message-v1:')) {
    try { const value = JSON.parse(content.slice('oreo-message-v1:'.length)); if (typeof value.text === 'string') return value; } catch {}
  }
  const files = [];
  const text = content.replace(/(?:^|\n\n)<file path="([^"]*)">\n[\s\S]*?\n<\/file>/g, (_, name) => { files.push({ name }); return ''; });
  return { text, files };
}
function sourceLinks(parent, sources = []) {
  const list = document.createElement('div'); list.className = 'sources';
  for (const [i, source] of sources.entries()) {
    try {
      const url = new URL(source.url); if (!['http:', 'https:'].includes(url.protocol)) continue;
      const link = document.createElement('a'); link.href = url.href; link.target = '_blank'; link.rel = 'noopener noreferrer';
      link.textContent = `${i + 1} · ${url.hostname.replace(/^www\./, '')}`; link.title = source.title || url.href; list.append(link);
    } catch {}
  }
  if (list.children.length) parent.append(list);
}
function message(row) {
  const value = typeof row.content === 'string' ? unpack(row.content) : row.content;
  const el = document.createElement('article'); el.className = 'turn ' + (row.role === 'user' ? 'user' : 'assistant');
  if (row.role === 'user') {
    el.textContent = value.text || 'Please read the attached file.';
    for (const file of value.files || []) {
      const chip = document.createElement('div'); chip.className = 'attachment-chip'; chip.textContent = file.name; el.append(chip);
      if (file.preview) { const image = document.createElement('img'); image.src = file.preview; image.alt = file.name; el.append(image); }
    }
  } else {
    const body = document.createElement('div'); body.className = 'md'; body.innerHTML = markdown(value.text); el.append(body);
    sourceLinks(el, value.sources);
  }
  return el;
}
function render() {
  timeline.replaceChildren();
  if (!rows.length) timeline.innerHTML = welcome;
  else for (const row of rows) timeline.append(message(row));
  stage.scrollTop = stage.scrollHeight;
}
function renderSidebar() {
  $('#history').replaceChildren();
  for (const row of conversations) {
    const item = document.createElement('div'); item.className = 'history-row';
    const button = document.createElement('button'); button.className = 'chat-open'; button.textContent = row.title; button.title = row.title;
    item.classList.toggle('active', row.id === chatId); button.setAttribute('aria-current', row.id === chatId ? 'true' : 'false');
    button.onclick = () => select(row);
    const remove = document.createElement('button'); remove.className = 'chat-delete'; remove.type = 'button'; remove.textContent = '×';
    remove.title = 'Delete chat'; remove.setAttribute('aria-label', 'Delete chat: ' + row.title); remove.onclick = event => { event.stopPropagation(); void deleteConversation(row); };
    item.append(button, remove); $('#history').append(item);
  }
  $('#chat-title').textContent = conversations.find(row => row.id === chatId)?.title || 'New chat'; controls();
}
async function account(expected = epoch) {
  const historyData = await api('/api/conversations'); if (expected !== epoch) return;
  ready = true; conversations = historyData.conversations; renderSidebar();
}
function clearFiles() { for (const file of pending) if (file.preview) URL.revokeObjectURL(file.preview); pending = []; tray(); }
function resetDraft() { for (const url of previewUrls) URL.revokeObjectURL(url); previewUrls.clear(); clearFiles(); composer.value = ''; composer.style.height = 'auto'; web = preferences.web; $('#web').classList.toggle('on', web); $('#web').setAttribute('aria-pressed', String(web)); }
async function deleteConversation(row) {
  if (busy || loading || reading || !confirm('Delete this chat? This cannot be undone.')) return;
  const expected = epoch; loading = true; controls(); notify('Deleting chat…');
  try {
    await api('/api/conversations?id=' + encodeURIComponent(row.id), { method: 'DELETE' });
    if (expected !== epoch) return;
    conversations = conversations.filter(item => item.id !== row.id);
    if (chatId === row.id) {
      ++epoch; chatId = null; rows = []; resetDraft(); render();
    }
    renderSidebar(); notify('');
  } catch (error) { if (expected === epoch) notify(error.message); }
  finally { loading = false; controls(); }
}
async function select(row) {
  if (busy || loading || reading) return;
  const expected = ++epoch; loading = true; controls(); document.body.classList.remove('drawer'); notify('Loading chat…');
  try {
    const data = await api('/api/conversations?id=' + encodeURIComponent(row.id)); if (expected !== epoch) return;
    chatId = row.id; rows = data.messages; resetDraft(); render(); renderSidebar(); notify('');
  } catch (error) { if (expected === epoch) notify(error.message); }
  finally { if (expected === epoch) { loading = false; controls(); } }
}
function newChat() {
  if (busy || loading || reading) return;
  ++epoch; chatId = null; rows = []; resetDraft(); render(); renderSidebar(); notify(''); composer.focus(); document.body.classList.remove('drawer');
}
const read = file => new Promise((resolve, reject) => {
  const reader = new FileReader(); reader.onload = () => resolve(reader.result.split(',')[1]); reader.onerror = () => reject(new Error('Could not read ' + file.name)); reader.readAsDataURL(file);
});
async function resizePhoto(file) {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) return file;
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, 1568 / Math.max(bitmap.width, bitmap.height));
    const canvas = document.createElement('canvas'); canvas.width = Math.round(bitmap.width * scale); canvas.height = Math.round(bitmap.height * scale);
    const context = canvas.getContext('2d'); context.fillStyle = '#fff'; context.fillRect(0, 0, canvas.width, canvas.height); context.drawImage(bitmap, 0, 0, canvas.width, canvas.height); bitmap.close();
    const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.85));
    if (blob && blob.size < file.size) return new File([blob], file.name, { type: 'image/jpeg' });
  } catch {}
  return file;
}
async function addFiles(files) {
  if (!ready || busy || loading || reading) return;
  const expected = epoch; reading = true; controls();
  try {
    for (const original of files) {
      const file = await resizePhoto(original); if (expected !== epoch) return;
      if (pending.length >= 5) throw new Error('Attach up to 5 files at a time.');
      if (file.size + pending.reduce((n, f) => n + f.size, 0) > 2200000) throw new Error('Keep attachments under 2.2 MB in total.');
      const data = await read(file); if (expected !== epoch) return;
      const preview = file.type.startsWith('image/') ? URL.createObjectURL(file) : ''; if (preview) previewUrls.add(preview);
      pending.push({ name: file.name, type: file.type || 'application/octet-stream', data, size: file.size, preview });
    }
    notify('');
  } catch (error) { if (expected === epoch) notify(error.message); }
  finally { reading = false; tray(); controls(); }
}
function tray() {
  $('#tray').replaceChildren();
  pending.forEach((file, i) => {
    const item = document.createElement('div'); item.className = 'file';
    if (file.preview) { const image = document.createElement('img'); image.src = file.preview; image.alt = ''; item.append(image); }
    const name = document.createElement('span'); name.textContent = file.name;
    const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = '×'; remove.setAttribute('aria-label', 'Remove ' + file.name); remove.disabled = busy;
    remove.onclick = () => { if (file.preview) URL.revokeObjectURL(file.preview); pending.splice(i, 1); tray(); controls(); };
    item.append(name, remove); $('#tray').append(item);
  });
}
async function send() {
  if ($('#send').disabled) return;
  const expected = epoch, text = composer.value.trim(), files = [...pending];
  const outgoing = { role: 'user', content: { text, files } };
  busy = true; controls(); tray(); notify(files.length ? 'Reading files…' : web ? 'Searching the web…' : 'Thinking…');
  composer.value = ''; composer.style.height = 'auto';
  timeline.querySelector('.welcome')?.remove();
  const userEl = message(outgoing); timeline.append(userEl);
  const replyEl = message({ role: 'assistant', content: { text: '' } }); replyEl.classList.add('streaming'); timeline.append(replyEl);
  stage.scrollTop = stage.scrollHeight;
  const replyBody = replyEl.querySelector('.md');
  replyBody.classList.add('streaming-plain');
  const streamText = document.createTextNode('');
  replyBody.append(streamText);
  let reply = '', displayedLength = 0, done = null, receivedChat = chatId, paint = null;
  const paintReply = () => {
    paint = null;
    if (expected !== epoch) return;
    const nearBottom = stage.scrollHeight - stage.scrollTop - stage.clientHeight < 140;
    streamText.appendData(reply.slice(displayedLength));
    displayedLength = reply.length;
    if (nearBottom) stage.scrollTop = stage.scrollHeight;
  };
  try {
    const response = await request('/api/chat', { method: 'POST', body: JSON.stringify({ message: text, conversation_id: chatId, files: files.map(({ name, type, data }) => ({ name, type, data })), model: $('#model').value, web, stream: true, settings: preferences }) });
    if (!response.ok || !response.headers.get('content-type')?.includes('text/event-stream')) {
      const data = await response.json(); throw new Error(data.error || 'Could not start the reply.');
    }
    const reader = response.body.getReader(), decoder = new TextDecoder(); let buffer = '';
    const consume = event => {
      if (expected !== epoch) return;
      if (event.conversation_id) receivedChat = event.conversation_id;
      if (event.error) throw new Error(event.error);
      if (event.status) notify(event.status);
      if (event.text) {
        reply += event.text;
        if (paint === null) paint = setTimeout(paintReply, 40);
      }
      if (event.done) done = event;
    };
    while (true) {
      const part = await reader.read(); buffer += decoder.decode(part.value || new Uint8Array(), { stream: !part.done });
      let end; while ((end = buffer.indexOf('\n\n')) >= 0) {
        const frame = buffer.slice(0, end); buffer = buffer.slice(end + 2);
        for (const line of frame.split('\n')) if (line.startsWith('data: ')) consume(JSON.parse(line.slice(6)));
      }
      if (part.done) break;
    }
    if (expected !== epoch) return;
    if (!done) throw new Error('The connection ended before the reply was saved. Refresh this chat before retrying.');
    clearTimeout(paint); reply = done.reply; paintReply();
    replyBody.classList.remove('streaming-plain'); replyBody.innerHTML = markdown(reply);
    sourceLinks(replyEl, done.sources);
    if (done.model !== $('#model').value) { const note = document.createElement('div'); note.className = 'meta'; note.textContent = 'Used a vision model for this image.'; replyEl.append(note); }
    chatId = done.conversation_id; rows.push(outgoing, { role: 'assistant', content: { text: reply, sources: done.sources } });
    pending = []; tray(); composer.value = ''; composer.style.height = 'auto';
    // Preview URLs stay alive for this open chat; history uses saved file names.
    web = preferences.web; $('#web').classList.toggle('on', web); $('#web').setAttribute('aria-pressed', String(web));
    const saved = conversations.find(row => row.id === chatId) || { id: chatId, title: (text || files.map(file => file.name).join(', ') || 'New chat').slice(0, 80) };
    conversations = [{ ...saved, updated_at: new Date().toISOString() }, ...conversations.filter(row => row.id !== chatId)].slice(0, 100);
    renderSidebar();
    notify((done.warnings || []).join(' '));
  } catch (error) {
    if (expected === epoch) {
      userEl.remove(); replyEl.remove(); if (!rows.length) render();
      if (!composer.value) { composer.value = text; composer.dispatchEvent(new Event('input')); }
      chatId = receivedChat;
      try { await account(expected); } catch {}
      notify(error.message);
    }
  } finally { clearTimeout(paint); replyEl.classList.remove('streaming'); busy = false; tray(); controls(); if (ready && expected === epoch) composer.focus(); }
}
$('#send').onclick = send;
$('#composer').onsubmit = event => { event.preventDefault(); void send(); };
$('#new-chat').onclick = newChat;
$('#attach').onclick = () => $('#pick').click();
$('#pick').onchange = event => { void addFiles([...event.target.files]); event.target.value = ''; };
$('#web').setAttribute('aria-pressed', 'false');
$('#web').onclick = () => { web = !web; $('#web').classList.toggle('on', web); $('#web').setAttribute('aria-pressed', String(web)); };
composer.oninput = () => { composer.style.height = 'auto'; composer.style.height = Math.min(composer.scrollHeight, 220) + 'px'; controls(); };
composer.onkeydown = event => { if (preferences.enter && event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); void send(); } };
composer.onpaste = event => { if (event.clipboardData.files.length) { event.preventDefault(); void addFiles([...event.clipboardData.files]); } };
document.addEventListener('dragover', event => { if (ready && [...event.dataTransfer.types].includes('Files')) event.preventDefault(); });
document.addEventListener('drop', event => { if (ready && event.dataTransfer.files.length) { event.preventDefault(); void addFiles([...event.dataTransfer.files]); } });
document.addEventListener('click', async event => {
  const button = event.target.closest('.copy'); if (!button) return;
  try { await navigator.clipboard.writeText(button.parentElement.querySelector('code').textContent); button.textContent = 'Copied'; setTimeout(() => button.textContent = 'Copy', 1500); } catch { notify('Could not copy. Select the code to copy it.'); }
});
$('#mobile-menu').onclick = () => document.body.classList.toggle('drawer');
$('.mobile-backdrop').onclick = () => document.body.classList.remove('drawer');
document.addEventListener('keydown', event => { if (event.key === 'Escape') document.body.classList.remove('drawer'); });
$('#refresh').onclick = async () => { try { await account(); notify(''); } catch (error) { notify(error.message); } };
$('#google').onclick = async () => {
  notify('Opening Google…');
  const { error } = await supabase.auth.signInWithOAuth({ provider: 'google', options: { redirectTo: location.origin } }); if (error) notify(error.message);
};
$('#sign-out').onclick = async () => { const { error } = await supabase.auth.signOut(); if (error) notify(error.message); };
if ('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js').catch(() => {});
// Chrome, Edge and Android offer installs through this event. iOS never fires it, so there the
// button shows the Share > Add to Home Screen steps instead. iPads report themselves as Macs with touch.
let installPrompt = null;
const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
const installed = matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
if (ios && !installed) $('#install').classList.remove('hidden');
addEventListener('beforeinstallprompt', event => { event.preventDefault(); installPrompt = event; $('#install').classList.remove('hidden'); });
addEventListener('appinstalled', () => { installPrompt = null; $('#install').classList.add('hidden'); });
$('#install').onclick = async () => {
  if (!installPrompt) {
    if (ios) { document.body.classList.remove('drawer'); $('#ios-install').classList.remove('hidden'); }
    return;
  }
  installPrompt.prompt(); await installPrompt.userChoice; installPrompt = null; $('#install').classList.add('hidden');
};
$('#ios-install-close').onclick = () => $('#ios-install').classList.add('hidden');
async function show(session) {
  const next = session?.user.id || null;
  document.body.classList.toggle('signed-out', !next); $('#auth').classList.toggle('hidden', !!next); stage.classList.toggle('hidden', !next); $('.compose-wrap').classList.toggle('hidden', !next);
  $('#who').textContent = session?.user.email || '';
  if (next !== user) {
    ++epoch; user = next; ready = false; loading = false; chatId = null; rows = []; conversations = []; loadPreferences(next, defaultModel); $('#send-hint').textContent = preferences.enter ? 'Enter to send · Shift + Enter for a new line' : 'Click the arrow to send · Enter for a new line'; $('#model').value = preferences.model || defaultModel; $('#settings').close(); resetDraft(); render(); renderSidebar(); notify('');
    if (next) { notify('Loading your chats…'); try { await account(); notify(''); } catch (error) { notify(error.message); } }
  }
  controls();
}
controls();
try {
  const response = await fetch('/api/config'); if (!response.ok) throw new Error('Could not load Oreo. Please refresh.');
  const config = await response.json(); if (!config.supabaseUrl || !config.supabasePublishableKey) throw new Error('Sign-in is not configured.');
  const compactModelNames = { opus: 'Opus', sonnet5: 'Sonnet 5', sonnet: 'Sonnet', haiku: 'Haiku', gpt: 'GPT', gemini: 'Gemini' };
  for (const [label, id] of Object.entries(config.models)) $('#model').add(new Option(compactModelNames[label] || config.modelLabels?.[label] || label, id));
  defaultModel = config.defaultModel;
  $('#model').value = defaultModel;
  for (const [label, id] of Object.entries(config.models)) $('#s-model').add(new Option(config.modelLabels?.[label] || label, id));
  installSettings((value, saved) => {
    $('#model').value = value.model; web = value.web; $('#web').classList.toggle('on', web); $('#web').setAttribute('aria-pressed', String(web));
    $('#send-hint').textContent = value.enter ? 'Enter to send · Shift + Enter for a new line' : 'Click the arrow to send · Enter for a new line';
    notify(saved ? 'Settings saved.' : 'Settings apply to this session. This browser could not save them.');
  });
  supabase = createClient(config.supabaseUrl, config.supabasePublishableKey);
  const { data, error } = await supabase.auth.getSession(); if (error) throw error;
  await show(data.session); if (!data.session) notify('');
  supabase.auth.onAuthStateChange((_event, session) => { setTimeout(() => { void show(session); }, 0); });
  const callback = new URLSearchParams(location.hash.slice(1)).get('error_description') || new URLSearchParams(location.search).get('error_description');
  if (callback) { notify(callback); history.replaceState(null, '', location.pathname); }
} catch (error) {
  notify(navigator.onLine ? error.message : 'You are offline. Oreo needs a connection to chat.'); $('#google').disabled = true;
  if (!navigator.onLine) addEventListener('online', () => location.reload(), { once: true });
}
