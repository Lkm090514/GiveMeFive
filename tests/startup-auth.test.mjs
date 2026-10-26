import test from 'node:test';
import assert from 'node:assert/strict';
import {request,ensureIdentity} from '../dist/assessment/v4/api.mjs';
import {startupFailure} from '../dist/assessment/v4/startup-errors.mjs';
test('identity initialization shares one request and never manufactures a login',async()=>{
 const prior=globalThis.fetch;let calls=0,release;
 globalThis.fetch=()=>{calls++;return new Promise(resolve=>release=()=>resolve(new Response(JSON.stringify({owner_id:'student',role:'student'}))));};
 try{const first=ensureIdentity(true),second=ensureIdentity();assert.equal(first,second);assert.equal(calls,1);release();assert.equal((await first).owner_id,'student');}finally{globalThis.fetch=prior;}
});
test('startup diagnostics distinguish no login, expired identity, static server, network and internal errors',async()=>{
 const prior=globalThis.fetch;
 try{
  for(const [response,kind,title] of [
   [new Response(JSON.stringify({detail:{code:'auth_required',message:'need login'}}),{status:401}),'auth-required','尚未登录'],
   [new Response(JSON.stringify({detail:{code:'auth_expired',message:'expired'}}),{status:401}),'auth-expired','登录状态已失效'],
   [new Response('<html>static</html>',{status:404}),'backend-missing','未连接完整题库服务'],
   [new Response('Internal Server Error',{status:500}),'server','题库服务内部错误'],
   [new Response(JSON.stringify({detail:'forbidden'}),{status:403}),'api','题库请求未完成']
  ]){globalThis.fetch=async()=>response;await assert.rejects(request('/me'),error=>{assert.equal(error.kind,kind);assert.equal(startupFailure(error).title,title);return true;});}
  globalThis.fetch=async()=>{throw Error('disconnected');};await assert.rejects(request('/me'),error=>startupFailure(error).title==='本地服务未运行或连接中断');
  globalThis.fetch=async()=>new Response('[]');assert.deepEqual(await request('/questions'),[],'empty bank is a successful response');
 }finally{globalThis.fetch=prior;}
});

import vm from 'node:vm';
import fs from 'node:fs';
test('replacing a failed launch link in the same tab verifies the new fragment',async()=>{
 const events={},bodies=[],destinations=[],status={textContent:''};
 const context={location:{hash:'#launch=invalid',replace:url=>destinations.push(url)},history:{replaceState(){context.location.hash='';}},document:{getElementById:()=>status},sessionStorage:{setItem(){}},addEventListener:(name,fn)=>events[name]=fn,fetch:async(path,options)=>{
  if(path.endsWith('/me'))return new Response('{}');const data=JSON.parse(options.body);bodies.push(data);return data.ticket==='valid'?new Response('{}'):new Response(JSON.stringify({detail:{message:'登录链接已失效'}}),{status:401});
 }};
 vm.runInNewContext(fs.readFileSync(new URL('../dist/local-login.js',import.meta.url),'utf8'),context);
 await new Promise(resolve=>setImmediate(resolve));assert.match(status.textContent,/失效/);assert.deepEqual(destinations,[]);
 context.location.hash='#launch=valid';events.hashchange();await new Promise(resolve=>setImmediate(resolve));
 assert.deepEqual(bodies,[{ticket:'invalid'},{ticket:'valid'}]);assert.deepEqual(destinations,['/']);assert.equal(context.location.hash,'');
});
