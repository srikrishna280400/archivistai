/**
 * Archivist AI - Service Worker
 * High-fidelity PWA with offline support, cache-first strategy
 * Optimized for Play Store / TWA deployment
 */

const CACHE_NAME = 'archivist-ai-v1';
const STATIC_ASSETS = [
  '/',
  '/manifest.webmanifest',
  '/service-worker.js',
  '/js/app.js',
  'https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap',
  'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css',
];

const API_CACHE_NAME = 'archivist-api-v1';
const API_CACHE_TTL = 30000; // 30 seconds

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME && key !== API_CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Never cache API requests — always hit network
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirstWithApiCache(request));
    return;
  }

  // Static assets: cache-first, then network
  event.respondWith(cacheFirst(request));
});

async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) {
    // Stale-while-revalidate: serve cached, update in background
    fetchAndCache(request).catch(() => {});
    return cached;
  }
  return fetchAndCache(request);
}

async function fetchAndCache(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    // Offline fallback for navigation
    if (request.mode === 'navigate') {
      const cached = await caches.match('/');
      if (cached) return cached;
    }
    return new Response('Offline', { status: 503 });
  }
}

async function networkFirstWithApiCache(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      // Cache successful API responses for 30s
      const cache = await caches.open(API_CACHE_NAME);
      const responseToCache = response.clone();
      // Add timestamp header for TTL check
      const headers = new Headers(responseToCache.headers);
      headers.set('sw-cached-at', Date.now().toString());
      const cachedResponse = new Response(await responseToCache.blob(), {
        status: responseToCache.status,
        statusText: responseToCache.statusText,
        headers,
      });
      cache.put(request, cachedResponse);
    }
    return response;
  } catch (error) {
    // Offline: try cached API response
    const cached = await caches.match(request);
    if (cached) {
      const cachedAt = cached.headers.get('sw-cached-at');
      if (cachedAt && Date.now() - parseInt(cachedAt) < API_CACHE_TTL) {
        return cached;
      }
    }
    // No cached response or expired — return error
    return new Response(JSON.stringify({ error: 'Offline', cached: false }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

// Background sync for share target (optional)
self.addEventListener('sync', (event) => {
  if (event.tag === 'share-sync') {
    event.waitUntil(syncSharedArticles());
  }
});

async function syncSharedArticles() {
  // Placeholder: when online, sync any queued share actions
  console.log('[SW] Background sync triggered');
}