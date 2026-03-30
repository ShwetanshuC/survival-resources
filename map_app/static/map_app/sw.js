// Service Worker — cache-first for app shell, network-only for API calls
// Cache version: bump this string to force cache refresh on deploy
var CACHE_NAME = 'survival-v5';

// App shell assets to cache on install
var SHELL_URLS = [
    '/',
    '/static/map_app/css/style.css',
    '/static/map_app/js/script.js',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css',
    'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
];

// Install: pre-cache the app shell
self.addEventListener('install', function(event) {
    event.waitUntil(
        caches.open(CACHE_NAME).then(function(cache) {
            // Use individual adds so one CDN failure doesn't break the whole install
            return Promise.allSettled(
                SHELL_URLS.map(function(url) {
                    return cache.add(url).catch(function(err) {
                        console.warn('[SW] Failed to cache:', url, err);
                    });
                })
            );
        }).then(function() {
            return self.skipWaiting();
        })
    );
});

// Activate: delete old caches
self.addEventListener('activate', function(event) {
    event.waitUntil(
        caches.keys().then(function(keys) {
            return Promise.all(
                keys.filter(function(key) { return key !== CACHE_NAME; })
                    .map(function(key) { return caches.delete(key); })
            );
        }).then(function() {
            return self.clients.claim();
        })
    );
});

// Fetch: network-only for API, cache-first for everything else
self.addEventListener('fetch', function(event) {
    var url = new URL(event.request.url);

    // API calls — always go to network, never cache dynamic Overpass results
    if (url.pathname.startsWith('/api/')) {
        event.respondWith(fetch(event.request));
        return;
    }

    // App shell — cache-first, fall back to network
    event.respondWith(
        caches.match(event.request).then(function(cached) {
            if (cached) return cached;
            return fetch(event.request).then(function(response) {
                // Cache successful GET responses for shell assets
                if (
                    response.ok &&
                    event.request.method === 'GET' &&
                    (url.origin === self.location.origin ||
                     url.hostname.includes('unpkg.com') ||
                     url.hostname.includes('cdnjs.cloudflare.com'))
                ) {
                    var toCache = response.clone();
                    caches.open(CACHE_NAME).then(function(cache) {
                        cache.put(event.request, toCache);
                    });
                }
                return response;
            });
        })
    );
});
