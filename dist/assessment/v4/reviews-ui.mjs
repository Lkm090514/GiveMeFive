const states={repair:'待修正',independent:'等待独立检查',delayed:'等待延迟复查',due:'延迟复查已到期',passed:'本次复查通过'};
const events={error:'记录错误',uncertain:'标记猜对但不确定',note:'保存笔记',correction:'完成一次修正',review_started:'开始复查',review_passed:'整组复查通过',review_failed:'复查失败，返回修正',review_inconclusive:'答案或证据变化，本次不推进状态',review_uncertain:'提交后标记不确定，恢复等待独立检查',manually_removed:'手动移出'};

export function reviewPanel(m,{esc,button}){
 const c=m.review||{state:'repair',notes:[],events:[]},last=c.notes.at(-1),same=last?.version_id===m.version_id;
 return `<section class="as-feedback"><h3>修正与可选复查</h3><p>${esc(states[c.display_state||c.state]||c.state)}${c.due_at?' · '+esc(new Date(c.due_at).toLocaleString()):''}</p><p class="muted">笔记可以留空。独立检查使用未见过、有可靠答案的公共题；通过一次不表示永久掌握。</p>${c.active_review?`<a class="as-btn" href="#session/${encodeURIComponent(c.active_review)}">继续未完成的复查</a>`:`<form data-note-form="${esc(m.question_id)}" data-previous="${esc(last?.id||'')}" data-assets="${esc(JSON.stringify(same?last.assets:[]))}" class="as-form"><label>错误原因 / 不确定的原因<input name="cause" maxlength="12000" value="${esc(same?last.cause:'')}"></label><label>正确解题思路<textarea name="reasoning" maxlength="12000">${esc(same?last.reasoning:'')}</textarea></label><label>文字笔记或步骤<textarea name="text" maxlength="12000">${esc(same?last.text:'')}</textarea></label><label>步骤图片（可选，每张最多 4 MiB）<input name="images" type="file" accept="image/png,image/jpeg,image/webp" multiple></label><label><input name="ready" type="checkbox">已完成修正，准备独立检查</label><button class="as-btn">保存笔记 / 修正</button></form><div class="as-actions"><label>复查题数 <input data-review-count="${esc(m.question_id)}" type="number" min="1" max="20" value="3" style="width:70px"></label>${c.state==='independent'?button('开始独立检查',`data-review="${esc(m.question_id)}" data-phase="independent"`,true):''}${c.state==='delayed'?button('开始延迟复查',`data-review="${esc(m.question_id)}" data-phase="delayed" ${c.display_state!=='due'?'disabled':''}`,true):''}</div>`}<details><summary>笔记修改历史（${c.notes.length}）与复查证据</summary>${c.notes.map(n=>`<article class="as-feedback"><small>${esc(new Date(n.at).toLocaleString())} · 题目版本 ${esc(n.version_id)}</small><p style="white-space:pre-wrap">原因：${esc(n.cause)}\n思路：${esc(n.reasoning)}\n${esc(n.text)}</p>${n.assets.map(a=>`<img class="as-image" loading="lazy" src="/api/v4/learning/images/${esc(a)}" alt="本次修正的步骤图片">`).join('')}</article>`).join('')}<ul>${c.events.map(e=>`<li>${esc(new Date(e.at).toLocaleString())} · ${esc(events[e.kind]||e.kind)}${e.session_id?` · <a href="#session/${encodeURIComponent(e.session_id)}">查看整组作答</a>`:''}</li>`).join('')}</ul></details></section>`;
}

export function bindReviews({request,act,say,openSession,refresh}){
 for(const el of document.querySelectorAll('[data-uncertain]'))el.onclick=()=>act(async()=>{await request('/learning/uncertain',{method:'POST',body:{record_id:el.dataset.uncertain}});say('已保存为“猜对但不确定”，原分数和作答不变。');});
 for(const form of document.querySelectorAll('[data-note-form]'))form.onsubmit=e=>{e.preventDefault();act(async()=>{
  const f=new FormData(form),assets=JSON.parse(form.dataset.assets||'[]'),files=f.getAll('images').filter(x=>x.size);
  if(assets.length+files.length>8)throw Error('每次修正最多保留 8 张图片');
  for(const file of files){if(file.size>4*1024*1024)throw Error('步骤图片须小于 4 MiB');const body=new FormData();body.set('file',file);assets.push((await request('/learning/'+form.dataset.noteForm+'/images',{method:'POST',body})).asset_id);}
  await request('/learning/'+form.dataset.noteForm+'/notes',{method:'POST',body:{cause:f.get('cause'),reasoning:f.get('reasoning'),text:f.get('text'),assets,expected_note_id:form.dataset.previous||null,ready_for_check:f.has('ready')}});await refresh();say('已保存，原笔记和作答记录仍保留。');
 });};
 for(const el of document.querySelectorAll('[data-review]'))el.onclick=()=>act(async()=>{
  const input=[...document.querySelectorAll('[data-review-count]')].find(x=>x.dataset.reviewCount===el.dataset.review);
  openSession(await request('/sessions',{method:'POST',body:{mode:'practice',request_id:crypto.randomUUID(),review_question:el.dataset.review,review_phase:el.dataset.phase,count:Number(input?.value||3)}}));
 });
}
