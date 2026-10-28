let loginBusy=false;
async function loginFromLauncher(){
 if(loginBusy)return;
 const status=document.getElementById('status'),fragment=location.hash.slice(1);
 if(!fragment){status.textContent='尚未提供登录凭证。请重新运行统一启动器，使用它生成的完整登录链接。';return;}
 history.replaceState(null,'','/local-login');loginBusy=true;status.textContent='正在验证启动入口…';
 try{
  const value=decodeURIComponent(fragment),data=value.startsWith('launch=')?{ticket:value.slice(7)}:{token:value};
  const response=await fetch('/api/v4/login',{method:'POST',credentials:'same-origin',cache:'no-store',headers:{'Content-Type':'application/json','X-GMF-Request':'1'},body:JSON.stringify(data)});
  if(!response.ok){let result;try{result=await response.json();}catch{}throw Error(result?.detail?.message||result?.detail||'登录未完成，请重新运行启动器。');}
  const check=await fetch('/api/v4/me',{credentials:'same-origin',cache:'no-store'});
  if(!check.ok)throw Error('浏览器未保留登录状态。请允许本站 Cookie，并使用同一浏览器中的 localhost 入口。');
  sessionStorage.setItem('gmf-had-auth','1');location.replace('/');
 }catch(error){status.textContent=error.message;}
 finally{loginBusy=false;if(location.hash)loginFromLauncher();}
}
addEventListener('hashchange',()=>{if(location.hash)loginFromLauncher();});
loginFromLauncher();
