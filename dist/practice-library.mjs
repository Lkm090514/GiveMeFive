// Private resources are keyed by server instance + account, never by a shared API URL alone.
let flight;
async function inventory(){
 if(!flight)flight=fetch('/api/v4/library',{credentials:'same-origin',cache:'no-store'}).then(async r=>{if(!r.ok)throw Error(r.status===401?'请先通过本地启动入口登录。':'无法读取私人练习册资源清单。');return r.json();}).catch(e=>{flight=null;throw e;});
 return flight;
}
const name=(m,b)=>'givemefive-private-'+m.namespace+'-'+b.document_id+'-'+b.version;
export async function verified(response,item){if(!response)return false;const bytes=await response.arrayBuffer();if(bytes.byteLength!==item.bytes)return false;const hash=globalThis.GMFResourceHash?await globalThis.GMFResourceHash.sha256(bytes):Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');return hash===item.sha256;}
export async function resource(m,b,item){
 const cache=await caches.open(name(m,b)),url=new URL(item.url,location.origin).href,local=await cache.match(url);
 if(await verified(local?.clone(),item))return local;
 const response=await fetch(url,{credentials:'same-origin',cache:'no-store'});
 if(!response.ok)throw Error('资源读取失败（'+response.status+'）');
 if(!await verified(response.clone(),item))throw Error('资源完整性校验失败，请重试。');
 if(globalThis.GMFCacheAvailable!==false)await cache.put(url,response.clone());return response;
}
export async function cacheImage(img){
 const url=img.dataset.librarySrc;if(!url||img.dataset.loading)return;img.dataset.loading='1';
 try{
  const m=await inventory(),b=m.libraries.find(b=>b.resources.some(r=>r.url===url));
  if(!b){img.src=url;return;}
  const response=await resource(m,b,b.resources.find(r=>r.url===url));
  const object=URL.createObjectURL(await response.blob());img.onload=img.onerror=()=>URL.revokeObjectURL(object);img.src=object;
 }catch(error){img.alt+='（'+error.message+'）';img.src=url;}finally{delete img.dataset.librarySrc;}
}
export async function hydrateImages(scope){
 const images=[...scope.querySelectorAll('img[data-library-src]')];if(!images.length)return;
 try{
  const response=await fetch('/api/v4/me',{credentials:'same-origin',cache:'no-store'});
  if(!response.ok)throw Error('登录状态失效，请使用启动入口重新登录。');
  const identity=await response.json();if(flight&&(await flight).owner_id!==identity.owner_id)flight=null;
  await Promise.all(images.map(cacheImage));
 }catch(error){for(const img of images)img.alt+='（'+error.message+'）';}
}
export async function bindLibrarySettings(){
 const container=document.getElementById('practice-library');if(!container)return;
 const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const en=document.documentElement.lang==='en',say=(zh,enText)=>en?enText:zh;
 try{
  flight=null;const m=await inventory();
  container.innerHTML=`<h3>${say('私人 PDF 练习册','Private PDF workbooks')}</h3><p class="tiny">${say('按原卷目录分类。未预下载的题图会在打开题目时校验并缓存；下载只保存资源，不删除作答。练习与考试仍需本地服务运行。','Grouped by the original contents. Question images are verified and cached when opened. Downloading preserves answers. The local service is still required for practice and exams.')}</p>`;
  if(!m.libraries.length){container.insertAdjacentHTML('beforeend',`<p>${say('暂无已解析的私人练习册，请先在模考上传 PDF。','No parsed private workbooks. Upload a PDF in Assessment first.')}</p>`);return;}
  for(const b of m.libraries){
   const row=document.createElement('section');row.className='section';row.innerHTML=`<b>${esc(b.title)}</b><p>${b.question_count} ${say('题','questions')} · ${say('已分类','classified')} ${b.classified}</p><div class="mf-actions"><button class="btn secondary" data-download>${say('下载 / 继续下载练习册','Download / resume workbook')}</button><button class="ghost-btn" data-remove>${say('删除练习册缓存','Remove cached workbook')}</button><a class="ghost-btn" href="/assessment/#practice">${say('按知识点练习','Practice by topic')}</a></div><progress max="${b.resources.length}" value="0" style="width:100%"></progress><p role="status"></p>`;container.append(row);
   const status=row.querySelector('[role=status]'),bar=row.querySelector('progress'),download=row.querySelector('[data-download]'),remove=row.querySelector('[data-remove]');
   const count=async()=>{const cache=await caches.open(name(m,b));let n=0;for(const r of b.resources)if(await verified((await cache.match(new URL(r.url,location.origin).href))?.clone(),r))n++;bar.value=n;status.textContent=n===b.resources.length?say('已完整下载，资源校验通过。','Fully downloaded and verified.'):say(`已缓存 ${n} / ${b.resources.length} 个资源，可继续下载。`,`${n} / ${b.resources.length} resources cached; download can resume.`);};
   await count();
   if(globalThis.GMFCacheAvailable===false){download.disabled=remove.disabled=true;status.textContent=say('当前环境可在线查看。离线缓存请使用 HTTPS 或 localhost。','Online viewing is available. Offline caching requires HTTPS or localhost.');continue;}
   download.onclick=async()=>{download.disabled=remove.disabled=true;let done=0,failed=0;try{for(const item of b.resources){try{await resource(m,b,item);done++;}catch{failed++;}bar.value=done;status.textContent=say(`已校验 ${done} / ${b.resources.length}，失败 ${failed}`,`Verified ${done} / ${b.resources.length}; failed ${failed}`);}status.textContent=failed?say(`下载未完成：失败 ${failed} 个。点击继续下载可重试。`,`Incomplete: ${failed} failed. Resume to retry.`):say('已完整下载，资源校验通过。','Fully downloaded and verified.');}finally{download.disabled=remove.disabled=false;}};
   remove.onclick=async()=>{download.disabled=remove.disabled=true;try{const prefix='givemefive-private-'+m.namespace+'-'+b.document_id+'-';for(const key of await caches.keys())if(key.startsWith(prefix))await caches.delete(key);bar.value=0;status.textContent=say('练习册缓存已删除，原 PDF、作答与学习记录保留。','Cache removed. Original PDF, answers and learning records are preserved.');}finally{download.disabled=remove.disabled=false;}};
  }
 }catch(error){container.textContent=error.message;}
}
