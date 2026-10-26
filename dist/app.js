(async () => {
  'use strict';
  await LearningStore.open();
  await ContentRuntime.init();
  const REVIEW_PAGE=document.body.dataset.module==='mf-review';
  const MFV3=REVIEW_PAGE?null:await import('./mind-flow/v3/ui.mjs?v=4.2-focus');
  const Data=window.PathlineData, Engine=window.PathlineEngine, Parsers=window.PathlineParsers, I18n=window.PathlineI18n;
  const F=window.PathlineFusion, physics=F.makeCourse(window.PathlineTextbook);
  const KEY='pathline.fusion.v0.1.state',Sessions=window.PathlineSessions;
  const DEFAULT={
    version:5,onboarded:true,theme:'light',lang:'zh',name:'本地学习者',activeCourseId:physics.id,customCourses:[],evidence:F.emptyEvidence(),targets:{},sessions:[],savedExercises:[],deletedCourseIds:[],tocCollapsed:false,directoryCollapsed:false,mfEntryContext:null,mfContext:null,mfRuns:{},assessmentContext:null,
    examDates:{stats:'',micro:'',sat:'',ielts:''},
    progress:{},activity:[],streak:{count:0,lastDay:null},settings:{dailyGoal:35,sound:false,compact:false},route:'overview',routeParams:{},draftImport:null
  };
  let state=await load(), quiz=null, deferredInstall=null, readingScroll=0,selectedWeekDay=null,selectedWeekCourse=null,activeSession=null,lastInputAt=Date.now(),lastSessionTick=Date.now(),mfSessionActive=false,sessionVisible=!document.hidden;
  GMFShared.setCurrent(state);
  document.body.classList.toggle('gmf-review',REVIEW_PAGE);
  const params=new URLSearchParams(location.search);if(params.get('course_id')&&allCourses()[params.get('course_id')])state.activeCourseId=params.get('course_id');
  const app=document.getElementById('app');
  const toastRoot=document.getElementById('toast-root');
  const stateImport=document.getElementById('state-import');

  function clone(x){return JSON.parse(JSON.stringify(x));}
  async function load(){
    let raw;try{raw=JSON.parse(localStorage.getItem(KEY)||'null');}catch{}
    const legacy=migrate(raw?{...clone(DEFAULT),...raw}:clone(DEFAULT));
    const restored=await LearningStore.restore(legacy,window.PathlineTextbook.course);Object.assign(restored,await LearningStore.getModule('preferences')||{},await LearningStore.getModule('mf-review')||{});return migrate(restored);
  }
  function migrate(s){
    s.customCourses=Array.isArray(s.customCourses)?s.customCourses:[];s.progress=s.progress||{};s.activity=Array.isArray(s.activity)?s.activity:[];
    s.examDates={...DEFAULT.examDates,...(s.examDates||{})};s.settings={...DEFAULT.settings,...(s.settings||{})};s.route=s.route||'overview';s.routeParams=s.routeParams||{};
    s.lang=s.lang==='en'?'en':'zh';
    s.evidence=s.evidence&&['exposure','learning_repair','assessment'].every(k=>Array.isArray(s.evidence[k]))?s.evidence:F.emptyEvidence();
    F.normalizeEvidence(s.evidence);
    s.mfRuns=s.mfRuns&&typeof s.mfRuns==='object'?s.mfRuns:{};
    for(const run of Object.values(s.mfRuns))run.paused=false;
    s.version=6;s.sessions=Array.isArray(s.sessions)?s.sessions.filter(x=>x&&(x.course_id==null||typeof x.course_id==='string')&&(x.topic_id==null||typeof x.topic_id==='string')&&['learn','review','assessment','focus'].includes(x.mode)&&Number.isFinite(x.active_seconds)&&x.active_seconds>=0):[];
    s.savedExercises=Array.isArray(s.savedExercises)?s.savedExercises:[];
    s.targets=s.targets&&typeof s.targets==='object'?s.targets:{};
    s.deletedCourseIds=Array.isArray(s.deletedCourseIds)?s.deletedCourseIds.filter(id=>typeof id==='string'):[];
    for(const c of [physics,...s.customCourses])if(F.isAP(c))s.targets[c.id]=F.targetScore(c,s.targets[c.id]);
    s.customCourses=s.customCourses.filter(c=>c&&typeof c.id==='string'&&typeof c.title==='string'&&Array.isArray(c.units)&&c.units.every(u=>Array.isArray(u.topics)&&u.topics.every(t=>typeof t.id==='string'&&typeof t.title==='string')));
    if(![physics.id,...Object.keys(Data.courses),...s.customCourses.map(c=>c.id)].includes(s.activeCourseId))s.activeCourseId=physics.id;
    if(s.route==='import')s.route='courses';
    if(!['overview','pathway','review','progress','courses','settings','study','mindflow','assessment'].includes(s.route))s.route='overview';
    return s;
  }
  function save(){if(REVIEW_PAGE)LearningStore.putModule('mf-review',{mfContext:state.mfContext,mfRuns:state.mfRuns});LearningStore.putModule('preferences',{lang:state.lang,theme:state.theme});return LearningStore.save(state,window.PathlineTextbook.course).catch(()=>{toast(U('浏览器无法保存，请先导出备份；关闭页面可能丢失记录。'));return false;});}
  function T(key,vars={}){return I18n.t(state.lang,key,vars)}
  function L(en,zh){return state.lang==='zh'?zh:en}
  function cText(c,field){return I18n.course(state.lang,c,field)||''}
  function uText(u,field){return I18n.unit(state.lang,u,field)||''}
  function tText(topic,field){return I18n.topic(state.lang,topic,field)||''}
  function tObjectives(topic){return state.lang==='en'&&window.PathlineReviewContract.goals_en[topic.id]?window.PathlineReviewContract.goals_en[topic.id]:I18n.objectives(state.lang,topic)}
  function tQuestion(topic,index,q){return I18n.question(state.lang,topic,index,q)}
  function reasonText(r){return I18n.reason(state.lang,r)}
  function registeredCourses(){return {...Data.courses,[physics.id]:physics,...Object.fromEntries(state.customCourses.map(c=>[c.id,c]))};}
  function allCourses(){return Object.fromEntries(Object.entries(registeredCourses()).filter(([id])=>!state.deletedCourseIds.includes(id)));}
  function course(id=state.activeCourseId){return allCourses()[id]||physics;}
  function ensureProgress(c){state.progress[c.id]=Engine.ensureCourseProgress(c,state.progress[c.id]||{});save();return state.progress[c.id];}
  function progress(c=course()){return ensureProgress(c);}
  function setAccent(){document.documentElement.style.setProperty('--accent','var(--blue)');}
  function setTheme(){let mode=state.theme;if(mode==='system')mode=matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';document.documentElement.dataset.theme=mode;if(state.mfContext)state.mfContext.theme=mode;document.querySelector('meta[name="theme-color"]').content=mode==='dark'?'#15181D':'#F5F7FB';}
  function setLanguage(){
    window.PathlineLanguage=state.lang;document.documentElement.lang=state.lang==='zh'?'zh-CN':'en';
    document.title='GiveMeFive · '+labelForRoute();
    const meta=document.querySelector('meta[name="description"]');
    if(meta)meta.content=state.lang==='zh'?'把课程材料转化为自适应学习路径：主动提取、间隔复习与可解释优先级。':'Pathline turns course material into an adaptive learning pathway with retrieval practice, spaced review and explainable priorities.';
  }
  function esc(s=''){return String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
  function fmtDate(ts){if(!ts)return T('common.notStudied');return new Intl.DateTimeFormat(state.lang==='zh'?'zh-CN':'en-US',{month:'short',day:'numeric'}).format(new Date(ts));}
  function relDue(ts){
    if(!ts)return T('common.now');const d=(ts-Date.now())/86400000;
    if(d<=0)return T('common.dueNow');if(d<1)return T('common.inHours',{n:Math.max(1,Math.round(d*24))});if(d<7)return T('common.inDays',{n:Math.round(d)});return fmtDate(ts);
  }
  function pct(n){return `${Math.max(0,Math.min(100,Math.round(n)))}%`}
  function icon(name){const m={overview:'◫',pathway:'↗',review:'⟳',progress:'⌁',import:'＋',settings:'⚙',moon:'◐',sun:'☀',book:'▤',target:'◎',spark:'✦',arrow:'→',back:'←',check:'✓',upload:'↑',download:'↓'};return m[name]||'•'}
  function toast(msg){toastRoot.innerHTML=`<div class="toast">${esc(msg)}</div>`;setTimeout(()=>{toastRoot.innerHTML=''},2600)}
  async function route(name,params={}){
    if(name==='assessment'){await jump(name,params.topicId);return;}
    if(REVIEW_PAGE){sessionTick();await save();location.href=GMFShared.url(name==='progress'?'progress':'pathline',moduleContext(state.mfContext?.topic_id))+(name==='review'?'#review':'');return;}
    if(name==='progress'){const latest=await LearningStore.restore(state,window.PathlineTextbook.course);state.evidence=latest.evidence;state.sessions=latest.sessions;}
    if(name==='import')name='courses';
    if(!Object.keys(allCourses()).length && !['courses','settings'].includes(name))name='courses';
    if(name==='study')try{await ContentRuntime.ensureTopic(params.topicId);}catch{toast(U('课程内容暂时无法加载，请联网后重试。'));return;}
    if(name==='mindflow'&&state.route!=='mindflow')state.mfEntryContext=moduleContext(params.topicId||state.routeParams.topicId);
    state.route=name;state.routeParams=params;
    const hash=name==='study'?`#topic/${params.topicId}/${params.section||'reading'}`:name==='mindflow'?`#mindflow/${params.page||'focus'}`:`#${name}`;
    history.replaceState(null,'',hash);
    if(name==='study' && F.isReady(topicById(course(),params.topicId)?.topic||{}))expose(params.topicId,'topic_opened');
    save();render();window.scrollTo({top:0,behavior:'instant'});document.querySelector('.main')?.scrollTo({top:0,behavior:'instant'});
  }
  function activeExamDate(c){return state.examDates[c.id]||''}
  function recordActivity(type,cid,topicId,meta={}){
    state.activity.unshift({at:Date.now(),type,cid,topicId,...meta});state.activity=state.activity.slice(0,300);
    const day=F.dayKey(),last=state.streak.lastDay;
    if(last!==day){const y=F.dayKey(Date.now()-86400000);state.streak.count=last===y?(state.streak.count||0)+1:1;state.streak.lastDay=day;}
    save();
  }
  function topicById(c,id){for(const u of c.units)for(const t of u.topics)if(t.id===id)return {unit:u,topic:t};return null}
  function languageToggle(extraClass=''){return `<button class="ghost-btn lang-toggle ${extraClass}" data-lang-toggle aria-label="${esc(T('common.language'))}: ${state.lang==='zh'?'中文':'English'}" title="${esc(T('common.language'))}"><span class="lang-option ${state.lang==='zh'?'active':''}">中文</span><span class="lang-divider">/</span><span class="lang-option ${state.lang==='en'?'active':''}">EN</span></button>`}
  function toggleLanguage(){state.lang=state.lang==='zh'?'en':'zh';save();render();}
  function localReasonList(reasons){return reasons.map(reasonText)}

  function moduleContext(tid=REVIEW_PAGE?state.mfContext?.topic_id:state.routeParams.topicId){if(!REVIEW_PAGE&&state.route==='mindflow'&&state.mfEntryContext?.course_id===course().id)return state.mfEntryContext;const c=course(),unit=topicById(c,tid)?.unit;return {course_id:c.id,unit_id:unit?.id??null,topic_id:unit?tid:null,return_to:REVIEW_PAGE?GMFShared.safeReturn(params.get('return_to')):new URL('?course_id='+encodeURIComponent(c.id)+'#'+(unit?'topic/'+tid+'/reading':'pathway'),new URL('.',document.baseURI)).href};}
  async function jump(module,tid=REVIEW_PAGE?state.mfContext?.topic_id:state.routeParams.topicId){if(module==='mindflow'&&!REVIEW_PAGE){await route('mindflow',{page:'focus',topicId:tid});return;}if(module==='review'&&MFV3?.isFocusing())await MFV3.pauseForReview();sessionTick();await save();await LearningStore.flush();if(module!=='review'&&MFV3?.current()?.state==='Focusing')sessionStorage.setItem('gmf-mf-handoff',JSON.stringify({id:MFV3.current().session_id,at:Date.now()}));location.href=GMFShared.url(module,moduleContext(tid));}
  function appShell(content){
    const c=course(),directory=!REVIEW_PAGE&&['overview','pathway','study','review'].includes(state.route);setAccent();GMFShared.setCurrent(state);
    document.body.classList.toggle('gmf-root-no-directory',!directory);
    const sidebar=directory?`<aside id="course-directory" class="sidebar pl-directory" aria-label="课程目录" ${state.directoryCollapsed?'hidden':''}><div class="directory-head"><p class="directory-label">${U('课程目录')}</p><button class="ghost-btn directory-toggle" id="directory-hide" aria-controls="course-directory" aria-expanded="true">${U('收起目录')}</button></div><h2>${esc(c.title)}</h2><button class="nav-btn" data-route="overview">${U('总览')}</button><button class="nav-btn" data-route="review">${U('复习安排')}</button>${c.units.map(u=>`<details ${u.topics.some(t=>t.id===state.routeParams.topicId)?'open':''}><summary>${esc(u.title)}</summary>${u.topics.map(t=>`<button class="nav-btn ${t.id===state.routeParams.topicId?'active':''}" ${t.id===state.routeParams.topicId?'aria-current="page"':''} data-study="${esc(t.id)}">${esc(t.title)}</button>`).join('')}</details>`).join('')}</aside>`:'';
    return `${GMFShared.header(REVIEW_PAGE||state.route==='mindflow'?'mindflow':state.route==='progress'?'progress':'pathline',moduleContext())}${MFV3?MFV3.miniTemplate():''}<div class="shell ${directory&&state.directoryCollapsed?'directory-collapsed':''}">${sidebar}<main class="main"><header class="topbar">${directory&&state.directoryCollapsed?`<button class="ghost-btn directory-toggle" id="directory-toggle" aria-controls="course-directory" aria-expanded="${!state.directoryCollapsed}">${U(state.directoryCollapsed?'展开课程目录':'收起课程目录')}</button>`:''}<div class="current-course"><span class="tiny">${U('当前课程')}</span><b>${esc(c.title)}</b></div><div class="top-actions"><label class="target-control">${U('目标成绩')} ${F.isAP(c)?`<select id="target-score">${[1,2,3,4,5].map(n=>`<option ${String(n)===F.targetScore(c,state.targets[c.id])?'selected':''}>${n}</option>`).join('')}</select>`:`<input id="target-score" value="${esc(F.targetScore(c,state.targets[c.id]))}" maxlength="20">`}</label><button class="ghost-btn" id="course-switch">${U('切换课程')}</button></div></header><div class="page ${state.route==='study'?'focus-page':REVIEW_PAGE?'mf-page':''}">${REVIEW_PAGE?`<p class="gmf-context-copy">Physics C · ${esc(state.mfContext?.title||'')}</p>`:''}${content}</div></main></div>`;
  }
  function labelForRoute(){return U(({overview:'总览',pathway:'学习路径',review:'复习',progress:'进度',courses:'课程',settings:'设置',study:'学习路径',mindflow:'心流',assessment:'模考'})[state.route]||'学习路径');}
  function render(){
    document.body.classList.toggle('gmf-mf-route',state.route==='mindflow'&&!REVIEW_PAGE);if(state.route!=='mindflow')document.body.classList.remove('mf-immersed');
    setTheme();setLanguage();
    if(!Object.keys(allCourses()).length&&!['courses','settings'].includes(state.route))state.route='courses';
    if(!allCourses()[state.activeCourseId])state.activeCourseId=Object.keys(allCourses())[0]||physics.id;
    syncSession();
    const views={overview:renderOverview,pathway:renderPathway,review:renderReview,progress:renderProgress,courses:renderCourses,settings:renderSettings,study:renderStudy,mindflow:REVIEW_PAGE?renderMindFlow:MFV3.template,assessment:renderAssessment};
    app.innerHTML=appShell((views[state.route]||renderOverview)());
    document.querySelector('[data-gmf-lang]')?.addEventListener('click',toggleLanguage);document.querySelector('[data-gmf-theme]')?.addEventListener('click',()=>{state.theme=document.documentElement.dataset.theme==='dark'?'light':'dark';save();render();});
    bindGlobal();bindView();
    const analysisSlot=document.getElementById('as-topic-analysis');if(analysisSlot)import('./assessment/v4/analysis-ui.mjs').then(m=>m.mountAnalysis(analysisSlot)).catch(()=>{analysisSlot.textContent='知识点学习证据暂不可用。';});
    const images=document.querySelectorAll('[data-source-image]');if('IntersectionObserver' in window){const io=new IntersectionObserver(entries=>{for(const e of entries)if(e.isIntersecting){e.target.setAttribute('href',e.target.dataset.sourceImage);io.unobserve(e.target);}}, {rootMargin:'400px'});images.forEach(x=>io.observe(x));}else images.forEach(x=>x.setAttribute('href',x.dataset.sourceImage));if(state.route==='mindflow'){if(REVIEW_PAGE)bindMindFlow();else MFV3.mount(state.routeParams.page);}if(state.route==='study'&&MFV3){MFV3.attachPL(moduleContext());returnToAssessment();}if(state.route==='assessment')bindAssessment();
  }
  function returnToAssessment(){
    if(state.route!=='study')return;
    const raw=params.get('return_to');if(!raw)return;
    const target=new URL(GMFShared.safeReturn(raw));
    if(target.origin!==location.origin||!target.pathname.endsWith('/assessment/')||!target.hash.startsWith('#session/'))return;
    const box=document.getElementById('mf-pl');if(!box)return;
    const link=document.createElement('a');link.className='btn secondary';link.href=target.href;link.textContent='返回模考原会话';box.prepend(link);
  }
  function renderOnboard(){return `<div class="onboarding"><div class="onboard-language">${languageToggle()}</div><section class="onboard-card"><div class="onboard-copy">
    <div class="brand"><span class="brand-mark">P</span><span>学习路径</span></div><div class="eyebrow">${esc(T('onboard.eyebrow'))}</div><h1>${esc(T('onboard.title'))}</h1>
    <p>${esc(T('onboard.desc'))}</p>
    <div class="field" style="margin-top:24px"><label>${esc(T('onboard.name'))}</label><input id="onboard-name" value="${esc(state.name||'')}" placeholder="Serena"></div>
    <div class="onboard-actions"><button class="btn accent" id="onboard-start">${esc(T('onboard.start'))} ${icon('arrow')}</button><button class="btn secondary" id="onboard-choose">${esc(T('onboard.choose'))}</button></div>
  </div><div class="onboard-art">${[1,2,3,4].map(i=>`<div class="mini-route"><i>${i}</i><div><b>${esc(T(`onboard.step${i}.title`))}</b><span>${esc(T(`onboard.step${i}.sub`))}</span></div></div>`).join('')}</div></section></div>`}
  function bindOnboard(){
    document.getElementById('onboard-start').onclick=()=>{state.name=document.getElementById('onboard-name').value.trim()||'Serena';state.onboarded=true;state.activeCourseId='stats';ensureProgress(course());save();render()};
    document.getElementById('onboard-choose').onclick=()=>{state.name=document.getElementById('onboard-name').value.trim()||'Serena';state.onboarded=true;save();render();setTimeout(showCourseSwitch,0)};
  }
  function renderOverview(){
    const c=course(),p=progress(c),ranked=F.availableRanked(Engine,c,p,activeExamDate(c)),next=ranked[0],due=Engine.dueTopics(c,p).filter(r=>F.isReady(r.topic)),cp=F.courseCompletion(state.evidence,c),ep=F.exerciseProgress(state.evidence,c.id,exerciseIds(c));
    return `<div class="hero-row compact-hero"><div><div class="eyebrow">${U('总览')}</div><h1>${esc(c.title)}</h1></div></div>${next?`<section class="next-card card"><div><span class="pill accent">${U('下一步建议')}</span><h2>${esc(next.topic.title)}</h2><p class="muted">${U('根据目前留下的学习记录，建议从这里继续。')}</p><div class="reason-row">${evidenceBadges(c,next.topic)}</div><div class="hero-actions"><button class="btn accent" data-study="${next.topic.id}">${U('继续学习')}</button><button class="btn secondary" data-route="pathway">${U('查看学习路径')}</button></div></div></section>`:`<p class="muted">${U('这门课程还没有可打开的学习内容。')}</p>`}<div class="grid cols-2 section progress-cards">${completionCard('课程进度',cp,'topic')}${completionCard('正式习题进度',ep,'exercise')}</div>${due.length?`<section class="review-notice section"><span>${U('待复习')} · ${due.length}</span><button class="btn secondary small" data-route="review">${U('开始复习')}</button></section>`:''}${ranked.length>1?`<section class="section"><div class="section-head"><h2>${U('可继续的内容')}</h2></div><div class="card pad">${ranked.slice(1,4).map(r=>queueRow(r)).join('')}</div></section>`:''}<section class="section"><div class="section-head"><h2>${U('课程')}</h2><button class="btn secondary small" data-route="courses">${U('管理课程')}</button></div><div class="grid cols-3">${Object.values(allCourses()).map(courseCard).join('')}</div></section>`;
  }
  function greeting(){const h=new Date().getHours();return h<12?T('greeting.morning'):h<18?T('greeting.afternoon'):T('greeting.evening')}
  function queueRow(r){return `<div class="queue-row simple-queue"><div class="queue-copy"><b>${esc(r.topic.title)}</b><span>${topicStatus(course(),r.topic)}</span></div><button class="btn secondary small" data-study="${r.topic.id}">${U('继续学习')}</button></div>`;}
  function courseCard(c){const cp=F.courseCompletion(state.evidence,c);return `<button class="card course-card interactive-card" data-course="${esc(c.id)}"><div class="orb">${c.id===state.activeCourseId?'✓':'▤'}</div><h3>${esc(c.title)}</h3><p>${c.contentKind==='openstax'?'7 Units / 41 Topics':U('自定义课程')}</p><div class="meta"><span class="tiny">${U('{done} / {total} Topics · {percent}%',{done:cp.count,total:cp.total,percent:cp.percent})}</span><b>${U('目标成绩')} ${esc(F.targetScore(c,state.targets[c.id]))}</b></div>${progressBar(cp.percent,U('课程进度'))}</button>`;}
  function renderPathway(){
    const c=course(),p=progress(c);F.capReview(p,activeExamDate(c));
    return `<div class="hero-row compact-hero"><div><div class="eyebrow">${U('学习路径')}</div><h1>${esc(c.title)}</h1><p>${c.units.length} Units / ${c.units.flatMap(u=>u.topics).length} Topics</p></div></div>${c.units.map((u,unitIndex)=>{const stats=F.unitProgress(state.evidence,c.id,u);return `<section class="card path-unit"><div class="unit-head"><div class="unit-title"><span class="tiny">Unit ${c.id===physics.id?esc(u.id):unitIndex+1}</span><h3>${esc(u.title)}</h3></div><div class="unit-summary">${c.id===physics.id?`<span class="pill mcq-weight">MCQ ${F.mcqWeights[u.id]}</span>`:''}<div class="unit-progress" data-unit-progress="${u.id}"><b>${stats.percent}%</b>${progressBar(stats.percent,U('学习进度'))}<span class="tiny">${U('已学习 {done} / {total}',{done:stats.count,total:stats.total})}</span></div></div></div><div class="topic-list">${u.topics.map((t,topicIndex)=>`<button class="topic-row ${F.completed(state.evidence,c.id,t.id)?'topic-completed':''}" data-study="${t.id}" ${F.isReady(t)?'':`disabled title="${U('内容暂不可打开。')}"`}><span class="topic-index">${c.id===physics.id?esc(t.id):topicIndex+1}</span><span class="topic-main"><b>${esc(t.title.replace(new RegExp('^'+t.id.replace('.','\\.')+'\\s+'),''))}</b></span><span class="topic-signal">${topicStatus(c,t)}${MindFlowV1.derived(state.evidence,c.id,t.id,p[t.id]).latest_mf_result?`<small>${mfResult(c.id,t.id)}</small>`:''}</span><span class="chev">${F.completed(state.evidence,c.id,t.id)?'✓':F.isReady(t)?'›':''}</span></button>`).join('')}</div></section>`;}).join('')}`;
  }
  function unitMastery(u,p){return Math.round(u.topics.reduce((s,t)=>s+(p[t.id]?.mastery||0),0)/Math.max(1,u.topics.length))}
  function renderReview(){
    const c=course(),p=progress(c);F.capReview(p,activeExamDate(c));const ranked=F.availableRanked(Engine,c,p,activeExamDate(c)),due=Engine.dueTopics(c,p).filter(r=>F.isReady(r.topic)),future=ranked.filter(r=>r.state.dueAt>Date.now()).sort((a,b)=>a.state.dueAt-b.state.dueAt);
    const row=(r,isDue)=>`<div class="queue-row simple-queue"><div class="queue-copy"><b>${esc(r.topic.title)}</b><span>${isDue?U('已到期'):dueLabel(r.state.dueAt)}${MindFlowV1.derived(state.evidence,c.id,r.topic.id,p[r.topic.id]).latest_mf_result?` · ${mfResult(c.id,r.topic.id)}`:''}</span></div><button class="btn secondary small" ${MindFlowV1.blueprints[r.topic.id]?'data-mf':'data-study'}="${r.topic.id}">${U('开始复习')}</button></div>`;
    return `<div class="hero-row compact-hero"><div><div class="eyebrow">${U('复习')}</div><h1>${U('复习')}</h1><p>${U('学习过的内容，按时间回来看看。')}</p></div></div>${examCard(c)}<section class="section"><h2>${U('现在该复习')}</h2>${due.length?`<div class="card pad">${due.map(r=>row(r,true)).join('')}</div>`:`<p class="muted quiet-empty">${U('今天没有必须复习的内容。')}</p>`}</section>${future.length?`<section class="section"><h2>${U('接下来')}</h2><div class="card pad">${future.map(r=>row(r,false)).join('')}</div></section>`:''}<section class="section"><h2>${U('留下的题')}</h2>${savedExerciseRows(c)}</section><p class="tiny section">${U('想起来 → 讲清楚或应用 → 卡住就修 → 再试一次')}</p>`;
  }
  function renderProgress(){
    const c=course(),cp=F.courseCompletion(state.evidence,c),ep=F.exerciseProgress(state.evidence,c.id,exerciseIds(c)),mf=state.evidence.learning_repair,assessment=state.evidence.assessment,week=Sessions.week(state.sessions),maximum=Math.max(60,...week.map(d=>d.total)),names=['周一','周二','周三','周四','周五','周六','周日'];
    const history=c.units.flatMap(u=>u.topics).filter(t=>hasEvidence(c.id,t.id));
    return `<div class="hero-row compact-hero"><div><div class="eyebrow">${U('进度')}</div><h1>${U('学习回看')}</h1><p>${U('回看这周花在哪里。')}</p></div></div><div class="grid cols-2 progress-cards primary-progress">${completionCard('阅读完成度',cp,'topic')}${completionCard('习题完成度',ep,'exercise')}</div><section class="card pad weekly-card"><div class="section-head"><h2>${U('本周学习投入')}</h2><span class="tiny">${U('今日学习')} ${minutes(week.find(d=>d.key===F.dayKey())?.total||0)} / ${state.settings.dailyGoal} ${U('分钟')}</span></div><div class="weekly-chart">${week.map((d,i)=>`<div class="week-day ${selectedWeekDay===d.key?'selected':''}" data-week-day="${d.key}"><div class="week-column">${Object.entries(d.courses).map(([cid,totals])=>`<button class="week-segment course-color-${courseColor(cid)}" data-week-course="${esc(cid)}" data-day="${d.key}" style="height:${totals.total/maximum*100}%" aria-label="${esc(registeredCourses()[cid]?.title||(cid==='null'?U('自由学习 / 独立测评'):cid))} · ${minutes(totals.total)} ${U('分钟')}" title="${esc(registeredCourses()[cid]?.title||(cid==='null'?U('自由学习 / 独立测评'):cid))} · ${minutes(totals.total)} ${U('分钟')}\n${U('学习 {learn} · 复习 {review} · 测评 {assessment} 分钟',{learn:minutes(totals.learn),review:minutes(totals.review),assessment:minutes(totals.assessment)})}"></button>`).join('')}</div><button class="week-day-label" data-week-select="${d.key}" aria-label="${U(names[i])} · ${U('总计 {n} 分钟',{n:minutes(d.total)})}"><span>${U(names[i])}</span><b>${minutes(d.total)}</b></button></div>`).join('')}</div><div class="week-details" id="week-details" aria-live="polite">${weekDetails(week.find(d=>d.key===selectedWeekDay)||week.find(d=>d.key===F.dayKey())||week[0],selectedWeekCourse)}</div>${week.every(d=>!d.total)?`<p class="tiny">${U('打开教材或复习时，记录实际投入的时间。')}</p>`:''}</section><section class="section"><h2>${U('课程推进')}</h2><div class="process-summary"><span>${U('心流：{n} 次',{n:mf.length})}</span><span>${assessment.length?U('模考：{n} 次测评',{n:assessment.length}):U('模考：尚无')}</span></div></section><section class="section"><h2>${U('各节学习记录')}</h2><div class="card pad">${history.length?history.map(t=>`<div class="queue-row simple-queue"><div class="queue-copy"><b>${esc(t.title)}</b><span>${topicHistory(c,t)}</span></div><button class="btn secondary small" data-study="${t.id}" ${F.isReady(t)?'':'disabled'}>${U('回到教材')}</button></div>`).join(''):`<p class="muted">${U('还没有学习记录。')}</p>`}</div></section><section id="as-topic-analysis" class="section">正在读取知识点学习证据…</section>`;
  }
  function summaryStats(c,p){const arr=Object.values(p),attempts=arr.reduce((s,x)=>s+(x.attempts||0),0),correct=arr.reduce((s,x)=>s+(x.correct||0),0);return{attempts,correct,accuracy:attempts?Math.round(correct/attempts*100):0,confidence:Math.round(arr.reduce((s,x)=>s+(x.confidence||.5),0)/Math.max(1,arr.length)*100),mastered:arr.filter(x=>x.mastery>=75).length}}
  function last14Days(){const out=[],locale=state.lang==='zh'?'zh-CN':'en-US';for(let i=13;i>=0;i--){const d=new Date(Date.now()-i*86400000),key=d.toISOString().slice(0,10);let min=0;state.activity.forEach(a=>{if(new Date(a.at).toISOString().slice(0,10)===key&&a.minutes)min+=a.minutes});out.push({label:d.toLocaleDateString(locale,{month:'short',day:'numeric'}),short:d.toLocaleDateString(locale,{weekday:'narrow'}),min:Math.round(min)});}return out}
  function todayMinutes(cid){const day=F.dayKey();return Math.round(state.activity.filter(a=>a.cid===cid&&new Date(a.at).toISOString().slice(0,10)===day).reduce((s,a)=>s+(a.minutes||0),0))}
  function renderImport(){
    return `<div class="hero-row"><div><div class="eyebrow">${esc(T('import.eyebrow'))}</div><h1>${esc(T('import.title'))}</h1><p>${esc(T('import.desc'))}</p></div></div>
    <div class="grid cols-2"><section class="card import-panel"><div class="card-title"><h2>${esc(T('import.upload'))}</h2><span class="pill">${esc(T('import.localFirst'))}</span></div><div class="dropzone" id="dropzone"><div class="drop-icon">${icon('upload')}</div><h3>${esc(T('import.drop'))}</h3><p>${U('TXT · MD · CSV · JSON · HTML · 最大 30 MB')}</p><button class="btn secondary small" id="file-pick">${esc(T('import.choose'))}</button><input type="file" id="material-file" accept=".txt,.md,.csv,.json,.html,.htm" hidden></div><div id="file-status">${state.draftImport?fileStatus(state.draftImport):''}</div></section>
    <section class="card import-panel"><div class="card-title"><h2>${esc(T('import.build'))}</h2><span class="pill">${esc(T('common.custom'))}</span></div><div class="form-grid"><div class="field" style="grid-column:1/-1"><label>${esc(T('import.courseName'))}</label><input id="custom-title" placeholder="${esc(T('import.coursePlaceholder'))}" value="${esc(state.draftImport?.title||'')}"></div><div class="field"><label>${esc(T('common.target'))}</label><input id="custom-target" placeholder="A / 90% / 7.5" value="${esc(state.draftImport?.target||'A')}"></div><div class="field"><label>${esc(T('import.examDate'))}</label><input id="custom-date" type="date" value="${esc(state.draftImport?.examDate||'')}"></div><div class="field" style="grid-column:1/-1"><label>${esc(T('import.paste'))}</label><textarea id="custom-text" placeholder="${esc(T('import.pastePlaceholder'))}">${esc(state.draftImport?.text||'')}</textarea></div></div><div class="hero-actions"><button class="btn accent" id="generate-course">${esc(T('import.generate'))}</button><button class="btn secondary" id="clear-import">${esc(T('import.clear'))}</button></div></section></div>
    `;
  }
  function fileStatus(d){const source=d.source==='browser'?L('browser','浏览器'):d.source==='local parser'?L('local parser','本地解析器'):(d.source||L('browser','浏览器'));return `<div class="file-status"><span>${d.loading?'<span class="spinner"></span>':'✓'}</span><span><b>${esc(d.fileName||T('import.materialLoaded'))}</b><span>${d.loading?esc(T('import.reading')):esc(T('import.characters',{n:(d.text||'').length.toLocaleString(state.lang==='zh'?'zh-CN':'en-US'),source}))}</span></span></div>`}
  function renderSettings(){
    return `<div class="hero-row"><div><div class="eyebrow">${esc(T('settings.eyebrow'))}</div><h1>${esc(T('settings.title'))}</h1><p>${esc(T('settings.desc'))}</p></div></div>
    <div class="grid cols-2"><section class="card pad"><div class="card-title"><h2>${esc(T('settings.study'))}</h2></div><div class="settings-list">
      <div class="setting-row"><div><b>${esc(T('settings.dailyGoal'))}</b><p>${esc(T('settings.dailyGoalDesc'))}</p></div><select id="daily-goal"><option ${state.settings.dailyGoal===20?'selected':''}>20</option><option ${state.settings.dailyGoal===35?'selected':''}>35</option><option ${state.settings.dailyGoal===50?'selected':''}>50</option><option ${state.settings.dailyGoal===75?'selected':''}>75</option></select></div>
      <div class="setting-row"><div><b>${esc(T('common.theme'))}</b><p>${esc(T('settings.themeDesc'))}</p></div><select id="theme-select"><option value="system" ${state.theme==='system'?'selected':''}>${esc(T('common.system'))}</option><option value="light" ${state.theme==='light'?'selected':''}>${esc(T('common.light'))}</option><option value="dark" ${state.theme==='dark'?'selected':''}>${esc(T('common.dark'))}</option></select></div>
      <div class="setting-row"><div><b>${esc(T('common.language'))}</b><p>${U('界面立即切换；教材保留原文。')}</p></div><select id="language-select"><option value="zh" ${state.lang==='zh'?'selected':''}>中文</option><option value="en" ${state.lang==='en'?'selected':''}>English</option></select></div>
      <div class="setting-row"><div><b>${esc(T('settings.examDate'))}</b><p>${U('考试临近时，复习间隔缩短，最晚不超过考试日。')}</p></div><input id="exam-date" type="date" value="${esc(activeExamDate(course()))}"></div>
    </div></section>
    <section class="card pad"><div class="card-title"><h2>${esc(T('settings.data'))}</h2><span class="pill">${esc(T('common.local'))}</span></div><p class="muted" style="font-size:12px;line-height:1.55">${U('学习记录、课程和设置保存在当前浏览器中，可随时导出备份。')}</p><div class="hero-actions"><button class="btn secondary" id="export-state">${icon('download')} ${esc(T('settings.export'))}</button><button class="btn secondary" id="import-state-btn">${icon('upload')} ${esc(T('settings.import'))}</button><button class="btn danger" id="reset-state">${esc(T('settings.reset'))}</button></div><div class="divider"></div><div id="install-wrap">${deferredInstall?`<button class="btn accent" id="install-app">${esc(T('settings.install'))}</button>`:`<span class="tiny">${esc(T('settings.installHint'))}</span>`}</div></section></div>${renderOffline()}`;
  }
  function renderStudy(){
    const c=course(),found=topicById(c,state.routeParams.topicId);if(!found||!F.isReady(found.topic))return `<p class="muted">${U('这部分内容暂不可用。')}</p><button class="btn secondary" data-route="pathway">${U('返回学习路径')}</button>`;
    const t=found.topic,toc=c.contentKind==='openstax'?window.PathlineContent.navigation(t.id):`<button data-anchor="learning-goals">${U('学习目标')}</button><button data-anchor="imported-content">${U('导入正文')}</button>`;
    const content=c.contentKind==='openstax'?window.PathlineContent.topic(t.id):`<section id="learning-goals"><h2>${U('学习目标')}</h2><ul>${tObjectives(t).map(x=>`<li>${esc(x)}</li>`).join('')}</ul></section><section id="imported-content"><h2>${esc(t.title)}</h2><p>${esc(t.summary)}</p><p>${esc(t.excerpt||'')}</p></section>`;
    return `<div class="topic-heading"><div><p class="tiny">${U('学习路径')} / Unit ${c.id===physics.id?esc(found.unit.id):c.units.indexOf(found.unit)+1}</p><h1>${esc(t.title)}</h1></div><div class="topic-toolbar"><button class="btn secondary small" id="reading-fullscreen">${U('全屏阅读')}</button><button class="btn secondary small" data-route="pathway">${U('返回学习路径')}</button></div></div><div id="mf-pl" class="mf-pl"></div><div class="topic-frame ${state.tocCollapsed?'toc-collapsed':''}"><nav class="topic-toc" id="topic-toc" aria-label="${U('本节目录')}"><div class="directory-head"><h2>${U('本节目录')}</h2><button class="ghost-btn" id="toc-hide" aria-controls="topic-toc" aria-expanded="true">${U('收起目录')}</button></div>${toc}<h3>${U('课程其他知识点')}</h3>${c.units.map(u=>`<details ${u.id===found.unit.id?'open':''}><summary>Unit ${c.id===physics.id?esc(u.id):c.units.indexOf(u)+1} · ${esc(u.title)}</summary>${u.topics.map(x=>`<button data-study="${x.id}" ${F.isReady(x)?'':'disabled'} ${x.id===t.id?'aria-current="page"':''}>${esc(x.title)}${F.completed(state.evidence,c.id,x.id)?' ✓':''}</button>`).join('')}</details>`).join('')}</nav><div class="toc-divider"><button id="toc-toggle" aria-controls="topic-toc" aria-expanded="${!state.tocCollapsed}" title="${U(state.tocCollapsed?'显示目录':'收起目录')}">${U(state.tocCollapsed?'显示目录':'收起目录')}</button></div><button class="btn secondary small fullscreen-exit" id="exit-reading-fullscreen" aria-label="${U('退出全屏阅读')}">${U('退出全屏 · Esc')}</button><article class="topic-body" id="topic-body" tabindex="0">${content}<section class="content-actions"><button class="btn secondary" data-read="${t.id}" aria-pressed="false">${U('记录本节已学习')}</button><button class="btn secondary" data-mf="${t.id}">${U('心流')}</button><p class="tiny">${U('阅读和练习标记不代表掌握度。')}</p></section></article></div>`;
  }
  function startQuiz(topicId){startMindFlow(topicId);}
  function renderQuiz(){
    const c=course(),found=topicById(c,state.routeParams.topicId);if(!found)return '<div></div>';const topic=found.topic;
    if(!quiz||quiz.topicId!==topic.id)quiz={topicId:topic.id,index:0,answers:[],selected:null,confidence:.65,checked:false};
    if(quiz.index>=topic.questions.length)return renderQuizResult(c,topic);
    const rawQ=topic.questions[quiz.index],q=tQuestion(topic,quiz.index,rawQ),letters='ABCD';
    return `<div class="quiz-shell"><div class="quiz-progress">${topic.questions.map((_,i)=>`<i class="${i<quiz.index?'done':''}"></i>`).join('')}</div><section class="card question-card"><div class="eyebrow">${esc(T('quiz.label',{i:quiz.index+1,n:topic.questions.length}))}</div><h2>${esc(q.prompt)}</h2><div class="choices">${q.choices.map((x,i)=>{let cls='choice';if(quiz.selected===i)cls+=' selected';if(quiz.checked){if(i===q.answer)cls+=' correct';else if(i===quiz.selected)cls+=' wrong'}return `<button class="${cls}" data-choice="${i}" ${quiz.checked?'disabled':''}><span class="choice-key">${letters[i]}</span><span>${esc(x)}</span></button>`}).join('')}</div><div class="confidence"><label><span>${esc(T('quiz.confidence'))}</span><b id="confidence-label">${Math.round(quiz.confidence*100)}%</b></label><input id="confidence-range" type="range" min="0" max="100" value="${Math.round(quiz.confidence*100)}" ${quiz.checked?'disabled':''}></div>${quiz.checked?`<div class="feedback ${quiz.selected===q.answer?'good':'bad'}"><b>${esc(quiz.selected===q.answer?T('quiz.correct'):T('quiz.notQuite'))}</b> ${esc(q.explanation)}</div>`:''}<div class="quiz-actions"><button class="btn secondary" data-study="${topic.id}">${icon('back')} ${esc(T('common.topic'))}</button><button class="btn accent" id="quiz-next" ${quiz.selected===null?'disabled':''}>${esc(quiz.checked?(quiz.index===topic.questions.length-1?T('quiz.finish'):T('quiz.next')):T('quiz.check'))}</button></div></section></div>`;
  }
  function renderQuizResult(c,topic){const latest=quiz.answers,correct=latest.filter(a=>a.correct).length,score=Math.round(correct/Math.max(1,latest.length)*100),s=progress(c)[topic.id],heading=score===100?T('quiz.resultPerfect'):score>=60?T('quiz.resultOkay'):T('quiz.resultRepair');return `<div class="quiz-shell"><section class="card quiz-result"><div class="big">${score}%</div><h2>${esc(heading)}</h2><p>${esc(T('quiz.resultDesc',{m:s.mastery,when:relDue(s.dueAt)}))}</p><div class="hero-actions" style="justify-content:center"><button class="btn accent" data-route="overview">${esc(T('quiz.backOverview'))}</button><button class="btn secondary" data-study="${topic.id}">${esc(T('quiz.reviewTopic'))}</button></div></section></div>`}

  function bindLanguageToggles(){document.querySelectorAll('[data-lang-toggle]').forEach(b=>b.onclick=toggleLanguage)}
  function bindGlobal(){
    for(const id of ['directory-toggle','directory-hide'])document.getElementById(id)?.addEventListener('click',()=>{state.directoryCollapsed=!state.directoryCollapsed;save();render();});
    if(!REVIEW_PAGE)document.querySelectorAll('.gmf-global a').forEach(a=>a.addEventListener('click',e=>{const u=new URL(a.href);if(u.pathname===location.pathname&&u.hash){if(e.defaultPrevented)return;e.preventDefault();if(u.hash.startsWith('#mindflow/')&&state.route!=='mindflow')state.mfEntryContext=moduleContext();if(u.hash===location.hash)return;location.hash=u.hash;}}));
    document.querySelectorAll('[data-route]').forEach(b=>b.onclick=()=>route(b.dataset.route));document.querySelectorAll('[data-study]').forEach(b=>b.onclick=()=>route('study',{topicId:b.dataset.study}));
    document.querySelectorAll('[data-mf]').forEach(b=>{if(topicById(course(),b.dataset.mf))b.onclick=()=>startMindFlow(b.dataset.mf);});document.querySelectorAll('[data-course]').forEach(b=>b.onclick=()=>{state.activeCourseId=b.dataset.course;route('overview');});
    document.getElementById('target-score')?.addEventListener('change',e=>{state.targets[course().id]=F.targetScore(course(),e.target.value.trim());save();render();});
    document.getElementById('course-switch')?.addEventListener('click',showCourseSwitch);document.querySelectorAll('[data-lang-toggle]').forEach(b=>b.onclick=toggleLanguage);
    document.getElementById('theme-toggle')?.addEventListener('click',()=>{state.theme=document.documentElement.dataset.theme==='dark'?'light':'dark';save();render();});
  }
  function bindView(){
    if(state.route==='progress'){document.querySelectorAll('[data-week-day]').forEach(b=>b.onmouseenter=()=>selectWeekDay(b.dataset.weekDay));document.querySelectorAll('[data-week-select]').forEach(b=>{b.onclick=b.onfocus=b.onmouseenter=()=>selectWeekDay(b.dataset.weekSelect);});document.querySelectorAll('[data-week-course]').forEach(b=>{b.onclick=b.onmouseenter=b.onfocus=()=>selectWeekDay(b.dataset.day,b.dataset.weekCourse);});}
    document.querySelectorAll('[data-open-saved]').forEach(b=>b.onclick=()=>route('study',{topicId:b.dataset.topic,section:'exercises',exerciseId:b.dataset.openSaved}));
    if(state.route==='courses'){bindImport();document.querySelectorAll('[data-delete-course]').forEach(b=>b.onclick=()=>confirmDeleteCourse(b.dataset.deleteCourse));document.querySelectorAll('[data-restore-course]').forEach(b=>b.onclick=()=>{state.deletedCourseIds=state.deletedCourseIds.filter(id=>id!==b.dataset.restoreCourse);save();render();toast(U('课程和学习记录已恢复。'));});}if(state.route==='settings')bindSettings();
    if(state.route==='study'){
      document.getElementById('reading-fullscreen')?.addEventListener('click',()=>{readingScroll=document.getElementById('topic-body').scrollTop;document.querySelector('.topic-frame').classList.add('reading-fullscreen');document.getElementById('exit-reading-fullscreen').focus();});
      document.getElementById('exit-reading-fullscreen')?.addEventListener('click',exitReadingFullscreen);
      for(const id of ['toc-toggle','toc-hide'])document.getElementById(id)?.addEventListener('click',()=>{state.tocCollapsed=!state.tocCollapsed;document.querySelector('.topic-frame').classList.toggle('toc-collapsed',state.tocCollapsed);const button=document.getElementById('toc-toggle');button.textContent=button.title=U(state.tocCollapsed?'显示目录':'收起目录');button.setAttribute('aria-expanded',String(!state.tocCollapsed));save();});
      document.querySelectorAll('[data-anchor]').forEach(b=>b.onclick=()=>{const pane=document.getElementById('topic-body'),target=pane.querySelector(`#${CSS.escape(b.dataset.anchor)}`);if(target)pane.scrollTo({top:pane.scrollTop+target.getBoundingClientRect().top-pane.getBoundingClientRect().top,behavior:'smooth'});});
      document.querySelectorAll('[data-jump-exercise]').forEach(b=>b.onclick=()=>{const pane=document.getElementById('topic-body'),target=pane.querySelector(`[data-exercise-id="${CSS.escape(b.dataset.jumpExercise)}"]`);if(target){target.open=true;pane.scrollTo({top:pane.scrollTop+target.getBoundingClientRect().top-pane.getBoundingClientRect().top,behavior:'smooth'});}});
      document.querySelectorAll('[data-read]').forEach(b=>{paintReadButton(b);b.onclick=()=>{const c=course(),active=F.toggleCompletion(state.evidence,progress(c),{event_id:crypto.randomUUID(),course_id:c.id,topic_id:b.dataset.read});F.capReview(progress(c),activeExamDate(c));save();paintReadButton(b);toast(U(active?'本节已标记为已学习。':'已取消本节的已学习标记。'));};});
      document.querySelectorAll('[data-exposure-exercise]').forEach(b=>{paintExerciseButton(b);b.onclick=()=>{const c=course(),tid=state.routeParams.topicId;const recorded=F.togglePractice(state.evidence,progress(c),{event_id:crypto.randomUUID(),course_id:c.id,topic_id:tid,exercise_id:b.dataset.exposureExercise});F.capReview(progress(c),activeExamDate(c));save();document.querySelectorAll('[data-exposure-exercise]').forEach(paintExerciseButton);toast(U(recorded?'本题已标记为已完成。':'已取消本题的完成标记。'));};});
      document.querySelectorAll('[data-save-exercise]').forEach(b=>{paintSavedButton(b);b.onclick=()=>{const cid=course().id,id=b.dataset.saveExercise,active=!state.savedExercises.some(x=>x.course_id===cid&&x.exercise_id===id);state.savedExercises=state.savedExercises.filter(x=>!(x.course_id===cid&&x.exercise_id===id));if(active)state.savedExercises.push({course_id:cid,topic_id:state.routeParams.topicId,exercise_id:id,saved_at:new Date().toISOString()});save();document.querySelectorAll('[data-save-exercise]').forEach(paintSavedButton);toast(U(active?'已留下这道题。':'已取消留下。'));};});
      if(state.routeParams.exerciseId){const button=document.querySelector(`[data-jump-exercise="${CSS.escape(state.routeParams.exerciseId)}"]`),target=document.querySelector(`#exercises [data-exercise-id="${CSS.escape(state.routeParams.exerciseId)}"]`);if(button)button.click();else if(target){target.open=true;target.scrollIntoView({block:'start'});}}
      else if(state.routeParams.section==='exercises')document.querySelector('[data-anchor="exercises"]')?.click();
    }
    document.getElementById('return-pl')?.addEventListener('click',()=>route('overview'));
  }
  function paintExerciseButton(button){
    const recorded=F.practiceComplete(state.evidence,course().id,button.dataset.exposureExercise);
    button.classList.toggle('is-recorded',recorded);button.setAttribute('aria-pressed',String(recorded));button.textContent=U(recorded?'✓ 已完成':'记录已完成');
  }
  function exitReadingFullscreen(){
    const frame=document.querySelector('.reading-fullscreen');if(!frame)return;
    frame.classList.remove('reading-fullscreen');document.getElementById('topic-body').scrollTop=readingScroll;document.getElementById('reading-fullscreen')?.focus();
  }
  document.addEventListener('keydown',e=>{if(e.key==='Escape')exitReadingFullscreen();});
  function confirmDeleteCourse(id){
    const c=allCourses()[id];if(!c)return;
    const dialog=document.createElement('dialog');dialog.className='modal course-delete-dialog';dialog.setAttribute('aria-labelledby','course-delete-title');
    dialog.innerHTML=`<h2 id="course-delete-title">${U('删除这门课程？')}</h2><p><b>${esc(c.title)}</b></p><p>${U('课程将从列表移除。学习记录保留，可以在“已删除课程”中恢复。')}</p><div class="modal-actions"><button class="btn secondary" id="cancel-course-delete">${U('取消')}</button><button class="btn danger" id="confirm-course-delete">${U('确认删除')}</button></div>`;
    document.body.append(dialog);dialog.showModal();dialog.querySelector('#cancel-course-delete').focus();
    dialog.querySelector('#cancel-course-delete').onclick=()=>dialog.close();dialog.addEventListener('close',()=>dialog.remove());
    dialog.querySelector('#confirm-course-delete').onclick=()=>{state.deletedCourseIds.push(id);if(state.mfContext?.course_id===id)state.mfContext=null;state.activeCourseId=Object.keys(allCourses())[0]||physics.id;save();dialog.close();route('courses');toast(U('课程已删除，可在下方恢复。'));};
  }
  function showCourseSwitch(){
    document.body.insertAdjacentHTML('beforeend',`<div class="modal-wrap" id="course-modal" role="dialog" aria-modal="true" aria-labelledby="switch-title"><div class="modal"><div class="card-title"><h2 id="switch-title">${U('切换课程')}</h2><button class="icon-btn" id="close-modal" aria-label="${U('关闭')}">×</button></div><p>${U('各课程单独保留学习记录和复习时间。')}</p><div class="grid cols-2">${Object.values(allCourses()).map(courseCard).join('')}</div><div class="modal-actions"><button class="btn secondary" id="open-course-manager">${U('管理 / 导入课程')}</button></div></div></div>`);
    const modal=document.getElementById('course-modal');document.getElementById('close-modal').onclick=()=>modal.remove();modal.onclick=e=>{if(e.target===modal)modal.remove();};modal.onkeydown=e=>{if(e.key==='Escape')modal.remove();};modal.querySelectorAll('[data-course]').forEach(b=>b.onclick=()=>{state.activeCourseId=b.dataset.course;modal.remove();route('overview');});document.getElementById('open-course-manager').onclick=()=>{modal.remove();route('courses');};document.getElementById('close-modal').focus();
  }
  function bindImport(){
    const input=document.getElementById('material-file'),zone=document.getElementById('dropzone');document.getElementById('file-pick').onclick=()=>input.click();input.onchange=()=>input.files[0]&&handleFile(input.files[0]);
    ['dragenter','dragover'].forEach(ev=>zone.addEventListener(ev,e=>{e.preventDefault();zone.classList.add('drag')}));['dragleave','drop'].forEach(ev=>zone.addEventListener(ev,e=>{e.preventDefault();zone.classList.remove('drag')}));zone.addEventListener('drop',e=>e.dataTransfer.files[0]&&handleFile(e.dataTransfer.files[0]));
    document.getElementById('clear-import').onclick=()=>{state.draftImport=null;save();render()};
    document.getElementById('generate-course').onclick=()=>{
      const title=document.getElementById('custom-title').value.trim(),target=document.getElementById('custom-target').value.trim()||'A',examDate=document.getElementById('custom-date').value,text=document.getElementById('custom-text').value.trim()||state.draftImport?.text||'';
      if(text.length<80){toast(T('toast.moreMaterial'));return}
      const c=Parsers.buildCustomCourse(title||state.draftImport?.fileName?.replace(/\.[^.]+$/,'')||L('Imported Course','导入课程'),text);c.contentKind='imported';c.units.forEach(u=>u.topics.forEach(t=>t.contentKind='imported'));c.targetDefault=F.targetScore(c,target);c.exam=examDate||L('Custom date','自定义日期');state.customCourses.push(c);state.examDates[c.id]=examDate||'';state.activeCourseId=c.id;ensureProgress(c);state.draftImport=null;recordActivity('course_created',c.id,null,{});save();toast(T('toast.pathGenerated'));route('pathway');
    };
  }
  function localizedParserError(err){const msg=String(err?.message||err||'');if(/included local server/i.test(msg))return T('parser.server');if(/PDF support/i.test(msg))return T('parser.pdfDep');if(/Unsupported file/i.test(msg))return T('parser.unsupported');if(/uploaded file is empty/i.test(msg))return T('parser.empty');if(/30 MB/i.test(msg))return T('parser.large');if(/No readable text/i.test(msg))return T('parser.noText');return msg}
  async function handleFile(file){
    state.draftImport={fileName:file.name,loading:true,text:'',source:'',title:file.name.replace(/\.[^.]+$/,''),target:'A',examDate:''};save();render();
    try{const out=await Parsers.parseFile(file);state.draftImport={...state.draftImport,loading:false,text:out.text,source:out.source};save();render();const ta=document.getElementById('custom-text');if(ta)ta.value=out.text;toast(T('toast.readFile',{name:file.name}))}
    catch(e){state.draftImport={...state.draftImport,loading:false};save();render();toast(localizedParserError(e))}
  }
  function bindSettings(){
    bindOffline();
    document.getElementById('daily-goal').onchange=e=>{state.settings.dailyGoal=+e.target.value;save();toast(T('toast.goalUpdated'))};
    document.getElementById('theme-select').onchange=e=>{state.theme=e.target.value;save();render()};
    document.getElementById('language-select').onchange=e=>{state.lang=e.target.value==='en'?'en':'zh';save();render()};
    document.getElementById('exam-date').onchange=async e=>{sessionTick();state.examDates[state.activeCourseId]=e.target.value;F.capReview(progress(course()),activeExamDate(course()));await save();GMFShared.refreshCountdown();toast(U('考试日期已保存。'))};
    document.getElementById('export-state').onclick=exportState;document.getElementById('import-state-btn').onclick=()=>stateImport.click();
    document.getElementById('reset-state').onclick=confirmReset;document.getElementById('install-app')?.addEventListener('click',async()=>{if(deferredInstall){deferredInstall.prompt();await deferredInstall.userChoice;deferredInstall=null;render()}});
  }
  async function exportState(){await save();await LearningStore.flush();const blob=new Blob([JSON.stringify(await LearningStore.exportAll(),null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`pathline-backup-${new Date().toISOString().slice(0,10)}.json`;a.click();URL.revokeObjectURL(url);toast(T('toast.backupExported'))}
  function confirmReset(){document.body.insertAdjacentHTML('beforeend',`<div class="modal-wrap" id="reset-modal"><div class="modal"><h2>${esc(T('modal.resetTitle'))}</h2><p>${esc(T('modal.resetDesc'))}</p><div class="modal-actions"><button class="btn secondary" id="cancel-reset">${esc(T('common.cancel'))}</button><button class="btn danger" id="confirm-reset">${esc(T('modal.resetEverything'))}</button></div></div></div>`);const m=document.getElementById('reset-modal');document.getElementById('cancel-reset').onclick=()=>m.remove();document.getElementById('confirm-reset').onclick=()=>{LearningStore.reset().then(()=>{localStorage.removeItem(KEY);state=clone(DEFAULT);save();m.remove();render();})}}
  function bindQuiz(){
    document.querySelectorAll('[data-choice]').forEach(b=>b.onclick=()=>{quiz.selected=+b.dataset.choice;render()});const r=document.getElementById('confidence-range');if(r)r.oninput=e=>{quiz.confidence=+e.target.value/100;document.getElementById('confidence-label').textContent=`${e.target.value}%`};
    document.getElementById('quiz-next')?.addEventListener('click',()=>{
      const c=course(),topic=topicById(c,quiz.topicId).topic,q=topic.questions[quiz.index];
      if(!quiz.checked){quiz.checked=true;const correct=quiz.selected===q.answer;quiz.answers.push({correct,confidence:quiz.confidence});const p=progress(c);p[topic.id]=Engine.recordAnswer(p[topic.id],correct,quiz.confidence);recordActivity('answer',c.id,topic.id,{correct,minutes:Math.max(2,Math.round(topic.minutes/Math.max(1,topic.questions.length)))});save();render()}
      else{quiz.index++;quiz.selected=null;quiz.confidence=.65;quiz.checked=false;render()}
    });
  }
  stateImport.addEventListener('change',async()=>{const f=stateImport.files[0];if(!f)return;try{const incoming=JSON.parse(await f.text());if(incoming.schema==='gmf-backup/1'){const r=await LearningStore.restoreBackup(incoming);toast(`导入 ${r.inserted} 条；保留现有 ${r.kept} 条。请刷新。`);return;}state=migrate({...clone(DEFAULT),...incoming});save();render();toast(T('toast.backupImported'))}catch{toast(T('toast.backupFailed'))}stateImport.value=''});
  addEventListener('beforeinstallprompt',e=>{e.preventDefault();deferredInstall=e;if(state.route==='settings')render()});
  addEventListener('keydown',e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==='k'){e.preventDefault();showCourseSwitch()}});
  if('serviceWorker'in navigator)navigator.serviceWorker.register('./sw.js').catch(()=>{});
  matchMedia('(prefers-color-scheme: dark)').addEventListener?.('change',()=>{if(state.theme==='system')setTheme()});
  function renderCourses(){return `<div class="hero-row compact-hero"><div><div class="eyebrow">${U('课程')}</div><h1>${U('管理你的课程。')}</h1><p>${U('每门课程单独保存目标、考试日期和学习记录。')}</p></div></div><div class="grid cols-3">${Object.values(allCourses()).map(c=>`<section class="managed-course">${courseCard(c)}<button class="btn secondary small delete-course" data-delete-course="${esc(c.id)}">${U('删除课程')}</button></section>`).join('')||`<p class="muted">${U('暂无课程。可以恢复课程或导入自己的材料。')}</p>`}</div><p class="section"><a class="ghost-btn" href="#settings">${U('教材与离线')}</a></p>${state.deletedCourseIds.length?`<section class="card pad section"><h2>${U('已删除课程')}</h2><p class="tiny">${U('学习记录保留，恢复后可以继续学习。')}</p>${state.deletedCourseIds.filter(id=>registeredCourses()[id]).map(id=>`<div class="queue-row simple-queue"><b>${esc(registeredCourses()[id].title)}</b><button class="btn secondary small" data-restore-course="${esc(id)}">${U('恢复课程')}</button></div>`).join('')}</section>`:''}<details class="section course-import"><summary>${U('上传 / 导入课程材料')}</summary><p class="tiny">${U('文本文件和粘贴材料可用。暂不支持 PDF、DOCX、PPTX 导入。')}</p>${renderImport()}</details>`;}
  function reasonList(row){
    const labels={'low mastery':hasEvidence(course().id,row.topic.id)?'尚无独立测评证据':'尚无学习证据','review due':'复习到期','memory decay':'遗忘风险上升','unlocks later topics':'有助于后续 Topic','low confidence':'信心证据不足','prerequisites not ready':'前置知识待检查','best next gain':'当前推荐'};
    return [...row.reasons.map(x=>labels[x]||x),...(row.state.lastEvidenceReason?[row.state.lastEvidenceReason]:[])];
  }
  function hasEvidence(cid,tid){const e=F.topicEvidence(state.evidence,cid,tid);return e.exposure.length>0||e.learning.length>0||e.assessment.length>0||state.evidence.practice.some(x=>x.course_id===cid&&x.topic_id===tid);}
  function evidenceLabel(cid,tid){const e=F.topicEvidence(state.evidence,cid,tid);return e.learning.length?`最近巩固 ${fmtDate(Date.parse(e.learning.at(-1).completed_at))} · 掌握度待测评`:e.exposure.length?'最近学习 · 掌握度待测评':'尚无证据';}
  function expose(tid,action,extra={}){const c=course();F.recordExposure(state.evidence,progress(c),{event_id:crypto.randomUUID(),course_id:c.id,topic_id:tid,action,...extra});save();}
  function recentEvidence(cid){const e=state.evidence.learning_repair.filter(x=>x.course_id===cid).at(-1);return e?`<section class="card pad section"><h2>最近一次 Mind Flow 记录</h2><p><b>Topic ${esc(e.topic_id)}</b> · ${e.retrieval_attempts} 次提取 · ${e.retry_count} 次重试 · ${e.hint_usage} 次提示 · ${e.repair_steps.length} 项修正</p><p class="tiny">${e.successful_retrievals} 次自检成功；${e.completion?'本轮已完成':'本轮结束，仍有待办'}。仅表示学习过程，掌握度未增加。</p><p class="muted">${esc(progress(course())[e.topic_id]?.lastEvidenceReason||'本次没有新增提取、提示或修正行为，复习时间保持原状。')}</p></section>`:'';}
  function renderOffline(){return `<section class="card pad section" id="offline-textbook"><h2>${U('教材与离线')}</h2><p>${esc(window.PathlineTextbook.course.title||'AP Physics C: Mechanics')}</p><p class="tiny">${U('离线教材保存在当前浏览器；学习记录单独保存。')}</p><p class="tiny">${U('资源版本')} ${esc(ContentRuntime.manifest.resource_version)}</p><div class="offline-controls"><label>${U('下载范围')} <select id="download-unit"><option value="">${U('整门课程')}</option>${window.PathlineTextbook.course.units.map(u=>`<option value="${esc(u.unit_id)}">Unit ${esc(u.unit_id)} · ${esc(u.title)}</option>`).join('')}</select></label><div class="mf-actions"><button class="btn accent" id="download-course">${U('下载 / 继续下载')}</button><button class="btn secondary" id="pause-course" disabled>${U('暂停下载')}</button><button class="ghost-btn" id="check-course">${U('检查完整性')}</button></div></div><progress id="offline-progress" max="1" value="0" aria-label="${U('下载进度')}"></progress><p id="offline-status" role="status" aria-live="polite"></p><details id="offline-errors" hidden><summary>${U('失败资源')}</summary><ul></ul></details><div class="mf-actions"><button class="ghost-btn" id="remove-course-cache">${U('删除课程离线缓存')}</button></div><hr><h3>${U('原教材 PDF 文件')}</h3><p class="tiny">${U('导出真实 PDF 文件到下载目录，不代表已在浏览器中下载离线教材。')}</p><button class="btn secondary" id="download-pdf">${U('导出原教材 PDF')}</button><p class="tiny">OpenStax / Rice University · University Physics Volume 1 · CC BY-NC-SA 4.0. ${U('保留原图署名；仅管理现有教材，不新增公开分发资源。')}</p><hr><div id="practice-library" role="region" aria-label="私人练习册下载"></div></section>`;}
  function bindOffline(){
    const get=id=>document.getElementById(id);if(!get('download-course'))return;
    import('./practice-library.mjs').then(m=>m.bindLibrarySettings()).catch(e=>{get('practice-library').textContent=e.message;});
    const scope=()=>get('download-unit').value||null;
    const setStatus=text=>{if(get('offline-status'))get('offline-status').textContent=text;};
    const lock=on=>{for(const id of ['download-course','download-unit','check-course','remove-course-cache','download-pdf'])if(get(id))get(id).disabled=on;if(get('pause-course'))get('pause-course').disabled=!on;};
    const progress=(done,total,info={})=>{if(!get('offline-progress'))return;get('offline-progress').max=total;get('offline-progress').value=done;setStatus(U('已校验 {done} / {total} 个资源，失败 {failed} 个',{done,total,failed:info.failed||0}));};
    async function check(){lock(true);setStatus(U('正在核对真实资源清单…'));try{const value=await ContentRuntime.status(scope());progress(value.verified,value.total);setStatus(U(value.complete?'已完整下载，可离线阅读。':'已保存 {done} / {total} 个资源，可继续下载。',{done:value.verified,total:value.total}));}catch(error){setStatus(U('检查失败，请重试。')+' '+error.message);}finally{lock(false);}}
    get('download-unit').onchange=check;get('check-course').onclick=check;
    get('download-course').onclick=async()=>{lock(true);get('offline-errors').hidden=true;try{await navigator.serviceWorker?.ready;await ContentRuntime.download(progress,scope());setStatus(U('已完整下载，可离线阅读。'));}catch(error){setStatus(U(error.name==='AbortError'?'已暂停，已校验资源保留。':'下载未完成，请联网后点击“下载 / 继续下载”重试。'));if(error.failed&&get('offline-errors')){get('offline-errors').hidden=false;get('offline-errors').querySelector('ul').innerHTML=error.failed.map(path=>`<li>${esc(path)}</li>`).join('');}}finally{lock(false);}};
    get('pause-course').onclick=()=>ContentRuntime.pause();
    get('download-pdf').onclick=async()=>{lock(true);try{await ContentRuntime.downloadPDF(progress);setStatus(U('PDF 已交给浏览器保存，请查看下载列表。'));}catch(error){setStatus(U(error.name==='AbortError'?'已暂停，已校验资源保留。':'PDF 导出失败，请重试。')+' '+error.message);}finally{lock(false);}};
    get('remove-course-cache').onclick=async()=>{lock(true);try{await ContentRuntime.remove();get('offline-progress').value=0;setStatus(U('离线缓存已删除，学习记录保留。'));}catch(error){setStatus(error.message);}finally{lock(false);}};
    check();
  }
  function mfResult(cid,tid){const result=MindFlowV1.derived(state.evidence,cid,tid,state.progress[cid]?.[tid]).latest_mf_result;return U({'independent_success':'独立完成','repaired_success':'修正后完成','unresolved':'仍需复习'}[result]||'历史学习记录');}
  async function startMindFlow(tid){
    if(!REVIEW_PAGE){await jump('mindflow',tid);return;}
    const c=course(),found=topicById(c,tid);if(c.id!==physics.id||!found||!MindFlowV1.blueprints[tid]){toast(U('本节心流 正在准备'));return;}
    const k=c.id+'|'+tid,existing=state.mfRuns[k];
    if(!existing||existing.final_state){const context={session_id:crypto.randomUUID(),course_id:c.id,unit_id:window.PathlineTextbook.course.units.find(u=>u.topic_refs.includes(tid)).unit_id,topic_id:tid,title:found.topic.title,started_at:new Date().toISOString(),lang:state.lang};state.mfRuns[k]=MindFlowV1.create(context);}
    state.mfContext=state.mfRuns[k].context;await route('mindflow',{topicId:tid});
  }
  function renderMindFlow(){
    const run=currentMF(),ctx=run?.context;
    if(!ctx||ctx.course_id!==course().id)return `<div class="hero-row compact-hero"><h1>Mind Flow</h1><p>${U('先想起来，卡住就修，再独立试一次。')}</p></div><div class="grid cols-3">${Object.keys(MindFlowV1.blueprints).map(tid=>`<button class="card course-card interactive-card" data-mf="${tid}" ${course().id===physics.id?'':'disabled'}><h2>${esc(topicById(physics,tid).topic.title)}</h2><p>${U('开始一轮巩固')}</p></button>`).join('')}</div>`;
    const b=MindFlowV1.blueprints[ctx.topic_id],step=run.stage==='recall'?0:run.stage==='application'?1:run.stage==='repair'?2:3;
    const header=`<div class="mf-context"><button class="ghost-btn" id="mf-exit">${U('返回 Pathline')}</button></div>`;
    if(run.final_state)return `${header}<section class="card mf-task"><h1>${mfResult(ctx.course_id,ctx.topic_id)}</h1><p>${U(run.final_state==='unresolved'?'这一轮先到这里，已安排更早复习。':'这一轮已记录，下次复习时再试一次。')}</p><p id="mf-save-status" role="status">${U('学习记录保存在当前浏览器。')}</p><div class="mf-actions"><button class="btn accent" data-route="progress">${U('查看学习记录')}</button><button class="btn secondary" data-route="review">${U('查看复习安排')}</button><button class="btn secondary" data-route="assessment">${U('开始检测')}</button></div></section>`;
    const dots=`<div class="mf-dots" role="img" aria-label="${U('本轮进度 {n} / 4',{n:step+1})}">${[0,1,2,3].map(i=>`<span class="${i<step?'done':i===step?'current':''}"></span>`).join('')}</div>`;
    if(run.stage==='repair')return `${header}${dots}<section class="card mf-task"><h1>${U('补上这一处，再试一次。')}</h1><p class="muted">${U('刚才的回答还不完整。先从一个提示开始。')}</p>${run.hint_levels_used.map(level=>`<p class="mf-hint" role="status">${esc(MindFlowV1.text(b.hint_ladder[level-1],state.lang))}</p>`).join('')}${run.source_open?`<div class="mf-repair-body topic-body">${window.PathlineContent.repair(ctx.topic_id,b.repair_sources)}</div>`:''}<div class="mf-actions">${run.hint_levels_used.length?`<button id="mf-recheck" class="btn accent">${U('合上提示，独立再试')}</button>`:''}${run.hint_levels_used.length<2?`<button id="mf-hint" class="ghost-btn">${U('给我提示 {n}',{n:run.hint_levels_used.length+1})}</button>`:!run.source_open?`<button id="mf-source" class="btn secondary">${U('查看对应教材片段')}</button>`:''}</div><button id="mf-pause" class="ghost-btn mf-pause">${U(run.paused?'继续':'暂停')}</button></section>`;
    const prompt=MindFlowV1.prompt(run);
    return `${header}${dots}<section class="card mf-task"><form id="mf-answer-form"><h1>${U(run.stage==='recall'?'先不看资料，自己想。':run.stage==='application'?'用在一个小问题里。':'合上资料，再独立试一次。')}</h1><p class="mf-question" id="mf-question">${esc(MindFlowV1.text(prompt.text,state.lang))}</p><label class="tiny" for="mf-response">${U('你的回答')}</label><textarea id="mf-response" rows="${prompt.kind==='number'?2:4}" maxlength="4000" required ${prompt.kind==='number'?'inputmode="decimal"':''} aria-describedby="mf-question" ${run.paused?'disabled':''}>${esc(run.response)}</textarea><p class="tiny">${U(prompt.kind==='number'?'只填写数值；答案按本题条件核对。':'用自己的话或公式回答；本轮按明确的关键关系核对。')}</p><div class="mf-actions"><button class="btn accent" type="submit" ${run.paused?'disabled':''}>${U('提交回答')}</button><button id="mf-stuck" class="ghost-btn" type="button" ${run.paused?'disabled':''}>${U('我暂时想不起来')}</button></div><button id="mf-pause" class="ghost-btn mf-pause" type="button">${U(run.paused?'继续':'暂停')}</button><p id="mf-error" role="alert"></p></form></section>`;
  }
  function bindMindFlow(){
    const run=currentMF();if(!run)return;
    document.getElementById('mf-exit')?.addEventListener('click',async()=>{sessionTick();await save();if(REVIEW_PAGE)location.href=GMFShared.safeReturn(params.get('return_to'));else route('study',{topicId:run.context.topic_id});});
    document.getElementById('mf-response')?.addEventListener('input',e=>{run.response=e.target.value;save();});
    const redraw=async action=>{try{sessionTick();action();if(run.final_state){const evidence=MindFlowV1.evidence(run);F.acceptLearning(state.evidence,progress(course()),evidence,run.context);F.capReview(progress(course()),activeExamDate(course()));}const saved=await save();render();if(!saved&&run.final_state)document.getElementById('mf-save-status').textContent=U('保存失败，请保持页面打开并重试。');}catch(error){toast(U('无法完成本次操作，请重试。'));console.error(error);}};
    document.getElementById('mf-answer-form')?.addEventListener('submit',e=>{e.preventDefault();redraw(()=>MindFlowV1.submit(run,document.getElementById('mf-response').value));});
    document.getElementById('mf-stuck')?.addEventListener('click',()=>redraw(()=>MindFlowV1.submit(run,state.lang==='en'?'I do not recall':'暂时想不起来')));
    document.getElementById('mf-hint')?.addEventListener('click',()=>redraw(()=>MindFlowV1.hint(run)));
    document.getElementById('mf-source')?.addEventListener('click',async()=>{try{await ContentRuntime.ensure();redraw(()=>MindFlowV1.openSource(run));}catch{toast(U('课程内容暂时无法加载，请联网后重试。'));}});
    document.getElementById('mf-recheck')?.addEventListener('click',()=>redraw(()=>MindFlowV1.recheck(run)));
    document.getElementById('mf-pause')?.addEventListener('click',()=>redraw(()=>{run.paused=!run.paused;}));
  }
  function renderAssessment(){return '';}
  function bindAssessment(){}
  function U(text,vars={}){return window.PathlineUI.t(state.lang,text,vars);}
  function exerciseIds(c){return c.id===physics.id?[...new Set(window.PathlineTextbook.course.topics.filter(t=>t.status==='validated').flatMap(t=>t.exercise_refs))]:[];}
  function topicExercises(c,t){return c.id===physics.id?window.PathlineTextbook.course.topics.find(x=>x.topic_id===t.id)?.exercise_refs||[]:[];}
  function progressBar(percent,label){return `<div class="learning-progress" role="progressbar" aria-label="${esc(label)}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${percent}"><span style="width:${percent}%"></span></div>`;}
  function completionCard(label,stats,kind){return `<section class="card completion-card"><div class="card-title"><h2>${U(label)}</h2><b>${stats.percent}%</b></div><p>${kind==='topic'?U('{done} / {total} Topics · {percent}%',{done:stats.count,total:stats.total,percent:stats.percent}):stats.total?U('{done} / {total} 道 · {percent}%',{done:stats.count,total:stats.total,percent:stats.percent}):U('当前没有正式习题')}</p>${progressBar(stats.percent,U(label))}</section>`;}
  function topicStatus(c,t){const p=state.progress[c.id]?.[t.id];return U(p?.dueAt<=Date.now()&&p?.dueAt?'待复习':F.completed(state.evidence,c.id,t.id)?'已学习':hasEvidence(c.id,t.id)?'正在学习':'尚未学习');}
  function evidenceBadges(c,t){const list=[topicStatus(c,t)];if(state.evidence.practice.some(e=>e.course_id===c.id&&(e.topic_id===t.id||topicExercises(c,t).includes(e.exercise_id))))list.push(U('有练习记录'));if(!state.evidence.assessment.some(e=>e.course_id===c.id&&e.topic_id===t.id))list.push(U('尚无独立测评'));return list.map(label=>`<span class="reason">${label}</span>`).join('');}
  function topicHistory(c,t){const mf=state.evidence.learning_repair.filter(e=>e.course_id===c.id&&e.topic_id===t.id).length,ex=F.exerciseProgress(state.evidence,c.id,topicExercises(c,t)).count,assessment=state.evidence.assessment.filter(e=>e.course_id===c.id&&e.topic_id===t.id).length;return `${F.completed(state.evidence,c.id,t.id)?'✓ ':''}${topicStatus(c,t)} · ${U('{n} 道练习',{n:ex})} · ${U('心流 {n} 次',{n:mf})}${mf?` · ${mfResult(c.id,t.id)}`:''} · ${assessment?U('模考：{n} 次测评',{n:assessment}):U('尚无独立测评')}`;}
  function dueLabel(timestamp){const a=new Date(timestamp),b=new Date(),days=Math.round((Date.UTC(a.getFullYear(),a.getMonth(),a.getDate())-Date.UTC(b.getFullYear(),b.getMonth(),b.getDate()))/86400000);return days<=0?U('今天稍后'):days===1?U('明天'):days<=6?U('{n} 天后',{n:days}):days<=13?U('下周'):new Intl.DateTimeFormat(state.lang==='zh'?'zh-CN':'en-US',{month:'short',day:'numeric'}).format(a);}
  function examCard(c){const e=F.examInfo(activeExamDate(c)),date=e.date?new Intl.DateTimeFormat(state.lang==='zh'?'zh-CN':'en-US',{year:'numeric',month:'long',day:'numeric',weekday:'long'}).format(new Date(e.date)):'';return `<section class="card pad exam-card"><div><span class="tiny">${esc(c.title)}</span><h2>${e.state==='unset'?U('考试日期未设置'):e.state==='ended'?U('本次考试日期已结束'):e.state==='today'?U('考试就在今天'):U('距离考试还有')}</h2>${e.state==='upcoming'?`<p class="exam-days"><b>${e.days}</b> ${U('天')}</p>`:''}${date?`<p class="muted">${date}</p>`:''}${e.state==='upcoming'||e.state==='today'?`<p class="tiny">${U('考试临近时，复习间隔缩短，最晚不超过考试日。')}</p>`:''}</div><button class="btn secondary small" data-route="settings">${U('设置日期')}</button></section>`;}
  function savedExerciseRows(c){const saved=state.savedExercises.filter(e=>e.course_id===c.id);return saved.length?`<div class="card pad">${saved.map(s=>{const ex=window.PathlineTextbook.exercises.find(e=>e.exercise_id===s.exercise_id);return `<div class="queue-row simple-queue"><div class="queue-copy"><b>${esc(ex?`${ex.exercise_type} ${ex.source_number} · Chapter ${ex.source_chapter}`:s.exercise_id)}</b></div><button class="btn secondary small" data-open-saved="${esc(s.exercise_id)}" data-topic="${esc(s.topic_id)}">${U('打开题目')}</button></div>`;}).join('')}</div>`:`<p class="muted quiet-empty">${U('还没有留下的题。')}</p>`;}
  function minutes(seconds){const n=Math.round(seconds/6)/10;return n?String(n):seconds>0?'<0.1':'0';}
  function courseColor(cid){return Math.max(0,Object.keys(registeredCourses()).indexOf(cid))%5;}
  function weekDetails(day,cid){if(!day)return '';const names=Object.entries(day.courses).filter(([id])=>!cid||id===cid);return `<b>${new Intl.DateTimeFormat(state.lang==='zh'?'zh-CN':'en-US',{month:'short',day:'numeric',weekday:'long'}).format(new Date(day.date))} · ${U('总计 {n} 分钟',{n:minutes(day.total)})}</b>${names.map(([id,c])=>`<p><b>${esc(registeredCourses()[id]?.title||(id==='null'?U('自由学习 / 独立测评'):id))}</b> · ${minutes(c.total)} ${U('分钟')}<br><span class="tiny">${U('学习 {learn} · 复习 {review} · 测评 {assessment} 分钟',{learn:minutes(c.learn),review:minutes(c.review),assessment:minutes(c.assessment)})} · 心流专注 ${minutes(c.focus||0)} 分钟</span></p>`).join('')||`<p class="tiny">${U('本周还没有计时记录。')}</p>`}`;}
  function selectWeekDay(key,cid=null){selectedWeekDay=key;selectedWeekCourse=cid;const day=Sessions.week(state.sessions).find(d=>d.key===key);document.getElementById('week-details').innerHTML=weekDetails(day,cid);document.querySelectorAll('.week-day').forEach(e=>e.classList.toggle('selected',e.dataset.weekDay===key));}
  function paintReadButton(b){const active=F.completed(state.evidence,course().id,b.dataset.read);b.classList.toggle('is-recorded',active);b.setAttribute('aria-pressed',String(active));b.textContent=U(active?'✓ 本节已学习':'记录本节已学习');}
  function paintSavedButton(b){const active=state.savedExercises.some(e=>e.course_id===course().id&&e.exercise_id===b.dataset.saveExercise);b.classList.toggle('is-recorded',active);b.setAttribute('aria-pressed',String(active));b.textContent=U(active?'✓ 已留下':'留下这道题');}
  function currentMF(){return state.mfContext?state.mfRuns[MindFlowV1.key(state.mfContext)]:null;}
  function sessionTick(){const timestamp=Date.now();if(activeSession){const run=REVIEW_PAGE&&state.route==='mindflow'?currentMF():null;Sessions.credit(activeSession,lastSessionTick,timestamp,lastInputAt,sessionVisible&&navigator.onLine&&!MFV3?.isFocusing()&&(activeSession.mode!=='review'||!!run&&!run.final_state&&!run.paused)&&(activeSession.mode!=='assessment'||assessmentActive));if(run){run.active_seconds=activeSession.active_seconds;run.daily_seconds=activeSession.daily_seconds;}save();}lastSessionTick=timestamp;}
  let assessmentActive=false;
  function syncSession(){sessionTick();const c=course(),run=REVIEW_PAGE&&state.route==='mindflow'?currentMF():null,tid=state.route==='mindflow'?state.mfContext?.topic_id:state.routeParams.topicId,mode=state.route==='study'&&F.isReady(topicById(c,tid)?.topic||{})?'learn':run&&!run.final_state?'review':state.route==='assessment'&&state.assessmentContext?'assessment':null;
    const sid=mode==='review'?run.context.session_id:mode==='assessment'?state.assessmentContext.session_id:null;
    if(activeSession&&(!mode||activeSession.course_id!==c.id||activeSession.topic_id!==tid||activeSession.mode!==mode||sid&&activeSession.session_id!==sid)){activeSession.ended_at=new Date().toISOString();activeSession=null;}
    if(mode&&!activeSession){activeSession=sid?state.sessions.find(s=>s.session_id===sid):null;if(!activeSession){activeSession={session_id:sid||crypto.randomUUID(),course_id:c.id,unit_id:c.id===physics.id?window.PathlineTextbook.course.units.find(u=>u.topic_refs.includes(tid))?.unit_id??null:topicById(c,tid)?.unit.id||null,topic_id:tid||null,mode,started_at:new Date().toISOString(),ended_at:new Date().toISOString(),active_seconds:0,daily_seconds:{}};state.sessions.push(activeSession);}lastInputAt=lastSessionTick=Date.now();save();}
  }
  function sessionInput(){sessionTick();lastInputAt=Date.now();}
  ['pointerdown','keydown','wheel','touchstart','scroll'].forEach(event=>document.addEventListener(event,sessionInput,{passive:true,capture:true}));
  let lastMove=0;document.addEventListener('pointermove',()=>{if(Date.now()-lastMove>1000){lastMove=Date.now();sessionInput();}},{passive:true});
  document.addEventListener('visibilitychange',()=>{sessionTick();sessionVisible=!document.hidden;lastInputAt=lastSessionTick=Date.now();});
  document.addEventListener('visibilitychange',async()=>{if(!document.hidden){await LearningStore.flush();const latest=await LearningStore.restore(state,window.PathlineTextbook.course);state.evidence=latest.evidence;for(const session of latest.sessions)if(!state.sessions.some(s=>s.session_id===session.session_id))state.sessions.push(session);for(const c of Object.values(allCourses()))for(const u of c.units)for(const t of u.topics)F.rebuildSchedule(state.evidence,progress(c),c.id,t.id);if(['progress','review','pathway','overview'].includes(state.route))render();}});
  window.addEventListener('pagehide',()=>{sessionTick();if(activeSession)activeSession.ended_at=new Date().toISOString();save();});
  setInterval(sessionTick,5000);

  function readHash(){
    const [kind,id,section]=location.hash.slice(1).split('/');
    if(kind==='topic' && topicById(course(),id)){state.route='study';state.routeParams={topicId:id,section:section||'reading'};}
    else if(!REVIEW_PAGE&&['overview','pathway','review','progress','courses','settings','mindflow','assessment'].includes(kind)){state.route=kind;state.routeParams=kind==='mindflow'?{page:id||'focus'}:{};}
  }
  window.addEventListener('hashchange',async()=>{readHash();if(state.route==='progress'){const latest=await LearningStore.restore(state,window.PathlineTextbook.course);state.evidence=latest.evidence;state.sessions=latest.sessions;}if(state.route==='study')await ContentRuntime.ensureTopic(state.routeParams.topicId);save();render();});
  if(!REVIEW_PAGE&&location.hash.startsWith('#mindflow/')&&params.get('return_to')){const tid=params.get('topic_id'),unit=topicById(course(),tid)?.unit;state.mfEntryContext={course_id:course().id,unit_id:unit?.id??null,topic_id:unit?tid:null,return_to:GMFShared.safeReturn(params.get('return_to'))};}
  readHash();
  if(REVIEW_PAGE){
    const tid=params.get('topic_id')||state.mfContext?.topic_id;
    if(!MindFlowV1.blueprints[tid]||course().id!==physics.id){location.replace(GMFShared.url('mindflow',moduleContext()));return;}
    const k=course().id+'|'+tid;let run=state.mfRuns[k];
    if(!run||run.final_state&&params.get('new_session')==='1'){const found=topicById(course(),tid);run=state.mfRuns[k]=MindFlowV1.create({session_id:crypto.randomUUID(),course_id:course().id,unit_id:window.PathlineTextbook.course.units.find(u=>u.topic_refs.includes(tid)).unit_id,topic_id:tid,title:found.topic.title,started_at:new Date().toISOString(),lang:state.lang});}
    state.mfContext=run.context;state.route='mindflow';params.delete('new_session');const reviewUrl=new URL(location.href);reviewUrl.searchParams.delete('new_session');history.replaceState(null,'',reviewUrl);
  }else if(state.route==='assessment'){location.replace(GMFShared.url(state.route,moduleContext()));return;}
  for(const c of Object.values(allCourses())){const p=Engine.ensureCourseProgress(c,state.progress[c.id]||{});state.progress[c.id]=p;for(const u of c.units)for(const t of u.topics)F.rebuildSchedule(state.evidence,p,c.id,t.id);F.capReview(p,activeExamDate(c));}
  if(REVIEW_PAGE)await ContentRuntime.ensure();else if(state.route==='study')await ContentRuntime.ensureTopic(state.routeParams.topicId);
  if(MFV3)await MFV3.init({toast,context:moduleContext,openTopic:ctx=>{if(allCourses()[ctx.course_id])state.activeCourseId=ctx.course_id;route('study',{topicId:ctx.topic_id});}});
  if(state.route==='progress'){const latest=await LearningStore.restore(state,window.PathlineTextbook.course);state.evidence=latest.evidence;state.sessions=latest.sessions;}
  render();
})().catch(error=>{document.getElementById('app').innerHTML='<main class="page"><h1>GiveMeFive</h1><p>本地数据或课程无法打开，请联网并重新加载。 / Local data or course could not be opened. Reconnect and reload.</p><button onclick="location.reload()">重新加载 / Reload</button></main>';console.error(error);});
