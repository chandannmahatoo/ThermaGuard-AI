/* Public web config is generated from the same build environment as the client. */
importScripts('/firebase-messaging-config.js');
importScripts('https://www.gstatic.com/firebasejs/10.13.2/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.13.2/firebase-messaging-compat.js');
firebase.initializeApp(self.THERMAGUARD_FIREBASE_CONFIG);
const messaging = firebase.messaging();
messaging.onBackgroundMessage(payload => {
  // Firebase already displays notification payloads. Only data messages need this.
  if (payload.notification) return;
  if (!payload.data?.title && !payload.data?.body) return;
  return self.registration.showNotification(payload.data.title || 'ThermaGuard Alert', {
    body: payload.data.body || '',
    tag: payload.data.event_id || undefined,
    data: {url: self.location.origin},
  });
});

// Network-only navigation with a safe offline shell. Never cache protected data.
self.addEventListener('fetch', event => {
  if (event.request.mode !== 'navigate' || new URL(event.request.url).origin !== self.location.origin) return;
  event.respondWith(fetch(event.request).catch(() => new Response(
    '<!doctype html><html lang="en"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ThermaGuard offline</title><body><main><h1>ThermaGuard is offline</h1><p>Reconnect to load your authorized monitoring workspace. No incident data is stored for offline access.</p><a href="/">Retry connection</a></main></body></html>',
    {status:503,headers:{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store'}}
  )));
});
