import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import vm from 'node:vm';
import ts from 'typescript';
import React from 'react';
const require=createRequire(import.meta.url);
function compile(file,mocks={},globals={}) {
 const exports={};vm.runInNewContext(ts.transpileModule(readFileSync(new URL(file,import.meta.url),'utf8'),{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true}}).outputText,{exports,require:n=>mocks[n]??require(n),setTimeout,clearTimeout,...globals});return exports;
}
function helper(options={}) {
 const calls=[]; const worker={state:'activated'};
 const registration={active:worker};
 const notification={permission:options.permission||'granted',requestPermission:async()=>{calls.push('permission');return options.grant||'granted'}};
 const browser={isSecureContext:options.secure??true,Notification:notification,PushManager:{}};
 class ApiError extends Error {constructor(status){super('sensitive-provider-value');this.status=status}}
 const mod=compile('../lib/pushNotifications.ts',{
  'firebase/messaging':{getToken:async(_,args)=>{calls.push(['token',args]);if(options.tokenError)throw Error('sensitive-token');return options.empty?'':'private-fcm-token'}},
  './firebase':{getFirebaseMessaging:async()=>({})},
  './firebaseConfig':{hasFirebaseConfig:()=>options.config??true},
  './api':{ApiError,apiPut:async(...args)=>{calls.push(['put',...args]);if(options.httpError)throw new ApiError(options.httpError);return {registered:options.registered??true}}},
 },{window:browser,Notification:notification,navigator:{serviceWorker:{register:async(...args)=>{calls.push(['worker',...args]);if(options.workerError)throw Error('unsafe-message');return registration}}},process:{env:{NEXT_PUBLIC_FIREBASE_VAPID_KEY:options.vapid??'public-vapid-test'}}});
 return {...mod,calls,registration};
}
test('push helper requires saved preferences before any browser or API request',async()=>{const h=helper();await assert.rejects(h.registerBrowserPush(false,'session'),/save your notification preferences/);assert.equal(h.calls.length,0)});
test('push helper requires authentication before browser permission or token request',async()=>{const h=helper();await assert.rejects(h.registerBrowserPush(true,''),/session/);assert.equal(h.calls.length,0)});
test('permission then root service worker then FCM then authenticated device PUT',async()=>{const h=helper({permission:'default'});await h.registerBrowserPush(true,'session');assert.equal(h.calls[0],'permission');assert.equal(h.calls[1][0],'worker');assert.equal(h.calls[1][1],'/firebase-messaging-sw.js');assert.equal(h.calls[1][2].scope,'/');assert.equal(h.calls[2][1].serviceWorkerRegistration,h.registration);assert.equal(h.calls[3][1],'/auth/push-device');assert.equal(h.calls[3][2].token,'private-fcm-token');assert.equal(h.calls[3][3],'session')});
test('denied permission makes no service-worker or backend request',async()=>{const h=helper({permission:'denied'});await assert.rejects(h.getPushToken(),/permission/);assert.equal(h.calls.length,0)});
test('missing configuration fails before browser permission',async()=>{const h=helper({permission:'default',config:false});await assert.rejects(h.getPushToken(),/configuration/);assert.equal(h.calls.length,0)});
test('missing VAPID key fails before registration',async()=>{const h=helper({vapid:''});await assert.rejects(h.getPushToken(),/VAPID/);assert.equal(h.calls.length,0)});
test('insecure origin is rejected',async()=>{const h=helper({secure:false});await assert.rejects(h.getPushToken(),/HTTPS/)});
test('registration failure is actionable without raw SDK errors',async()=>{const h=helper({workerError:true});await assert.rejects(h.getPushToken(),e=>/firebase-messaging-sw/.test(e.message)&&!e.message.includes('unsafe-message'))});
test('FCM failure never sends token or displays SDK exception',async()=>{const h=helper({tokenError:true});await assert.rejects(h.registerBrowserPush(true,'session'),e=>/could not issue/.test(e.message)&&!e.message.includes('sensitive-token'));assert.ok(!h.calls.some(c=>c[0]==='put'))});
test('empty FCM token cannot be registered',async()=>{const h=helper({empty:true});await assert.rejects(h.registerBrowserPush(true,'session'),/could not issue/);assert.ok(!h.calls.some(c=>c[0]==='put'))});
for(const status of [401,422,500])test(`backend ${status} cannot produce success`,async()=>{const h=helper({httpError:status});await assert.rejects(h.registerBrowserPush(true,'session'),e=>!e.message.includes('sensitive-provider-value'))});
test('backend must explicitly confirm registration',async()=>{const h=helper({registered:false});await assert.rejects(h.registerBrowserPush(true,'session'),/did not confirm/)});
test('worker activation is awaited and times out rather than hanging',async()=>{const h=helper();const installing=new EventTarget();installing.state='installing';const promise=h.waitForActiveWorker({installing},100);installing.state='activated';installing.dispatchEvent(new Event('statechange'));await promise;installing.state='installing';await assert.rejects(h.waitForActiveWorker({installing},5),/timed out/)});
test('background notification payload is not displayed twice; data payload is displayed once',async()=>{
 let callback;let count=0;const source=readFileSync(new URL('../public/firebase-messaging-sw.js',import.meta.url),'utf8');
 vm.runInNewContext(source,{importScripts(){},firebase:{initializeApp(){},messaging:()=>({onBackgroundMessage:fn=>callback=fn})},self:{THERMAGUARD_FIREBASE_CONFIG:{},location:{origin:'http://localhost:3000'},registration:{showNotification:async()=>{count++}}}});
 await callback({notification:{title:'Notice'}});assert.equal(count,0);await callback({data:{title:'Notice',body:'Evidence'}});assert.equal(count,1);assert.doesNotMatch(source,/console\.log|apiKey:/);
});

// Exercise the actual component event handlers and state transitions, with the
// registration boundary mocked. No Firebase credentials or real subscriptions.
function ui(register=async()=>{},enabled=true) {
 const state=[];let index=0;
 const hooks={...React,useState:init=>{const i=index++;if(!(i in state))state[i]=typeof init==='function'?init():init;return [state[i],v=>{state[i]=typeof v==='function'?v(state[i]):v}]},useEffect(){}};
 const Component=compile('../components/NotificationSettings.tsx',{'react':hooks,'../lib/pushNotifications':{registerBrowserPush:register},'../lib/api':{getStoredToken:()=>assert.fail('Use current session prop')}}).default;
 const props={authToken:'session',notif:{notifications_enabled:enabled,latitude:null,longitude:null,alert_radius_km:10},notifBusy:false,onSaveNotif(){},isAdmin:false,organizations:[],assignments:[]};
 function render(){index=0;return Component(props)}
 function nodes(node){return node&&typeof node==='object'?[node,...[node.props?.children].flat(Infinity).flatMap(nodes)]:[]}
 function text(node){return typeof node==='string'?node:node&&typeof node==='object'?[node.props?.children].flat(Infinity).map(text).join(''):''}
 return {render,props,find:(tree,name)=>nodes(tree).find(n=>n.type==='button'&&text(n).includes(name)),text};
}
test('UI prevents registration when saved preferences are disabled, even if local toggle changes',async()=>{let calls=0;const u=ui(async()=>{calls++},false);const button=u.find(u.render(),'Enable Browser Push');assert.equal(button.props.disabled,true);await button.props.onClick();assert.equal(calls,0);assert.match(u.text(u.render()),/save your notification preferences/)});
test('UI renders loading and confirmed success and sends current session',async()=>{let done;const u=ui((enabled,token)=>{assert.equal(enabled,true);assert.equal(token,'session');return new Promise(resolve=>done=resolve)});const pending=u.find(u.render(),'Enable Browser Push').props.onClick();assert.match(u.text(u.render()),/Enabling Push/);done();await pending;assert.match(u.text(u.render()),/Browser push notifications are enabled/)});
test('UI failure is visible and allows retry',async()=>{const u=ui(async()=>{throw Error('Registration could not complete')});await u.find(u.render(),'Enable Browser Push').props.onClick();assert.match(u.text(u.render()),/Could not enable browser push notifications/);assert.equal(u.find(u.render(),'Enable Browser Push').props.disabled,false)});
test('UI cannot race preference saving',async()=>{let calls=0;const u=ui(async()=>{calls++});u.props.notifBusy=true;await u.find(u.render(),'Enable Browser Push').props.onClick();assert.equal(calls,0)});
