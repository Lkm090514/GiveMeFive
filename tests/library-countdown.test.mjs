import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {createHash} from 'node:crypto';
import {resource} from '../dist/practice-library.mjs';

test('private resource cache verifies bytes, resumes and isolates accounts',async()=>{
 const old={caches:globalThis.caches,fetch:globalThis.fetch,location:globalThis.location};
 const stores=new Map();let requests=0,offline=false;
 globalThis.location={origin:'http://localhost:4173'};
 globalThis.caches={open:async name=>{if(!stores.has(name))stores.set(name,new Map());const s=stores.get(name);return {match:async k=>s.get(k)?.clone(),put:async(k,v)=>s.set(k,v.clone())};}};
 globalThis.fetch=async()=>{requests++;if(offline)throw Error('disconnected');return new Response('image');};
 const book={document_id:'doc',version:'v1'},item={url:'/api/v4/assets/a',bytes:5,sha256:createHash('sha256').update('image').digest('hex')};
 try{
  await resource({namespace:'one'},book,item);assert.equal(requests,1);
  offline=true;assert.equal(await (await resource({namespace:'one'},book,item)).text(),'image');assert.equal(requests,1);
  await assert.rejects(resource({namespace:'two'},book,item));assert.equal(requests,2);
  const cache=await caches.open('givemefive-private-one-doc-v1');await cache.put('http://localhost:4173'+item.url,new Response('wrong'));
  await assert.rejects(resource({namespace:'one'},book,item));offline=false;
  assert.equal(await (await resource({namespace:'one'},book,item)).text(),'image');assert.equal(requests,4);
 }finally{Object.assign(globalThis,old);}
});

test('exam countdown uses calendar dates and rejects invalid dates',()=>{
 const w={},document={currentScript:{src:'http://localhost:4173/shared-shell.js'},addEventListener(){}};
 vm.runInNewContext(fs.readFileSync(new URL('../dist/shared-shell.js',import.meta.url),'utf8'),{window:w,document,URL,Date});
 const now=new Date(2026,9,25,23,59);
 assert.equal(w.GMFShared.examCountdown('2026-10-26',now),1);
 assert.equal(w.GMFShared.examCountdown('2026-10-25',now),0);
 assert.equal(w.GMFShared.examCountdown('2026-10-24',now),-1);
 assert.equal(w.GMFShared.examCountdown('2026-02-30',now),null);
 assert.equal(w.GMFShared.examCountdown('',now),null);
});
