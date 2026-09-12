import {firebaseConfig, hasFirebaseConfig} from '../../lib/firebaseConfig';
// Freeze the public worker config alongside the client build to prevent drift.
export const dynamic = 'force-static';
export function GET() {
  if (!hasFirebaseConfig()) return new Response('/* Firebase web configuration is incomplete. */', {status:503});
  return new Response(`self.THERMAGUARD_FIREBASE_CONFIG = ${JSON.stringify(firebaseConfig)};`, {
    headers: {'Content-Type':'application/javascript; charset=utf-8','Cache-Control':'no-cache'},
  });
}
