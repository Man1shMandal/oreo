const $ = selector => document.querySelector(selector);
const defaults = { instructions: '', reply_style: 'brief', context: 'efficient', temperature: 0.7, reuse_files: true, web: true, enter: true, model: '' };
export let preferences = { ...defaults };
let owner = null, defaultModel = '';
const key = () => 'oreo-settings-v2:' + owner;
const previousKey = () => 'oreo-settings-v1:' + owner;
export function loadPreferences(user, model) {
  owner = user; defaultModel = model; preferences = { ...defaults, model };
  if (user) {
    try {
      let stored = localStorage.getItem(key());
      if (stored === null) {
        stored = localStorage.getItem(previousKey());
        const migrated = JSON.parse(stored || '{}');
        for (const name of Object.keys(defaults)) if (typeof migrated[name] === typeof defaults[name]) preferences[name] = migrated[name];
        if (stored !== null) preferences.web = true;
        localStorage.setItem(key(), JSON.stringify(preferences));
      } else {
        stored = JSON.parse(stored);
        for (const name of Object.keys(defaults)) if (typeof stored[name] === typeof defaults[name]) preferences[name] = stored[name];
      }
    } catch {}
  }
  return preferences;
}
function fill(value) {
  $('#s-instructions').value = value.instructions; $('#s-model').value = value.model;
  $('#s-style').value = value.reply_style; $('#s-context').value = value.context;
  $('#s-temperature').value = value.temperature; $('#s-temperature-value').value = Number(value.temperature).toFixed(1);
  $('#s-files').checked = value.reuse_files; $('#s-web').checked = value.web; $('#s-enter').checked = value.enter;
}
export function installSettings(onSave) {
  $('#open-settings').onclick = () => { fill(preferences); $('#settings').showModal(); };
  $('#close-settings').onclick = () => $('#settings').close();
  $('#settings').addEventListener('click', event => { if (event.target === $('#settings')) { const rect = event.target.getBoundingClientRect(); if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) event.target.close(); } });
  $('#s-temperature').oninput = () => $('#s-temperature-value').value = Number($('#s-temperature').value).toFixed(1);
  $('#s-efficient').onclick = () => { $('#s-style').value = 'brief'; $('#s-context').value = 'efficient'; $('#s-temperature').value = '0.4'; $('#s-temperature-value').value = '0.4'; $('#s-web').checked = false; };
  $('#s-reset').onclick = () => fill({ ...defaults, model: defaultModel });
  $('#settings-form').onsubmit = event => {
    event.preventDefault();
    if (!owner) return;
    preferences = { instructions: $('#s-instructions').value.trim(), model: $('#s-model').value, reply_style: $('#s-style').value, context: $('#s-context').value, temperature: Number($('#s-temperature').value), reuse_files: $('#s-files').checked, web: $('#s-web').checked, enter: $('#s-enter').checked };
    let saved = true; try { localStorage.setItem(key(), JSON.stringify(preferences)); } catch { saved = false; }
    onSave(preferences, saved); $('#settings').close();
  };
}
