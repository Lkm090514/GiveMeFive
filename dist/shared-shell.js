(function(root){
  'use strict';
  const BASE=new URL('.',document.currentScript.src),Store=root.LearningStore;
  let current={},context={course_id:null,unit_id:null,topic_id:null,return_to:new URL('#pathway',BASE).href},catalog;
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function text(zh,en){return current.lang==='en'?en:zh;}
  function examCountdown(date,now=new Date()){
    if(!/^\d{4}-\d{2}-\d{2}$/.test(date||''))return null;
    const [y,m,d]=date.split('-').map(Number),target=new Date(y,m-1,d);
    if(target.getFullYear()!==y||target.getMonth()!==m-1||target.getDate()!==d)return null;
    return Math.round((Date.UTC(y,m-1,d)-Date.UTC(now.getFullYear(),now.getMonth(),now.getDate()))/86400000);
  }
  function countdownText(id){
    const days=examCountdown(current.examDates?.[id]);if(days===null)return '';
    const c=(current.customCourses||[]).find(c=>c.id===id)||root.PathlineData?.courses?.[id];
    const name=c?.title||(id===catalog?.course_id?catalog.title:null)||(id==='ap-physics-c-mechanics-2026-27'?'AP Physics C: Mechanics':id);
    return name+' · '+(days>0?text('距考试 '+days+' 天',days+' days to exam'):days===0?text('今天考试','Exam today'):text('考试已结束','Exam date passed'));
  }
  function refreshCountdown(){for(const el of document.querySelectorAll('[data-gmf-countdown]')){el.textContent=countdownText(el.dataset.gmfCountdown);el.hidden=!el.textContent;}}
  function safeReturn(value){try{const u=new URL(value||'#pathway',BASE);return u.origin===BASE.origin&&u.pathname.startsWith(BASE.pathname)?u.href:new URL('#pathway',BASE).href;}catch{return new URL('#pathway',BASE).href;}}
  function url(module,ctx=context){const u=new URL(({pathline:'#pathway',mindflow:'#mindflow/focus',assessment:'assessment/',review:'mind-flow/review.html',progress:'#progress',settings:'#settings',courses:'#courses'})[module]??'',BASE);for(const key of ['course_id','unit_id','topic_id','return_to'])if(ctx[key]!=null)u.searchParams.set(key,ctx[key]);if(module==='review')u.searchParams.set('new_session','1');return u.href;}
  function parseContext(params=new URLSearchParams(location.search)){
    const courseId=params.get('course_id'),topicId=params.get('topic_id');
    let course=courseId===catalog?.course_id?catalog:null;
    const custom=(current.customCourses||[]).find(c=>c.id===courseId);
    const unit=course?.units.find(u=>u.topic_refs.includes(topicId))||custom?.units.find(u=>u.topics.some(t=>t.id===topicId));
    const validCourse=!!course||!!custom;
    return {course_id:validCourse?courseId:null,unit_id:unit?.unit_id??unit?.id??null,topic_id:unit?topicId:null,return_to:safeReturn(params.get('return_to'))};
  }
  function title(ctx=context){if(!ctx.course_id)return text('不绑定课程，自由开始','Start freely, without a course');const t=catalog?.topics.find(t=>t.topic_id===ctx.topic_id),custom=(current.customCourses||[]).find(c=>c.id===ctx.course_id);return (ctx.course_id===catalog?.course_id?'Physics C':custom?.title||ctx.course_id)+(t?' · '+t.topic_id+' '+t.title:'');}
  function header(module,ctx=context){return `<header class="gmf-global"><a class="gmf-brand" href="${esc(url('pathline',ctx))}"><span class="gmf-bars" aria-hidden="true">${[0,1,2,3,4].map(bar=>`<i style="height:${12+bar*3}px"></i>`).join('')}</span>GiveMeFive</a><nav aria-label="${text('核心系统','Core systems')}">${['pathline','mindflow','assessment','progress'].map(m=>`<a href="${esc(url(m,ctx))}" ${m===module?'aria-current="page"':''}>${(current.lang==='en'?{pathline:'Pathline',mindflow:'Mind Flow',assessment:'Assessment',progress:'Progress'}:{pathline:'学习路径',mindflow:'心流',assessment:'模考',progress:'进度'})[m]}</a>`).join('')}</nav><span class="gmf-countdown" data-gmf-countdown="${esc(ctx.course_id||current.activeCourseId||'')}" ${countdownText(ctx.course_id||current.activeCourseId)?'':'hidden'}>${esc(countdownText(ctx.course_id||current.activeCourseId))}</span><div class="gmf-secondary"><a href="${esc(url('courses',ctx))}">${text('课程','Courses')}</a><a href="${esc(url('settings',ctx))}">${text('设置','Settings')}</a><button type="button" data-gmf-lang aria-label="${text('切换语言','Switch language')}">${current.lang==='en'?'中':'EN'}</button><button type="button" data-gmf-theme aria-label="${text('切换明暗主题','Switch theme')}">◐</button></div></header>`;}
  function preferences(){const theme=current.theme==='system'?matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light':current.theme||'light';document.documentElement.dataset.theme=theme;document.documentElement.lang=current.lang==='en'?'en':'zh-CN';document.body.classList.toggle('dark',theme==='dark');root.PathlineLanguage=current.lang||'zh';return {theme,lang:current.lang||'zh'};}
  async function init(){await Store.open();current=await Store.getModule('current')||{};Object.assign(current,await Store.getModule('preferences')||{});try{const u=new URL('data/course.json',BASE);const r=await fetch(u);catalog=await r.json();}catch{catalog=null;}context=parseContext();preferences();return {current,context};}
  function mount(module){document.querySelector('.gmf-global')?.remove();document.body.insertAdjacentHTML('afterbegin',header(module));document.querySelector('[data-gmf-theme]').onclick=async()=>{current.theme=preferences().theme==='dark'?'light':'dark';await Store.putModule('preferences',{theme:current.theme,lang:current.lang});await Store.patchCurrent({theme:current.theme});preferences();document.dispatchEvent(new CustomEvent('gmf-preferences',{detail:preferences()}));};document.querySelector('[data-gmf-lang]').onclick=async()=>{current.lang=current.lang==='en'?'zh':'en';await Store.putModule('preferences',{theme:current.theme,lang:current.lang});await Store.patchCurrent({lang:current.lang});preferences();mount(module);document.dispatchEvent(new CustomEvent('gmf-preferences',{detail:preferences()}));};}
  // An active module link preserves the current form/session and does not reload it.
  document.addEventListener('click',e=>{const a=e.target.closest?.('.gmf-global nav a[aria-current="page"]');if(!a||e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;e.preventDefault();e.stopImmediatePropagation();},true);
  function session(ctx,mode,id=crypto.randomUUID()){return {session_id:id,course_id:ctx.course_id,unit_id:ctx.unit_id,topic_id:ctx.topic_id,source:mode==='assessment'?'Assessment':'MF',mode,started_at:new Date().toISOString(),ended_at:new Date().toISOString(),active_seconds:0,daily_seconds:{}};}
  async function finishFocus(record,values){const s=record.study_session;const event={schema_version:3,event_id:s.session_id,session_id:s.session_id,course_id:s.course_id,unit_id:s.unit_id,topic_id:s.topic_id,exercise_id:null,source:'MF',type:'MF_SESSION_COMPLETED',occurred_at:record.date,payload:{mode:'focus',timer_mode:record.mode,goal:record.goal,completed_steps:record.steps.filter(t=>t.status==='done').map(t=>t.title),remaining_steps:record.steps.filter(t=>t.status!=='done').map(t=>t.title),blockers:record.notes,active_seconds:s.active_seconds}};await Store.commit('mf-focus',values,event,s);}
  const originals=new WeakMap();
  function localize(scope=document.body){
    if(!scope||!root.PathlineUI?.aliases)return;
    const blocked='[data-user-content],[data-original-content],.as-stem,.as-shared,.topic-body,script,style,textarea,pre';
    const walker=document.createTreeWalker(scope,NodeFilter.SHOW_TEXT);let node;
    while(node=walker.nextNode()){
      if(node.parentElement?.closest(blocked))continue;
      const raw=node.textContent,prior=originals.get(node),source=prior&&raw===prior.last?prior.source:raw;
      const clean=source.trim(),ui=root.PathlineUI;
      if(!Object.hasOwn(ui.dictionary,clean)&&!Object.hasOwn(ui.aliases,clean))continue;
      const next=source.replace(clean,ui.t(root.PathlineLanguage||'zh',clean));originals.set(node,{source,last:next});if(next!==raw)node.textContent=next;
    }
    for(const el of scope.querySelectorAll?.('[aria-label],[title],[placeholder]')||[]){if(el.closest(blocked))continue;for(const attr of ['aria-label','title','placeholder']){const raw=el.getAttribute(attr);if(!raw)continue;const key='data-ui-'+attr;const source=el.getAttribute(key)||raw;if(!Object.hasOwn(root.PathlineUI.dictionary,source)&&!Object.hasOwn(root.PathlineUI.aliases,source))continue;if(!el.hasAttribute(key))el.setAttribute(key,source);el.setAttribute(attr,root.PathlineUI.t(root.PathlineLanguage||'zh',source));}}
  }
  // Dynamic feedback and dialogs share the same dictionary as the navigation.
  if(typeof MutationObserver!=='undefined'){
    const pending=new Set();let queued=false;
    const observe=()=>new MutationObserver(records=>{for(const record of records){const el=record.target.nodeType===3?record.target.parentElement:record.target;if(el?.isConnected)pending.add(el);}if(!queued){queued=true;queueMicrotask(()=>{queued=false;for(const el of pending)localize(el);pending.clear();});}}).observe(document.body,{childList:true,subtree:true,characterData:true});
    if(document.body)observe();else document.addEventListener('DOMContentLoaded',observe,{once:true});
    document.addEventListener('gmf-preferences',()=>localize());
  }
  root.GMFShared={examCountdown,refreshCountdown,localize,init,mount,header,url,title,esc,text,preferences,session,finishFocus,get context(){return context;},get current(){return current;},setCurrent:value=>{current=value;},safeReturn};
})(window);
