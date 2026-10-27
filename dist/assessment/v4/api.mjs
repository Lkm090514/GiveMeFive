let identityFlight=null;
export class APIError extends Error{constructor(message,{status=0,kind='api',path=''}={}){super(message);Object.assign(this,{status,kind,path});}}
export async function request(path,options={}){
 const headers={'X-GMF-Request':'1',...options.headers};
 if(options.body&&!(options.body instanceof FormData)){headers['Content-Type']='application/json';options={...options,body:JSON.stringify(options.body)};}
 const controller=new AbortController(),abort=()=>controller.abort(),timer=setTimeout(()=>controller.abort(),20000);
 options.signal?.addEventListener('abort',abort,{once:true});if(options.signal?.aborted)abort();
 let response,data;
 try{
  response=await fetch('/api/v4'+path,{...options,signal:controller.signal,headers,credentials:'same-origin',cache:'no-store'});
  try{data=await response.json();}catch{throw new APIError('模考接口没有返回有效 JSON。',{status:response.status,kind:response.status>=500?'server':'backend-missing',path});}
 }catch(error){
  if(error instanceof APIError)throw error;
  throw new APIError(controller.signal.aborted?'连接模考服务超时。':'无法连接模考服务。',{kind:controller.signal.aborted?'timeout':'backend-unreachable',path});
 }finally{clearTimeout(timer);options.signal?.removeEventListener('abort',abort);}
 if(!response.ok){
  const detail=data?.detail,code=detail?.code;
  const kind=response.status===401?(code==='auth_expired'?'auth-expired':'auth-required'):response.status>=500?'server':'api';
  const message=typeof detail==='string'?detail:detail?.message||'请求未完成（'+response.status+'）';
  if(response.status===401)identityFlight=null;
  throw new APIError(message,{status:response.status,kind,path});
 }
 return data;
}
export function ensureIdentity(force=false){
 if(force)identityFlight=null;
 if(!identityFlight)identityFlight=request('/me').then(value=>{if(typeof sessionStorage!=='undefined')sessionStorage.setItem('gmf-had-auth','1');return value;}).catch(error=>{identityFlight=null;throw error;});
 return identityFlight;
}
