import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import vm from 'node:vm';
import ts from 'typescript';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
const require=createRequire(import.meta.url);
const source=readFileSync(new URL('../components/ContextPanel.tsx',import.meta.url),'utf8');
const exports={};
vm.runInNewContext(ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true,target:ts.ScriptTarget.ES2022}}).outputText,{exports,require:name=>name==='../lib/api'?{apiPost:()=>assert.fail('SSR must not request routes')}:require(name)});
const render=context=>renderToStaticMarkup(React.createElement(exports.default,{event:{id:'test',context},token:'test-token',onRoute:()=>{}}));
test('missing context renders unavailable without invented values',()=>{
 const html=render({});assert.match(html,/Not enriched yet/);assert.doesNotMatch(html,/Temperature \(°C\)/);assert.doesNotMatch(html,/test-token/);
});
test('failed provider payload is not displayed as evidence',()=>{
 const html=render({weather:{status:'failed',reason:'timeout',temperature_c:999}});assert.match(html,/timeout/);assert.doesNotMatch(html,/999/);
});
test('available modelled context displays units and provenance',()=>{
 const html=render({weather:{status:'available',provider:'open_meteo',fetched_at:'2026-09-11',temperature_c:0,observed_at:'2026-09-11T12:00:00Z'}});
 assert.match(html,/Temperature \(°C\)/);assert.match(html,/>0</);assert.match(html,/Modelled grid context/);assert.match(html,/open_meteo/);
});
test('stale context explicitly reports failed refresh',()=>{
 const html=render({location:{status:'available',provider:'nominatim',display_name:'Test town',fetched_at:'2026-09-01',refresh_status:'failed'}});
 assert.match(html,/Test town/);assert.match(html,/Refresh failed/);assert.match(html,/2026-09-01/);
});
