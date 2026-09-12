import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

const source = readFileSync(new URL('../lib/api.ts', import.meta.url), 'utf8');
function client(fetch, env = {}) {
  const exports = {};
  vm.runInNewContext(ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, { exports, process: { env }, fetch, AbortController, DOMException, setTimeout, clearTimeout });
  return exports;
}

for (const env of [{}, {
  NEXT_PUBLIC_API_BASE_URL: 'http://127.0.0.1:8000/api/v1///',
  NEXT_PUBLIC_BACKEND_URL: 'http://127.0.0.1:8000///',
}]) {
  test(`health/login URLs and authorization, ${Object.keys(env).length ? 'configured' : 'fallback'}`, async () => {
    const calls = [];
    const api = client(async (url, init) => {
      calls.push({ url, init });
      return Response.json({ status: 'ok', demo_mode: false });
    }, env);
    await api.fetchHealth();
    await api.apiPost('/auth/login', { email: 'fixture@example.org', password: 'test-only' });
    await api.apiGet('/auth/me', 'test-only-token');
    assert.equal(calls[0].url, Object.keys(env).length ? 'http://127.0.0.1:8000/health' : '/health');
    assert.equal(calls[0].init.headers.Authorization, undefined);
    assert.equal(calls[1].url, Object.keys(env).length ? 'http://127.0.0.1:8000/api/v1/auth/login' : '/api/v1/auth/login');
    assert.equal(calls[1].init.method, 'POST');
    assert.equal(calls[1].init.headers['Content-Type'], 'application/json');
    assert.equal(calls[2].init.headers.Authorization, 'Bearer test-only-token');
  });
}

for (const status of [401, 403, 422, 500, 503]) {
  test(`HTTP ${status} remains an HTTP error, not backend unavailable`, async () => {
    const api = client(async () => Response.json({ detail: 'Request rejected' }, { status }));
    await assert.rejects(api.apiPost('/auth/login', {}), error =>
      error instanceof api.ApiError && error.status === status && error.message === 'Request rejected');
  });
}

test('401 without JSON has an authentication message', async () => {
  const api = client(async () => new Response('', { status: 401 }));
  await assert.rejects(api.apiPost('/auth/login', {}), error =>
    error.status === 401 && /Authentication/.test(error.message));
});

test('only a network rejection has status zero', async () => {
  const api = client(async () => { throw new TypeError('Failed to fetch'); });
  await assert.rejects(api.fetchHealth(), error => error.status === 0 && /Cannot reach/.test(error.message));
});

test('invalid health JSON is a response error, not a network error', async () => {
  const api = client(async () => new Response('<html>Wrong endpoint</html>', { status: 200 }));
  await assert.rejects(api.fetchHealth(), error => error.status === 200 && /not valid JSON/.test(error.message));
});

test('timeout stays distinct and does not issue another probe', async () => {
  let calls = 0;
  const api = client((url, { signal }) => {
    calls++;
    return new Promise((resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError'))));
  });
  await assert.rejects(api.fetchHealth(5), error => error.status === 504 && /timed out/.test(error.message));
  assert.equal(calls, 1);
});

test('timeout also covers reading the response body', async () => {
  const api = client(async (url, { signal }) => ({
    ok: true, status: 200,
    text: () => new Promise((resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))),
  }));
  await assert.rejects(api.fetchHealth(5), error => error.status === 504);
});

for (const base of ['/api/v1/', 'https://api.example.com/api/v1/']) {
  test(`health follows API base when no health override is set: ${base}`, async () => {
    const calls = [];
    const api = client(async url => { calls.push(url); return Response.json({ status: 'ok' }); }, {
      NEXT_PUBLIC_API_BASE_URL: base,
    });
    await api.fetchHealth();
    assert.equal(calls[0], base.replace(/\/api\/v1\/$/, '') + '/health');
  });
}

 test('successful authentication opens workspace despite failing dashboard endpoint', async () => {
  const calls=[];
  const api=client(async url=>{
    calls.push(url);
    if(url.endsWith('/auth/me'))return Response.json({id:1,email:'test@example.org',role:'admin'});
    if(url.endsWith('/events'))return Response.json({detail:'Events temporarily unavailable'},{status:503});
    if(url.endsWith('/alerts'))return Response.json([]);
    return Response.json({model_available:false});
  });
  let authenticated=false;
  const data=await api.loadWorkspace('test-token',user=>{
    authenticated=true;
    assert.equal(user.id,1);
    assert.equal(calls.length,1,'Authentication completes before dashboard requests');
  });
  assert.equal(authenticated,true);
  assert.equal(data.events,undefined);
  assert.equal(data.alerts.length,0);
  assert.equal(data.model.model_available,false);
  assert.equal(data.errors.length,1);
 });

 test('invalid session never opens workspace or loads dashboard data',async()=>{
  let calls=0;
  const api=client(async()=>{calls++;return Response.json({detail:'Authentication required'},{status:401})});
  await assert.rejects(api.loadWorkspace('expired',()=>assert.fail('Invalid session must not open workspace')),e=>e.status===401);
  assert.equal(calls,1);
 });
