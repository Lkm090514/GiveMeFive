// Only explicitly downloaded course resources live here. Never intercept private API data.
self.addEventListener('install',event=>event.waitUntil(self.skipWaiting()));
self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));
self.addEventListener('fetch',event=>{
 const u=new URL(event.request.url),base=new URL('./',self.registration.scope);
 if(event.request.cache==='no-store'||event.request.method!=='GET'||u.origin!==base.origin||u.pathname.startsWith('/api/')||u.pathname.startsWith('/local-login'))return;
 event.respondWith((async()=>{
  const index=await caches.open('givemefive-offline-index'),saved=await index.match(new URL('__offline_manifest__',base).href);
  if(!saved)return fetch(event.request);
  const m=await saved.json(),cache=await caches.open('givemefive-course-'+m.course_id+'-'+m.resource_version);
  const normalized=new URL(u);normalized.search='';if(normalized.pathname===base.pathname)normalized.pathname+='index.html';
  const local=await cache.match(normalized.href);
  if(local&&/\/(?:data|source|assets\/pages)\//.test(u.pathname)&&!u.pathname.endsWith('runtime-manifest.json'))return local;
  // Never overwrite a verified version with an unverified newer network response.
  try{const response=await fetch(event.request);if(response.ok||!local)return response;return local;}catch(error){
   // An interrupted upgrade must not strand a previously complete offline Unit.
   if(event.request.mode==='navigate'){const ready=await index.match(new URL('__offline_ready__',base).href);if(ready){const prior=await ready.clone().json(),previous=await caches.open('givemefive-course-'+prior.course_id+'-'+prior.resource_version),html=await previous.match(new URL('index.html',base).href);if(html){await index.put(new URL('__offline_manifest__',base).href,ready);return html;}}}
   if(local)return local;if(u.pathname.endsWith('runtime-manifest.json'))return new Response(JSON.stringify(m),{headers:{'Content-Type':'application/json'}});throw error;}
 })());
});
