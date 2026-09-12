import {getApp, getApps, initializeApp} from 'firebase/app';
import {getMessaging, isSupported} from 'firebase/messaging';
import {firebaseConfig, hasFirebaseConfig} from './firebaseConfig';

export async function getFirebaseMessaging() {
  if (typeof window === 'undefined' || !await isSupported()) return null;
  if (!hasFirebaseConfig()) throw new Error('Firebase web configuration is incomplete.');
  const app = getApps().some(app => app.name === '[DEFAULT]') ? getApp() : initializeApp(firebaseConfig);
  return getMessaging(app);
}
