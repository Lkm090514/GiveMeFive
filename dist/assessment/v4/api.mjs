let identityFlight=null;
export class APIError extends Error{constructor(message,{status=0,kind='api',path=''}={}){super(message);Object.assign(this,{status,kind,path});}}
export async function request(path,options={}){
 const headers={'X-GMF-Request':'1',...options.headers};
 if(options.body&&!(options.body instanceof FormData)){headers['Content-Type']='application/json';options={...options,body:JSON.stringify(options.body)};}
 let response;try{response=await fetch('/api/v4'+path,{...options,headers,credentials:'same-origin',cache:'no-store'});}catch{throw new APIError('无法连接本地 Python 服务。请运行 Start-GiveMeFive.cmd，并保持启动窗口打开。',{kind:'backend-unreachable',path});}
 let data;try{data=await response.json();}catch{throw new APIError('该地址没有返回题库 API 数据，可能启动了旧版静态预览。请使用项目根目录的统一启动器。',{status:response.status,kind:response.status>=500?'server':'backend-missing',path});}
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
