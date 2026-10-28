export function startupFailure(error,phase='identity',hadLogin=false,local=false){
 const kind=error.kind||(error.status===401?'auth-required':error.status>=500?'server':phase==='local-store'?'local-store':'api');
 if(kind==='auth-required'||kind==='auth-expired')return {title:kind==='auth-expired'||hadLogin?'登录状态已失效':'请登录后继续',message:'登录后可以继续自己的试卷与考试记录。',help:local?'请使用本机启动器提供的登录入口。':'请使用自己的账号登录。尚未注册时需要管理员邀请。',action:'重新检查登录',login_href:local?'/local-login':'/assessment/login.html'};
 if(['backend-unreachable','backend-missing','server','timeout'].includes(kind))return {title:'模考服务暂时不可用',message:kind==='timeout'?'连接服务超时，请稍后重试。':'暂时无法连接模考服务，你的已保存记录不会因此被删除。',help:local?'请检查本机 Python 服务是否仍在运行。':'请稍后重新连接。若持续出现，请联系管理员检查服务状态。',action:'重新连接'};
 if(kind==='local-store')return {title:'浏览器学习记录暂不可读取',message:error.message,help:'请允许本站存储。不要清除学习数据；必要时先导出备份。',action:'重试'};
 return {title:'题库请求未完成',message:error.message,help:'请重试。这不代表题库为空或需要重新登录。',action:'重试'};
}
