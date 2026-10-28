import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {webcrypto} from 'node:crypto';
const root=new URL('../dist/',import.meta.url),base='http://localhost:4175/';
const manifest=JSON.parse(fs.readFileSync(new URL('data/runtime-manifest.json',root),'utf8'));
function environment(){
 const stores=new Map(),calls=[],failed=new Set();let offline=false;
 const key=x=>typeof x==='string'?x:x.url;
 const caches={async open(name){if(!stores.has(name))stores.set(name,new Map());const values=stores.get(name);return {match:async k=>{const v=values.get(key(k));return v?new Response(v.body.slice(),{status:v.status}):undefined;},put:async(k,v)=>{const body=Buffer.from(await v.arrayBuffer());values.set(key(k),{body,status:v.status});},delete:async k=>values.delete(key(k))};},keys:async()=>[...stores.keys()],delete:async name=>stores.delete(name)};
 const fetch=async target=>{const url=key(target);calls.push(url);if(offline||failed.has(url))throw Error('offline');const path=new URL(url).pathname.slice(1);try{return new Response(fs.readFileSync(new URL(path,root)));}catch{return new Response('',{status:404});}};
 const window={},context={window,caches,fetch,URL,Response,crypto:webcrypto,AbortController,DOMException,Blob,setTimeout,document:{currentScript:{src:base+'content-runtime.js'}}};
 vm.runInNewContext(fs.readFileSync(new URL('content-runtime.js',root),'utf8'),context);
 return {runtime:window.ContentRuntime,caches,calls,failed,setOffline:x=>offline=x,context,window};
}
test('real Unit download pauses, resumes only missing resources, detects corruption and retries failures',async()=>{
 const e=environment(),r=e.runtime;await r.init();
 assert.equal(e.calls.length,2,'first online load does not preload textbook assets');
 await assert.rejects(r.download(done=>{if(done===5)r.pause();},'1'),{name:'AbortError'});
 const partial=await r.status('1');assert.ok(partial.verified>0&&partial.verified<partial.total);
 const before=e.calls.length;await r.download(null,'1');assert.equal(e.calls.length-before,partial.total-partial.verified);
 assert.equal((await r.status('1')).complete,true);
 const path=manifest.topics['1.1'].path,c=await e.caches.open(r.cacheName);
 await c.put(base+path,new Response('corrupt'));
 assert.equal((await r.status('1')).complete,false);
 e.failed.add(base+path);await assert.rejects(r.download(null,'1'),err=>err.failed.includes(path));
 e.failed.clear();const retry=e.calls.length;await r.download(null,'1');assert.equal(e.calls.length-retry,1);
 e.setOffline(true);await r.ensureTopic('1.1');assert.ok(e.window.PathlineTextbook.readings.length>0);
 const loaded=e.calls.length;await r.ensureTopic('1.1');assert.equal(e.calls.length,loaded,'no duplicate Topic requests');
});
test('whole real course is complete by inventory, offline SW serves deep links and images, deletion is course scoped',async()=>{
 const e=environment(),r=e.runtime;await r.init();await r.download();assert.equal((await r.status()).complete,true);
 const other=await e.caches.open('givemefive-course-other-course-v1');await other.put(base+'other',new Response('keep'));
 const events={},self={location:{origin:new URL(base).origin},registration:{scope:base},clients:{claim(){}},skipWaiting(){},addEventListener(type,fn){events[type]=fn;}};
 e.setOffline(true);vm.runInNewContext(fs.readFileSync(new URL('sw.js',root),'utf8'),{self,caches:e.caches,fetch:e.context.fetch,URL,Response});
 const get=async path=>{let response;events.fetch({request:new Request(base+path),respondWith(p){response=p;}});return response;};
 assert.ok((await get('?course_id=x')).ok);assert.ok((await get(manifest.topics['1.1'].assets[0])).ok);
 assert.equal((await get('api/v4/me')),undefined,'private APIs never enter offline textbook cache');
 await r.init();await r.ensureTopic('7.5');assert.ok(e.window.PathlineTextbook.readings.length);
 const index=await e.caches.open('givemefive-offline-index');await index.put(base+'__offline_manifest__',new Response(JSON.stringify({...manifest,resource_version:'interrupted-update'})));let fallback;events.fetch({request:{url:base,method:'GET',mode:'navigate'},respondWith(p){fallback=p;}});assert.ok((await fallback).ok);assert.equal((await (await index.match(base+'__offline_manifest__')).json()).resource_version,manifest.resource_version);
 await r.remove();assert.equal((await r.status()).complete,false);assert.equal(await (await other.match(base+'other')).text(),'keep');
 assert.ok(!fs.readFileSync(new URL('content-runtime.js',root),'utf8').includes('indexedDB'),'offline deletion never touches learning database');
});
test('version inventories match every shipped byte and reject mixing releases',async()=>{
 for(const [path,rule] of Object.entries(manifest.resources)){const bytes=fs.readFileSync(new URL(path,root));assert.equal(bytes.length,rule.bytes,path);const h=await webcrypto.subtle.digest('SHA-256',bytes);assert.equal(Buffer.from(h).toString('hex'),rule.sha256,path);}
 const e=environment();await e.runtime.init();await e.runtime.download(null,'1');const old=e.runtime.cacheName;
 const next={...manifest,resource_version:'test-next-version'};const saved=await e.caches.open('givemefive-offline-index');await saved.put(base+'__offline_manifest__',new Response(JSON.stringify(next)));
 e.setOffline(true);await assert.rejects(e.runtime.init(),/offline/);assert.notEqual(e.runtime.cacheName,old);assert.equal((await e.runtime.status('1')).verified,0);const count=e.calls.length;await e.runtime.download(null,'1');assert.equal(e.calls.length,count,'byte-identical resources from an older release are verified and reused without networking');
});


test('shared chrome boots from head before body exists; language aliases stay consistent',()=>{
 const listeners={},observed=[];const document={currentScript:{src:base+'shared-shell.js'},body:null,addEventListener(type,fn){listeners[type]=fn;}};
 const window={LearningStore:{}};
 vm.runInNewContext(fs.readFileSync(new URL('shared-shell.js',root),'utf8'),{window,document,URL,MutationObserver:class{observe(node){assert.ok(node);observed.push(node);}},queueMicrotask});
 assert.ok(window.GMFShared);document.body={};listeners.DOMContentLoaded();assert.equal(observed.length,1);
 vm.runInNewContext(fs.readFileSync(new URL('ui-text.js',root),'utf8'),{window});
 for(const [old,zh,en] of [['MF','心流','Mind Flow'],['AS','模考','Assessment'],['PL','学习路径','Pathline'],['Tasks · 任务','任务','Tasks'],['Blockers 问题','问题','Blockers'],['Records 记录','记录','Records']]){assert.equal(window.PathlineUI.t('zh',old),zh);assert.equal(window.PathlineUI.t('en',old),en);}
});

test('PDF export reconstructs the real original file and does not mark browser offline content complete',async()=>{
 const e=environment(),links=[];e.context.document.createElement=()=>({click(){links.push(this);}});e.context.setTimeout=()=>0;
 await e.runtime.init();await e.runtime.downloadPDF();assert.equal(links.length,1);assert.equal(links[0].download,'OpenStax-University-Physics-Volume-1.pdf');
 const pdf=JSON.parse(fs.readFileSync(new URL('source/pdf-parts.json',root),'utf8')),bytes=await (await fetch(links[0].href)).arrayBuffer();assert.equal(bytes.byteLength,pdf.bytes);
 assert.equal(Buffer.from(await webcrypto.subtle.digest('SHA-256',bytes)).toString('hex'),pdf.sha256);assert.equal((await e.runtime.status()).complete,false);URL.revokeObjectURL(links[0].href);
});
