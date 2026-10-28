// Server-only same-origin gateway. Never import this module into browser bundles.
export async function proxyAssessment(request,env){
 const url=new URL(request.url);
 if(!url.pathname.startsWith('/api/v4/'))return null;
 const fail=(status,code,message)=>Response.json({detail:{code,message}},{status,headers:{'Cache-Control':'private, no-store'}});
 if(!env.GMF_AS_BACKEND_URL||!env.GMF_AS_GATEWAY_KEY)return fail(503,'service_unavailable','模考服务暂时不可用');
 let backend;try{backend=new URL(env.GMF_AS_BACKEND_URL);if(backend.protocol!=='https:'||backend.username||backend.password||backend.search||backend.hash||backend.pathname!=='/')throw Error();}catch{return fail(503,'service_unavailable','模考服务暂时不可用');}
 if(!request.headers.get('oai-authenticated-user-id'))return fail(401,'auth_required','请登录后继续');
 if(!['GET','HEAD'].includes(request.method)&&(request.headers.get('Origin')!==url.origin||request.headers.get('X-GMF-Request')!=='1'))return fail(403,'bad_origin','请求来源无效');
 const target=new URL(url.pathname+url.search,backend),headers=new Headers();
 for(const key of ['Content-Type','Accept','Origin','X-GMF-Request'])if(request.headers.has(key))headers.set(key,request.headers.get(key));
 const cookie=request.headers.get('cookie')?.split(';').map(x=>x.trim()).find(x=>x.startsWith('__Host-gmf_cloud_session='));if(cookie)headers.set('Cookie',cookie);
 headers.set('X-GMF-Gateway-Key',env.GMF_AS_GATEWAY_KEY);
 const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),120000);
 try{
  const response=await fetch(target,{method:request.method,headers,body:['GET','HEAD'].includes(request.method)?undefined:request.body,redirect:'manual',signal:controller.signal});
  if(response.status>=300&&response.status<400)return fail(502,'bad_backend','模考服务暂时不可用');
  const out=new Headers({'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'});
  for(const key of ['Content-Type','Content-Disposition'])if(response.headers.has(key))out.set(key,response.headers.get(key));
  const cookies=response.headers.getSetCookie?.()||[response.headers.get('Set-Cookie')].filter(Boolean);
  for(const value of cookies)if(value.startsWith('__Host-gmf_cloud_session='))out.append('Set-Cookie',value);
  return new Response(response.body,{status:response.status,headers:out});
 }catch{return fail(503,'service_unavailable','模考服务暂时不可用，请稍后重试');}finally{clearTimeout(timer);}
}
