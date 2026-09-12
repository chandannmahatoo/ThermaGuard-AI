import {getToken} from 'firebase/messaging';
import {getFirebaseMessaging} from './firebase';
import {hasFirebaseConfig} from './firebaseConfig';
import {apiPut, ApiError} from './api';

export function waitForActiveWorker(registration: ServiceWorkerRegistration, timeoutMs = 20000): Promise<void> {
  if (registration.active?.state === 'activated') return Promise.resolve();
  const worker = registration.installing || registration.waiting || registration.active;
  if (!worker) return Promise.reject(new Error('The notification service worker did not start.'));
  return new Promise((resolve,reject)=>{
    const cleanup=()=>{clearTimeout(timer);worker.removeEventListener('statechange',changed);};
    const changed=()=>{
      if(worker.state==='activated'){cleanup();resolve();}
      else if(worker.state==='redundant'){cleanup();reject(new Error('The notification service worker could not activate.'));}
    };
    const timer=setTimeout(()=>{cleanup();reject(new Error('Notification service worker activation timed out. Retry Enable Browser Push.'));},timeoutMs);
    worker.addEventListener('statechange',changed);changed();
  });
}

export async function getPushToken(): Promise<string> {
  if (typeof window==='undefined' || !window.isSecureContext) throw new Error('Browser push requires HTTPS or localhost.');
  if (!('Notification' in window) || !('serviceWorker' in navigator) || !('PushManager' in window)) throw new Error('This browser does not support browser push. Use a supported Chrome browser.');
  if (!hasFirebaseConfig() || !process.env.NEXT_PUBLIC_FIREBASE_VAPID_KEY?.trim()) throw new Error('Firebase web configuration or the public VAPID key is missing. Restart the frontend after configuring it.');
  // Request permission directly from the button gesture, before other async work.
  const permission=Notification.permission==='default' ? await Notification.requestPermission() : Notification.permission;
  if(permission!=='granted') throw new Error('Notification permission was not granted. Allow notifications in this site’s Chrome settings, then retry.');
  let registration:ServiceWorkerRegistration;
  try {registration=await navigator.serviceWorker.register('/firebase-messaging-sw.js',{scope:'/',updateViaCache:'none'});}
  catch {throw new Error('Could not register /firebase-messaging-sw.js. Check its response and imported scripts in Chrome DevTools.');}
  await waitForActiveWorker(registration);
  try {
    const messaging=await getFirebaseMessaging();
    if(!messaging) throw new Error();
    const token=await getToken(messaging,{vapidKey:process.env.NEXT_PUBLIC_FIREBASE_VAPID_KEY,serviceWorkerRegistration:registration});
    if(!token) throw new Error();
    return token;
  } catch {throw new Error('Firebase could not issue a browser push token. Check the web app, public VAPID key and browser network access, then retry.');}
}

export async function registerBrowserPush(notificationsEnabled:boolean,authToken:string):Promise<void> {
  if(!notificationsEnabled) throw new Error('Enable notifications and save your notification preferences before registering this browser.');
  if(!authToken) throw new Error('Your session is unavailable. Sign in again and retry.');
  const token=await getPushToken();
  try {
    const response=await apiPut<{registered:boolean}>('/auth/push-device',{token},authToken);
    if(response.registered!==true) throw new Error();
  } catch(error) {
    if(error instanceof ApiError && error.status===401) throw new Error('Your session expired. Sign in again and retry.');
    if(error instanceof ApiError && error.status===422) throw new Error('The backend rejected registration. Save enabled notification preferences and retry.');
    throw new Error('The backend did not confirm browser push registration. Check connectivity and retry.');
  }
}
