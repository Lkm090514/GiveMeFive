import test from 'node:test';
import assert from 'node:assert/strict';
import {proxyAssessment} from '../deploy/sites/api-proxy.mjs';
const env={GMF_AS_BACKEND_URL:'https://api.example/',GMF_AS_GATEWAY_KEY:'server-only-test-key'};
const origin='https://gmf.example';
test('gateway returns JSON for unavailable service and requires platform identity',async()=>{
 const r=await proxyAssessment(new Request(origin+'/api/v4/me'),{});assert.equal(r.status,503);assert.equal((await r.json()).detail.code,'service_unavailable');
 assert.equal((await proxyAssessment(new Request(origin+'/api/v4/me'),env)).status,401);
 assert.equal(await proxyAssessment(new Request(origin+'/data/course.json'),env),null);
});
test('gateway forwards only assessment cookie and never forwards private Sites credentials',async()=>{
 const previous=globalThis.fetch;let observed;
 globalThis.fetch=async(url,options)=>{observed={url,options};return new Response('{"owner_id":"student-a"}',{headers:{'Content-Type':'application/json','Set-Cookie':'__Host-gmf_cloud_session=opaque; Path=/; HttpOnly; Secure; SameSite=Lax'}});};
 try{
  const request=new Request(origin+'/api/v4/me',{headers:{'oai-authenticated-user-id':'site-user','Cookie':'sites_cookie=private; __Host-gmf_cloud_session=opaque','Authorization':'Bearer do-not-forward','X-GMF-Gateway-Key':'client-forgery'}});
  const response=await proxyAssessment(request,env);assert.equal(response.status,200);
  assert.equal(observed.options.headers.get('Cookie'),'__Host-gmf_cloud_session=opaque');assert.equal(observed.options.headers.get('Authorization'),null);assert.equal(observed.options.headers.get('oai-authenticated-user-id'),null);assert.equal(observed.options.headers.get('X-GMF-Gateway-Key'),env.GMF_AS_GATEWAY_KEY);
  assert.match(response.headers.get('Set-Cookie'),/HttpOnly/);assert.equal(response.headers.get('Cache-Control'),'private, no-store');
 }finally{globalThis.fetch=previous;}
});
test('gateway denies cross-origin mutations and upstream redirects',async()=>{
 const headers={'oai-authenticated-user-id':'site-user','Origin':'https://evil.example','X-GMF-Request':'1'};
 assert.equal((await proxyAssessment(new Request(origin+'/api/v4/logout',{method:'POST',headers}),env)).status,403);
 const previous=globalThis.fetch;globalThis.fetch=async()=>new Response(null,{status:307,headers:{Location:'https://other.example/'}});
 try{assert.equal((await proxyAssessment(new Request(origin+'/api/v4/me',{headers}),env)).status,502);}finally{globalThis.fetch=previous;}
});
