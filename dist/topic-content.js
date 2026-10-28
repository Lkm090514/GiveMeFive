(function(){
'use strict';
const D = window.PathlineTextbook;
const ui=(text,vars={})=>window.PathlineUI?window.PathlineUI.t(window.PathlineLanguage||'zh',text,vars):text.replace(/\{(\w+)\}/g,(_,k)=>vars[k]??'');
const byId = (items, key) => new Map(items.map(item => [item[key], item]));
let topics = byId(D.course.topics, 'topic_id');
let readings,exercises,assets,supplements;
function indexes(){readings=byId(D.readings,'content_id');exercises=byId(D.exercises,'exercise_id');assets=byId(D.assets,'asset_id');supplements=byId(D.supplements,'supplement_id');}
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function region(ref, label) {
  const asset = assets.get(ref.asset_id);
  const [x0,y0,x1,y1] = ref.bbox;
  return `<figure class="source-region"><svg class="page-region" viewBox="${x0} ${y0} ${x1-x0} ${y1-y0}" role="img" aria-label="${esc(label)}"><title>${esc(label)}</title><image data-source-image="${esc(asset.path)}" x="0" y="0" width="612" height="792"/></svg><figcaption>${ui('印刷页')} ${ref.printed_page} · ${ui('PDF 第 {n} 页',{n:ref.pdf_page})} · OpenStax · <a target="_blank" rel="noopener" href="source/pdf-viewer.html#page=${ref.pdf_page}">${ui('查看原页')}</a></figcaption></figure>`;
}
function exercise(id) {
  const e = exercises.get(id);
  if (!e || e.visibility !== 'visible') throw new Error(`Invalid exercise reference: ${id}`);
  const dependency = e.dependency_refs?.length ? `<p class="meta">${ui('本题引用')}：${e.dependency_refs.map(r => r.kind==='exercise' ? `<button data-jump-exercise="${r.exercise_id}">${ui('原题')} ${esc(r.source_number)}</button>` : `<a target="_blank" href="source/pdf-viewer.html#page=${r.pdf_page}">Figure ${esc(r.figure_number)}</a>`).join(' · ')}</p>` : '';
  return `<details class="card exercise" data-exercise-id="${esc(id)}"><summary>${esc(e.exercise_type)} · ${e.source_number} · §${esc(e.source_section || ui('跨节习题'))}</summary>${dependency}${e.render_refs.map(r => region(r,`Chapter ${e.source_chapter} Exercise ${e.source_number}`)).join('')}${e.answer_ref ? `<a target="_blank" rel="noopener" href="source/pdf-viewer.html#page=${e.answer_ref.pdf_page}">Answer Key · ${ui('印刷页')} ${e.answer_ref.printed_page} / PDF ${e.answer_ref.pdf_page}</a>` : `<p class="meta">${ui('原教材未索引到本题答案。')}</p>`}<div class="exercise-actions"><button class="btn secondary small" aria-pressed="false" data-exposure-exercise="${esc(id)}">${ui('记录已完成')}</button><button class="btn secondary small" aria-pressed="false" data-save-exercise="${esc(id)}">${ui('留下这道题')}</button></div></details>`;
}
function supplementHTML(t) {
  return t.supplement_refs.map(id=>{
    const s=supplements.get(id);
    return `<section class="card supplement"><h2>${esc(s.title)}</h2>${s.formulas.map(f=>`<p class="formula">${esc(f)}</p>`).join('')}${s.notes.map(n=>`<p>${esc(n)}</p>`).join('')}</section>`;
  }).join('');
}
function renderChapter(ch) {
  const c=D.reviews.find(r=>r.chapter===ch);
  if (!c) return '<h1>没有这个章末习题入口</h1>';
  let html=`<h1>${esc(window.PathlineLanguage==='en'?`Chapter ${ch} exercises`:c.title)}</h1>`;
  for (const [kind,ids] of Object.entries(c.categories)) html+=`<h2>${esc(kind)}（${ids.length}）</h2>`+(ids.length?ids.map(exercise).join(''):`<p class="meta">${ui('当前没有正式习题')}</p>`);
  return html;
}

let objects,figures;
function refresh(){topics=byId(D.course.topics,'topic_id');indexes();objects=D.objects||[];figures=D.figures||[];}
function anchorId(ref){return 'source-'+ref;}
function topic(id){
  refresh();
  const t=topics.get(id);if(!t)return '<h2>未找到这个 Topic</h2>';
  if(t.status!=='validated')return `<section class="card pad"><h2>正式内容待完成</h2><p>本 Topic 仅建立了教材对应关系，正文和习题尚未处理。</p><p class="meta">${t.source_refs.map(r=>`OpenStax §${esc(r.replace('os-section-',''))}`).join(' · ')}</p></section>${supplementHTML(t)}`;
  const goals=(window.PathlineLanguage==='en'?window.PathlineReviewContract?.goals_en[id]:window.PathlineFusion.goals[id])||t.learning_goals||[];
  let html=`<section id="learning-goals"><h2>${ui('学习目标')}</h2><ul>${goals.map(g=>`<li>${esc(g)}</li>`).join('')}</ul></section>`;
  html+=`<section id="textbook-reading"><h2>${ui('OpenStax 原教材正文')}</h2>`;
  let lastSection=null;
  for(const ref of t.reading_refs){const r=readings.get(ref);if(r.source_section!==lastSection){html+=`<h3>OpenStax §${esc(r.source_section)}</h3>`;lastSection=r.source_section;}
    const labels=objects.filter(o=>(o.content_ref===ref||(o.content_refs||[]).includes(ref))&&['example','check_your_understanding'].includes(o.object_type)).map(o=>`${o.object_type==='example'?'Example':'Check Your Understanding'} ${o.number||''}`);
    const fig=figures.filter(f=>(f.reading_refs||[]).includes(ref)).map(f=>`Figure ${f.figure_number}`);
    html+=`<div id="${anchorId(ref)}">${[...fig,...labels].length?`<p class="reading-labels">${[...fig,...labels].map(esc).join(' · ')}</p>`:''}${region(r,`${t.title} · §${r.source_section} · printed ${r.printed_page}`)}</div>`;
  }
  html+='</section><section id="supplements">'+supplementHTML(t)+'</section>';
  html+=`<section id="exercises"><h2>${ui('正式教材习题')}（${t.exercise_refs.length}）</h2>${t.exercise_refs.map(exercise).join('')}</section>`;
  const chapters=[...new Set(t.source_refs.map(r=>Number(r.replace('os-section-','').split('.')[0])))];
  html+=`<section id="chapter-reviews"><h2>${ui('本章课后习题')}</h2>${chapters.map(ch=>`<details class="chapter-review"><summary>Chapter ${ch} · ${ui('正式教材习题')}</summary>${renderChapter(ch)}</details>`).join('')}</section>`;
  html+=`<section class="source-info" id="source-info"><h2>${ui('来源信息')}</h2><p>OpenStax / Rice University · University Physics Volume 1 · CC BY-NC-SA 4.0.</p><p>${ui('原图署名与许可见原图图注。')}</p><p><a href="source/pdf-viewer.html" target="_blank" rel="noopener">${ui('打开完整原教材 PDF')}</a></p><p class="meta">${ui('原文件缺少印刷页 863–874。')}</p></section>`;
  return html;
}
function navigation(id){refresh();const t=topics.get(id);if(!t||t.status!=='validated')return '<p class="meta">正式内容待完成。</p>';
  const buttons=[['learning-goals','学习目标'],['textbook-reading','OpenStax 正文']];
  for(const f of figures.filter(f=>(f.reading_refs||[]).some(r=>t.reading_refs.includes(r))))buttons.push([anchorId(f.reading_refs.find(r=>t.reading_refs.includes(r))),`Figure ${f.figure_number}`]);
  for(const o of objects.filter(o=>[o.content_ref,...(o.content_refs||[])].some(ref=>t.reading_refs.includes(ref))&&['example','check_your_understanding'].includes(o.object_type)))buttons.push([anchorId([o.content_ref,...(o.content_refs||[])].find(ref=>t.reading_refs.includes(ref))),`${o.object_type==='example'?'Example':'Check Your Understanding'} ${o.number||''}`]);
  if(t.supplement_refs.length)buttons.push(['supplements','Supplement']);
  buttons.push(['exercises',`正式教材习题（${t.exercise_refs.length}）`],['chapter-reviews','本章课后习题'],['source-info','来源信息']);
  return buttons.map(([id,label])=>`<button data-anchor="${esc(id)}">${esc(label.replace('正式教材习题',ui('正式教材习题')).replace('本章课后习题',ui('本章课后习题')).replace('来源信息',ui('来源信息')).replace('学习目标',ui('学习目标')).replace('OpenStax 正文',ui('OpenStax 正文')))}</button>`).join('');
}
function repair(topicId,sources){
  refresh();const t=topics.get(topicId);if(!t)throw new Error('Unknown repair topic');
  return sources.map(source=>{
    if(source.kind==='supplement'){if(!t.supplement_refs.includes(source.ref))throw new Error('Invalid repair supplement');return supplementHTML({...t,supplement_refs:[source.ref]});}
    let refs=source.kind==='reading'?[source.ref]:source.kind==='figure'?figures.find(f=>f.figure_id===source.ref)?.reading_refs:[objects.find(o=>o.object_id===source.ref)?.content_ref];
    refs=(refs||[]).filter(ref=>t.reading_refs.includes(ref));if(!refs.length)throw new Error('Repair source outside topic');
    return `<section class="card repair-source"><h2>${esc(source.label)}</h2>${refs.map(ref=>region(readings.get(ref),source.label)).join('')}</section>`;
  }).join('');
}
window.PathlineContent={topic,navigation,repair};

})();
