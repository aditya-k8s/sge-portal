/*
 * Service worker for the Shri Gouri Engineers portal.
 *
 * Caching policy, in short: static assets are cached, application data is
 * never cached.
 *
 *   Navigations (HTML)  network first, falling back to the offline page.
 *                       Responses are NOT stored. Every page in this app is
 *                       account-specific, so a cached dashboard could be
 *                       shown to the next person to open the app on a shared
 *                       phone, or after the project data has moved on.
 *   Static assets       cache first, revalidated in the background. Safe
 *                       because collectstatic writes content-hashed names.
 *   Everything else     straight to the network: uploaded media, the REST
 *                       API, notification counts, and every non-GET request.
 *
 * Bump CACHE_VERSION to retire old caches on the next visit.
 */

const CACHE_VERSION = 'sge-v1';
const STATIC_CACHE = CACHE_VERSION + '-static';

// Paths are derived from the registration scope so the worker behaves the
// same whether the app is served from / or from a sub-path such as /web/.
const SCOPE_URL = new URL(self.registration.scope);
const scopePath = (relative) => new URL(relative, SCOPE_URL).pathname;

const OFFLINE_URL = scopePath('offline/');
const STATIC_PREFIX = scopePath('static/');
const MEDIA_PREFIX = scopePath('media/');

// The offline page and the icons it uses must be available with no network.
const PRECACHE_URLS = [
  OFFLINE_URL,
  STATIC_PREFIX + 'icons/icon-192x192.png',
  STATIC_PREFIX + 'icons/favicon.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(STATIC_CACHE);
      // Individually, so one missing file cannot fail the whole install and
      // leave the app with no worker at all.
      await Promise.all(
        PRECACHE_URLS.map((url) =>
          cache.add(new Request(url, { cache: 'reload' })).catch(() => {})
        )
      );
      await self.skipWaiting();
    })()
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      const names = await caches.keys();
      await Promise.all(
        names
          .filter((name) => !name.startsWith(CACHE_VERSION))
          .map((name) => caches.delete(name))
      );
      await self.clients.claim();
    })()
  );
});

// Lets the page activate a waiting worker immediately after an update.
self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

async function networkFirstNavigation(request) {
  try {
    const response = await fetch(request);
    return response;
  } catch (error) {
    const cached = await caches.match(OFFLINE_URL);
    if (cached) {
      return cached;
    }
    return new Response(
      '<h1>You are offline</h1><p>Reconnect and try again.</p>',
      { status: 503, headers: { 'Content-Type': 'text/html; charset=utf-8' } }
    );
  }
}

async function cacheFirstStatic(request) {
  const cache = await caches.open(STATIC_CACHE);
  const cached = await cache.match(request);

  if (cached) {
    // Refresh in the background so a redeployed asset is picked up on the
    // visit after this one, without delaying the current render.
    fetch(request)
      .then((response) => {
        if (response && response.ok) {
          cache.put(request, response.clone());
        }
      })
      .catch(() => {});
    return cached;
  }

  try {
    const response = await fetch(request);
    if (response && response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    return new Response('', { status: 504, statusText: 'Offline' });
  }
}

self.addEventListener('fetch', (event) => {
  const request = event.request;

  // Never interfere with writes, or with anything cross-origin (fonts and
  // the Tailwind CDN handle their own caching).
  if (request.method !== 'GET') {
    return;
  }

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) {
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith(networkFirstNavigation(request));
    return;
  }

  if (url.pathname.startsWith(STATIC_PREFIX)) {
    event.respondWith(cacheFirstStatic(request));
    return;
  }

  // Uploaded media and API responses are left to the network so a client
  // never sees another project's file or a stale status.
  if (url.pathname.startsWith(MEDIA_PREFIX)) {
    return;
  }
});
