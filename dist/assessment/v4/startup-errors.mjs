export function startupFailure(error,phase='identity',hadLogin=false){
 const kind=error.kind||(error.status===401?'auth-required':error.status>=500?'server':phase==='local-store'?'local-store':'api');
 if(kind==='auth-required'||kind==='auth-expired')return {title:kind==='auth-expired'||hadLogin?'登录状态已失效':'尚未登录',message:error.message,help:'请双击项目根目录 Start-GiveMeFive.cmd。已自动打开的默认浏览器可直接使用；在其他浏览器中，请使用启动窗口提供的手动登录入口。',action:'重新检查登录'};
 if(kind==='backend-unreachable')return {title:'本地服务未运行或连接中断',message:error.message,help:'学习路径的已缓存页面仍可能打开，但题库需要真实 Python 后端。请保持启动窗口打开。',action:'重新连接'};
 if(kind==='backend-missing')return {title:'未连接完整题库服务',message:error.message,help:'请关闭旧版静态预览，使用项目根目录 Start-GiveMeFive.cmd。',action:'重新连接'};
 if(kind==='server')return {title:'题库服务内部错误',message:error.message,help:'登录可能仍然有效。请查看启动窗口或后端日志，再重试。',action:'重试'};
 if(kind==='local-store')return {title:'浏览器学习记录暂不可读取',message:error.message,help:'请允许本站存储。不要清除学习数据；必要时先导出备份。',action:'重试'};
 return {title:'题库请求未完成',message:error.message,help:'请重新检查服务连接；这不代表题库为空或需要重新登录。',action:'重试'};
}
