// Keeps the app shell available so the installed app opens on a weak connection.
// Only public, signed-out files are cached. /api/ and every non-GET request go
// straight to the network, so chats and tokens never land in the cache.
const CACHE = 'oreo-shell-v10';
const SHELL = ['/', '/chat.js', '/markdown.js', '/preferences.js', '/voice.js', '/theme.css', '/oreo.svg', '/manifest.webmanifest', '/icon-192.png'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', event => {
  event.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(key => key !== CACHE).map(key => caches.delete(key))))
    .then(() => self.clients.claim()));
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  const shell = url.origin === location.origin && !url.pathname.startsWith('/api/');
  // The Supabase client module comes from esm.sh; keep a copy so the page can start offline.
  const library = url.hostname === 'esm.sh';
  if (!shell && !library) return;
  // Network first, so a new release shows up on the next open; the cache is only a fallback.
  event.respondWith(fetch(request).then(response => {
    if (response.ok) {
      const copy = response.clone();
      caches.open(CACHE).then(cache => cache.put(request, copy));
    }
    return response;
  }).catch(() => caches.match(request).then(hit => hit || (request.mode === 'navigate' ? caches.match('/') : Response.error()))));
});
