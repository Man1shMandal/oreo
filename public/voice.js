// Voice chat with the browser's own speech engines: no API key, no extra server calls.
// Chrome, Edge and Safari (including iPhone) support recognition; Firefox does not,
// so the mic button is disabled there.
const Recognition = globalThis.SpeechRecognition || globalThis.webkitSpeechRecognition;
export const voiceSupported = !!Recognition;
export const speechSupported = !!globalThis.speechSynthesis && typeof globalThis.SpeechSynthesisUtterance === 'function';

// Short spoken phrases that run an action instead of being sent to Oreo.
const COMMANDS = [
  ['new-chat', /^(start (a )?)?new chat$/],
  ['web-on', /^((turn|switch) on (the )?web( search)?|((turn|switch) )?(the )?web( search)? on)$/],
  ['web-off', /^((turn|switch) off (the )?web( search)?|((turn|switch) )?(the )?web( search)? off)$/],
  ['settings', /^open settings$/],
  ['repeat', /^(read (that|it) again|repeat( that)?)$/],
  ['stop', /^(stop|stop talking|be quiet|cancel)$/],
];

export function command(text) {
  const said = text.toLowerCase().replace(/[^\p{L}\p{N} ]/gu, '').replace(/\s+/g, ' ').trim().replace(/^(oreo|hey oreo|please) /, '');
  return COMMANDS.find(([, pattern]) => pattern.test(said))?.[0] || null;
}

const join = (...parts) => parts.map(part => part.trim()).filter(Boolean).join(' ');

// Keeps listening through pauses until the returned stop() is called, so a sentence
// is never cut off. Browsers end a recognition session after a short silence, so a
// new one starts at once and its words are added on. onText always receives
// everything heard so far. After a few silent sessions in a row, onIdle is called
// so the mic is not left on by accident.
export function listen({ onText, onIdle, onError, silentRestarts = 3 }) {
  let heard = '', failed = false, stopped = false, silent = 0, recognition;
  const begin = () => {
    recognition = new Recognition();
    recognition.lang = navigator.language || 'en-US';
    recognition.interimResults = true;
    recognition.continuous = true;
    let session = '', spoke = false;
    recognition.onresult = event => {
      if (stopped || failed) return;
      let final = '', interim = '';
      for (const result of event.results) {
        if (result.isFinal) final += result[0].transcript; else interim += result[0].transcript;
      }
      session = final; spoke = true;
      onText(join(heard, final, interim));
    };
    recognition.onerror = onerror;
    recognition.onend = () => {
      heard = join(heard, session);
      if (stopped || failed) return;
      silent = spoke ? 0 : silent + 1;
      if (silent >= silentRestarts) { stopped = true; onIdle(heard); return; }
      try { begin(); } catch { failed = true; onError('Microphone is unavailable. Check browser permissions and try again.'); }
    };
    recognition.start();
  };
  const onerror = event => {
    if (stopped || failed) return;
    if (event.error === 'aborted') return;
    if (event.error === 'no-speech') return;
    failed = true;
    const messages = {
      'not-allowed': 'Allow microphone access for Oreo in your browser settings, then try again.',
      'service-not-allowed': 'Allow microphone access for Oreo in your browser settings, then try again.',
      'audio-capture': 'No microphone is available. Connect one and try again.',
      network: 'Voice recognition could not connect. Check your connection and try again.',
      'language-not-supported': 'Voice input does not support your browser language.',
    };
    onError(messages[event.error] || 'Could not hear that. Check your microphone and try again.');
  };
  begin();
  // Stopping drops anything still arriving, so a late word never refills a sent box.
  return () => { stopped = true; try { recognition.abort(); } catch {} };
}

// Markdown reads badly aloud, so speak the plain words and skip code blocks.
function plain(markdown) {
  return markdown.replace(/```[\s\S]*?```/g, ' (code shown on screen) ').replace(/`([^`]*)`/g, '$1')
    .replace(/!?\[([^\]]*)\]\([^)]*\)/g, '$1').replace(/^#+\s*/gm, '').replace(/[*_>|~]/g, '')
    .replace(/^\s*[-+]\s+/gm, '').replace(/\s+/g, ' ').trim();
}

let speechGeneration = 0;
export function speak(markdown, onEnd = () => {}) {
  const generation = ++speechGeneration;
  if (!globalThis.speechSynthesis || typeof globalThis.SpeechSynthesisUtterance !== 'function') return onEnd();
  try {
    speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(plain(markdown));
    utterance.lang = navigator.language || 'en-US';
    utterance.onend = utterance.onerror = () => { if (generation === speechGeneration) onEnd(); };
    speechSynthesis.speak(utterance);
  } catch { onEnd(); }
}

export function stopSpeaking() { speechGeneration++; try { globalThis.speechSynthesis?.cancel(); } catch {} }
export const speaking = () => !!globalThis.speechSynthesis?.speaking;
