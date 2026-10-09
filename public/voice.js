// Voice chat with the browser's own speech engines: no API key, no extra server calls.
// Chrome, Edge and Safari (including iPhone) support recognition; Firefox does not,
// so the mic button stays hidden there.
const Recognition = globalThis.SpeechRecognition || globalThis.webkitSpeechRecognition;
export const voiceSupported = !!Recognition;

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

// Listens for one utterance. Calls onText with the words so far and onDone with the final text.
export function listen({ onText, onDone, onError }) {
  const recognition = new Recognition();
  recognition.lang = navigator.language || 'en-US';
  recognition.interimResults = true;
  recognition.continuous = false;
  let text = '', failed = false, cancelled = false;
  recognition.onresult = event => {
    if (cancelled || failed) return;
    text = [...event.results].map(result => result[0].transcript).join('').trim();
    onText(text);
  };
  recognition.onerror = event => {
    if (cancelled || failed) return;
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
  // Cancelling still fires onend; it must not send the half-finished sentence.
  recognition.onend = () => { if (!failed && !cancelled) onDone(text); };
  recognition.start();
  return () => { cancelled = true; try { recognition.abort(); } catch {} };
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
