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
