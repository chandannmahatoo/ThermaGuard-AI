# Firebase browser push verification

The browser registration flow is explicit and runs only after saved notification preferences report `notifications_enabled: true`. The checkbox alone does not enable registration. Authentication reuses the active page session, with `getStoredToken()` as a fallback; its existing storage key is `thermaguard.token` in sessionStorage.

## Implementation

- `frontend/lib/firebaseConfig.ts` holds only explicitly named public Firebase web configuration.
- `frontend/lib/firebase.ts` initializes the default web app lazily in a supported browser. It does not initialize Firebase during server rendering.
- `frontend/app/firebase-messaging-config.js/route.ts` produces worker configuration from the same build environment as the client. Rebuild/restart after changing public environment values.
- `frontend/public/firebase-messaging-sw.js` imports that configuration, initializes Firebase, and handles data-only background messages. Firebase handles notification payloads automatically; the custom handler does not show them again. No payload logging or hardcoded project values remain.
- `frontend/lib/pushNotifications.ts` checks saved preferences/session before browser work, checks capability/configuration, requests permission from the button gesture, registers the root worker, waits for activation, requests an FCM token with the explicit worker registration and public VAPID key, then uses `apiPut('/auth/push-device', {token}, authToken)`. Success requires `registered: true`. Raw SDK/API exceptions are not displayed or logged.
- `frontend/components/NotificationSettings.tsx` uses that single registration helper, disables registration until saved preferences are enabled, and prevents preference saves while registration is running. Existing coordinate, radius and notification-save behavior is preserved.
- `frontend/app/page.tsx` passes its current authenticated session, supporting sessions when browser storage is unavailable.
- `frontend/next.config.ts` provides no-cache and root-scope headers for the worker.

The prior UI already used the right storage helper and endpoint. Problems found were the separately hardcoded worker configuration, missing capability/configuration checks and explicit worker-activation wait, and unsafe payload/error logging. An absent worker before a permitted button invocation is expected: registration is deliberately not automatic on page load. A specific failure in the user's Chrome session was not observed directly.

## Validation

- Existing frontend suite plus helper, worker and component-handler tests: **85 passed**.
- `npx tsc --noEmit` from `frontend`: **passed**.
- `npm run build` from `frontend`: **passed**.
- `/firebase-messaging-sw.js`: **200**, JavaScript MIME type, root scope header.
- `/firebase-messaging-config.js`: **200**, JavaScript MIME type, all five fields match the public environment configuration. Values were withheld from verification output.
- No backend file was modified by this push fix. Other pre-existing backend changes were left intact.
- Actual Chrome permission approval, FCM issuance and delivery were not performed by these automated checks.

## Exact Chrome steps

1. Open **http://127.0.0.1:3000/** in Chrome and sign in. Keep this same origin throughout: `localhost` and `127.0.0.1` have separate permissions, workers and sessions.
2. Open **Settings**. Enter valid home coordinates and radius as needed, enable notifications and click **Save Notification Preferences**. Wait for the saved confirmation. The browser-push button must remain disabled until this completes.
3. Open DevTools → **Network** and DevTools → **Application → Service Workers**. Do not run commands that print session or FCM tokens.
4. Click **Enable Browser Push**, then **Allow** in Chrome's notification prompt. If previously blocked, open the address-bar site controls → **Site settings → Notifications → Allow**, return and retry.
5. In Network, verify `/firebase-messaging-sw.js` and `/firebase-messaging-config.js` succeed with JavaScript responses. In Application → Service Workers, verify the script URL ends in `/firebase-messaging-sw.js`, the scope is `/`, and its status is **activated**. Inspect worker errors there if imported Firebase scripts are blocked by network policy or an extension.
6. Verify the UI reaches its browser-push success message. In Network, the **PUT `/api/v1/auth/push-device`** must succeed with **`{"registered":true}`**. Do not share the request payload, Authorization header, HAR, or token values.
7. For an authorized delivery test, leave the page in the background and use the existing backend's test flow. Successful registration alone does not prove delivery. Avoid sending an actual incident alert merely to test registration.
8. If preferences are rejected with 422, save enabled preferences again. For 401, sign in again. If FCM cannot issue a token, verify the web app and public VAPID key belong to the intended Firebase project and that Firebase requests are not blocked. After a configuration change, rebuild/restart the frontend and reload the page before retrying.

Reference: [Firebase web messaging setup](https://firebase.google.com/docs/cloud-messaging/web/get-started) and [background message behavior](https://firebase.google.com/docs/cloud-messaging/web/receive-messages).
