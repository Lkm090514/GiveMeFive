window.PathlineData = {courses:{}};



window.PathlineEngine = (() => {
  const DAY = 86400000;
  const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
  const now=()=>Date.now();
  const daysBetween=(a,b)=>Math.max(0,(b-a)/DAY);
  function initialTopicState(){return {mastery:22, attempts:0, correct:0, confidence:0.5, lastStudied:null, dueAt:null, intervalDays:0, ease:2.3, streak:0};}
  function ensureCourseProgress(course, existing={}){
    const out={...existing};
    course.units.forEach(u=>u.topics.forEach(t=>{ if(!out[t.id]) out[t.id]=initialTopicState(); }));
    return out;
  }
  function prerequisiteReadiness(topic, progress){
    if(!topic.prereq?.length) return 1;
    return topic.prereq.reduce((sum,id)=>sum+(progress[id]?.mastery??20)/100,0)/topic.prereq.length;
  }
  function downstreamLeverage(topic, course, progress){
    if(!course) return 0;
    const dependents=[];
    course.units.forEach(u=>u.topics.forEach(t=>{ if(t.prereq?.includes(topic.id)) dependents.push(t); }));
    if(!dependents.length) return 0;
    const weakness=dependents.reduce((sum,t)=>sum+(100-(progress[t.id]?.mastery??20))/100,0)/dependents.length;
    return clamp(weakness*(0.7+0.15*Math.min(2,dependents.length)),0,1);
  }
  function forgettingRisk(state){
    if(!state.lastStudied) return .45;
    const elapsed=daysBetween(state.lastStudied, now());
    const interval=Math.max(.5,state.intervalDays||1);
    return clamp(elapsed/interval,0,1.6)/1.6;
  }
  function examPressure(examDate){
    if(!examDate) return .35;
    const t=new Date(examDate).getTime(); if(!Number.isFinite(t)) return .35;
    const d=Math.max(0,(t-now())/DAY);
    return clamp(1-d/180,0.1,1);
  }
  function priority(topic,state,progress,examDate,course){
    const weakness=(100-state.mastery)/100;
    const forget=forgettingRisk(state);
    const prereqReady=prerequisiteReadiness(topic,progress);
    const leverage=downstreamLeverage(topic,course,progress);
    const confidenceGap=1-(state.confidence??.5);
    const overdue=(state.attempts>0 || state.lastInteraction) && state.dueAt && state.dueAt<=now()?1:0;
    const pressure=examPressure(examDate);
    const blockPenalty=topic.prereq?.length ? (prereqReady<.45?.18:prereqReady<.65?.08:0) : 0;
    const raw=.36*weakness+.20*forget+.12*leverage+.08*confidenceGap+.12*overdue+.07*pressure-blockPenalty;
    const score=100*clamp(raw,0,1);
    const reasons=[];
    if(weakness>.55) reasons.push('low mastery');
    if(overdue) reasons.push('review due');
    if((state.attempts>0 || state.lastInteraction) && forget>.55) reasons.push('memory decay');
    if(leverage>.35) reasons.push('unlocks later topics');
    if(confidenceGap>.55) reasons.push('low confidence');
    if(prereqReady<.6 && topic.prereq?.length) reasons.push('prerequisites not ready');
    if(reasons.length===0) reasons.push('best next gain');
    return {score:Math.round(score),reasons,prereqReady,leverage};
  }
  function recordAnswer(state, correct, confidence=.65){
    const s={...state};
    s.attempts=(s.attempts||0)+1; s.correct=(s.correct||0)+(correct?1:0);
    s.confidence=clamp((s.confidence??.5)*.65+confidence*.35,0,1);
    const quality=correct ? (confidence>.75?5:confidence>.45?4:3) : (confidence>.7?1:2);
    if(correct){
      s.streak=(s.streak||0)+1;
      s.ease=clamp((s.ease||2.3)+(quality===5?.12:.04),1.3,3.0);
      if(s.streak===1) s.intervalDays=1;
      else if(s.streak===2) s.intervalDays=3;
      else s.intervalDays=Math.max(1,Math.round((s.intervalDays||3)*s.ease));
      const gain=7 + (1-s.mastery/100)*10 + (confidence>.7?2:0);
      s.mastery=clamp(Math.round(s.mastery+gain),0,100);
    } else {
      s.streak=0; s.ease=clamp((s.ease||2.3)-.18,1.3,3.0); s.intervalDays=.35;
      const penalty=confidence>.7?9:5; s.mastery=clamp(Math.round(s.mastery-penalty),0,100);
    }
    s.lastStudied=now(); s.dueAt=now()+s.intervalDays*DAY;
    return s;
  }
  function courseReadiness(course,progress){
    let total=0,weight=0;
    course.units.forEach(u=>u.topics.forEach(t=>{const s=progress[t.id]||initialTopicState(); const w=1+((parseInt(u.weight)||15)/30); total+=s.mastery*w;weight+=w;}));
    return weight?Math.round(total/weight):0;
  }
  function rankedTopics(course,progress,examDate){
    const rows=[]; course.units.forEach(u=>u.topics.forEach(t=>{ const st=progress[t.id]||initialTopicState(); rows.push({unit:u,topic:t,state:st,...priority(t,st,progress,examDate,course)}); }));
    return rows.sort((a,b)=>b.score-a.score);
  }
  function dueTopics(course,progress){
    const rows=[]; course.units.forEach(u=>u.topics.forEach(t=>{const s=progress[t.id]; if(s&&(s.attempts>0||s.lastInteraction)&&s.dueAt&&s.dueAt<=now()) rows.push({unit:u,topic:t,state:s});}));
    return rows.sort((a,b)=>a.state.dueAt-b.state.dueAt);
  }
  return {initialTopicState,ensureCourseProgress,priority,recordAnswer,courseReadiness,rankedTopics,dueTopics,forgettingRisk,prerequisiteReadiness,downstreamLeverage};
})();



window.PathlineParsers = (()=>{
  const textExt=new Set(['txt','md','csv','json','html','htm']);
  const ext=name=>(name.split('.').pop()||'').toLowerCase();
  async function parseFile(file){
    if(!file.size)throw new Error('The uploaded file is empty.');
    if(file.size>30*1024*1024)throw new Error('File exceeds the 30 MB limit.');
    if(textExt.has(ext(file.name))) return {name:file.name,text:await file.text(),source:'browser'};
    try{
      const r=await fetch('/api/parse',{method:'POST',body:file,headers:{'X-Filename':encodeURIComponent(file.name),'Content-Type':'application/octet-stream'}});
      if(!r.ok){let m='';try{m=(await r.json()).error||''}catch{m=await r.text()}throw new Error(m||'Parser error')}
      const data=await r.json(); return {...data,source:'local parser'};
    }catch(err){
      if(String(err.message||'').includes('PDF support')) throw err;
      throw new Error('This format needs the included local server. Run “python3 server.py”, then reopen http://localhost:8787.');
    }
  }
  function headingsFromText(text){
    const lines=text.split(/\r?\n/).map(s=>s.trim()).filter(Boolean);
    const candidates=[];
    for(const line of lines){
      const cleaned=line.replace(/^#{1,6}\s*/,'').replace(/^\d+(?:\.\d+)*[.)]?\s*/,'').trim();
      if(/^(unit|chapter|section)\s+\d+[.:)]?$/i.test(cleaned)) continue;
      if(cleaned.length>=4 && cleaned.length<=86 && !/[.!?。！？]$/.test(cleaned) && cleaned.split(/\s+/).length<=12) candidates.push(cleaned);
    }
    const seen=new Set(); return candidates.filter(x=>{const k=x.toLowerCase(); if(seen.has(k))return false;seen.add(k);return true;}).slice(0,24);
  }
  function sentences(text){return text.replace(/\s+/g,' ').split(/(?<=[.!?。！？])\s*/).map(s=>s.trim()).filter(s=>s.length>35 && s.length<360);}
  const STOP=new Set('about after again against among because before being below between could every first from have into itself more most other over same should some such than that their there these they this those through under very what when where which while with would your using used also into onto only each then them were will been does doing just like make many much often both across within without'.split(' '));
  function terms(text){
    const seen=new Set(),out=[];
    for(const raw of text.match(/[A-Za-z][A-Za-z-]{4,}/g)||[]){const w=raw.toLowerCase();if(STOP.has(w)||seen.has(w))continue;seen.add(w);out.push(raw)}
    return out.sort((a,b)=>b.length-a.length);
  }
  function questionFrom(excerpt, pool, index){
    const own=terms(excerpt),answer=own.find(x=>pool.filter(y=>y.toLowerCase()===x.toLowerCase()).length===1)||own[0];
    if(!answer) return {prompt:'Which study move best checks whether you understand this concept?',choices:['Reread it repeatedly','Explain it from memory, then check the source','Highlight every sentence','Copy the paragraph word-for-word'],answer:1,explanation:'Active retrieval exposes gaps that passive rereading can hide.'};
    const distractors=pool.filter(x=>x.toLowerCase()!==answer.toLowerCase()).slice(index%Math.max(1,pool.length),index%Math.max(1,pool.length)+3);
    const fallbacks=['evidence','variable','process','structure'];
    while(distractors.length<3){const f=fallbacks[distractors.length];if(f.toLowerCase()!==answer.toLowerCase())distractors.push(f)}
    const choices=[answer,...distractors.slice(0,3)];
    const shift=index%4,rot=[...choices.slice(shift),...choices.slice(0,shift)],correct=rot.findIndex(x=>x===answer);
    const blanked=excerpt.replace(new RegExp(`\\b${answer.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')}\\b`,'i'),'_____');
    return {prompt:`Which term best completes this statement from your material? “${blanked}”`,choices:rot,answer:correct,explanation:`Your imported material links “${answer}” to this idea. Reconstruct the full statement from memory before rereading it.`};
  }
  function buildCustomCourse(title,text){
    const hs=headingsFromText(text),ss=sentences(text),pool=terms(text).slice(0,40);
    const names=hs.length>=3?hs.slice(0,12):ss.slice(0,8).map((s,i)=>`Concept ${i+1}: ${s.split(/\s+/).slice(0,7).join(' ')}…`);
    const seed=Date.now();
    const topics=(names.length?names:['Core concepts','Applications','Practice and review']).map((name,i)=>{
      const excerpt=ss[i]||ss[(i*3)%Math.max(1,ss.length)]||'Review the imported material and retrieve the central idea without looking.';
      return {id:`c-${seed}-${i}`,title:name,minutes:20,summary:excerpt,objectives:['Explain the idea in your own words','Retrieve the key rule without notes','Apply it to a new example'],questions:[questionFrom(excerpt,pool,i)],prereq:[]};
    });
    topics.forEach((t,i)=>t.prereq=i?[topics[i-1].id]:[]);
    return {id:`custom-${seed}`,title:title||'Imported Course',subtitle:'Generated locally from your material',accent:'amber',targetDefault:'A',exam:'Set your date',sourceText:text.slice(0,150000),units:[{id:'cu1',title:'Generated learning path',weight:'100%',topics}]};
  }
  return {parseFile,buildCustomCourse,headingsFromText};
})();



window.PathlineI18n = (() => {
  const ui = {
    en: {
      'nav.study':'Study','nav.overview':'Overview','nav.pathway':'Pathway','nav.review':'Review','nav.progress':'Progress','nav.import':'Import','nav.settings':'Settings',
      'route.overview':'Overview','route.pathway':'Learning pathway','route.review':'Review queue','route.progress':'Progress','route.import':'Import material','route.settings':'Settings','route.study':'Study','route.quiz':'Quick check',
      'common.switchCourse':'Switch course','common.language':'Language','common.theme':'Theme','common.target':'Target','common.unit':'Unit','common.mastery':'mastery','common.minutes':'min','common.minuteWord':'minutes','common.checks':'checks','common.last':'last','common.newTopic':'new topic','common.readiness':'readiness','common.back':'Back','common.topic':'Topic','common.review':'Review','common.cancel':'Cancel','common.system':'System','common.light':'Light','common.dark':'Dark','common.local':'local','common.custom':'Custom','common.now':'Now','common.notStudied':'Not studied','common.dueNow':'Due now','common.inHours':'in {n}h','common.inDays':'in {n}d',
      'onboard.eyebrow':'Adaptive study OS','onboard.title':'Know what to study next.','onboard.desc':'Turn a syllabus or your own material into a learning path that changes as you learn. Retrieval practice, spaced review, and priorities you can actually understand.','onboard.name':'Your name','onboard.start':'Start with AP Statistics','onboard.choose':'Choose a course','onboard.step1.title':'Learn a focused concept','onboard.step1.sub':'18–30 min · objectives first','onboard.step2.title':'Retrieve from memory','onboard.step2.sub':'Fast checks, not passive rereading','onboard.step3.title':'Path recalculates','onboard.step3.sub':'Weakness + forgetting + prerequisites + exam pressure','onboard.step4.title':'Review when it matters','onboard.step4.sub':'Due queue expands or shrinks with performance',
      'overview.title':'Your next best move is already ranked.','overview.desc':'Pathline recalculates priority from mastery, forgetting, confidence, prerequisites, due reviews, and the time left before your exam.','overview.next':'Highest-value next step','overview.studyNow':'Study now','overview.seePath':'See pathway','overview.priorityScore':'priority score','overview.courseReadiness':'Course readiness','overview.courseReadinessSub':'weighted by topic mastery','overview.reviewsDue':'Reviews due','overview.reviewsDueSub':'spaced retrieval queue','overview.topicsTouched':'Topics touched','overview.topicsTouchedSub':'at least one retrieval attempt','overview.minutesToday':'Minutes today','overview.goal':'goal {n} min','overview.queue':'Priority queue','overview.queueSub':'Not a fixed chapter order — the ranking changes with you.','overview.openReview':'Open review queue','overview.courses':'Courses','overview.coursesSub':'Built-in paths plus anything you import.','overview.createMaterial':'Create from material','overview.adaptivePath':'Adaptive learning path',
      'greeting.morning':'Good morning','greeting.afternoon':'Good afternoon','greeting.evening':'Good evening',
      'path.eyebrow':'Learning pathway','path.desc':'Topics remain organized by course structure while the priority rank tells you what deserves attention first.','path.defaultMap':'Your adaptive course map',
      'review.eyebrow':'Spaced review','review.due.one':'1 review due.','review.due.many':'{n} reviews due.','review.none':'Nothing is overdue.','review.descDue':'Clear due concepts first. Correct, confident answers expand the interval; incorrect answers pull the concept back sooner.','review.descNone':'Use the recommended queue below if you want to keep studying.','review.dayStreak':'{n} day streak','review.dueLabel':'Due {when}','review.how':'How scheduling works','review.explainable':'Explainable','review.howDesc':'A correct answer increases mastery and expands the next interval. A wrong answer shortens the interval. Confidence matters too: a confidently wrong answer is a stronger signal that the mental model needs repair. Priority also rises when a topic is weak, decaying, prerequisite-heavy, overdue, or close to the exam.',
      'progress.eyebrow':'Progress','progress.title':'See the signal, not just the streak.','progress.desc':'Mastery, retrieval accuracy, confidence, and review timing are separated so you can tell whether progress is real or only feels familiar.','progress.accuracy':'Retrieval accuracy','progress.correct':'{c}/{a} checks correct','progress.confidence':'Average confidence','progress.confidenceSub':'calibrated after each check','progress.strong':'Strong topics','progress.strongSub':'mastery ≥ 75%','progress.streak':'Day streak','progress.streakSub':'activity, not a punishment mechanic','progress.last14':'Last 14 days','progress.minutes':'minutes','progress.diagnostic':'Course diagnostic',
      'import.eyebrow':'Create from your material','import.title':'Bring your own syllabus.','import.desc':'TXT, Markdown, CSV and JSON parse directly in the browser. The original parser service for PDF, DOCX and PPTX is missing; paste text instead.','import.upload':'Upload material','import.localFirst':'local-first','import.drop':'Drop a course file here','import.formats':'PDF · DOCX · PPTX · TXT · MD · CSV · JSON · up to 30 MB','import.choose':'Choose file','import.build':'Build the path','import.courseName':'Course name','import.coursePlaceholder':'e.g. Biology — Cells & Membranes','import.examDate':'Exam date','import.paste':'Or paste material','import.pastePlaceholder':'Paste syllabus headings, notes, or a chapter outline…','import.generate':'Generate learning path','import.clear':'Clear','import.what':'What gets generated','import.topicMap':'1. Topic map','import.topicMapDesc':'Headings and strong concept boundaries become sequential topics with prerequisites.','import.checks':'2. Retrieval checks','import.checksDesc':'Every generated topic starts with an active-recall check instead of passive completion.','import.queue':'3. Adaptive queue','import.queueDesc':'The same ranking engine handles imported courses, including forgetting and exam pressure.','import.materialLoaded':'Material loaded','import.reading':'Reading text…','import.characters':'{n} characters extracted · {source}',
      'settings.eyebrow':'Settings','settings.title':'Keep the system yours.','settings.desc':'Pathline stores study state in this browser by default. Export it whenever you want a portable backup.','settings.study':'Study settings','settings.dailyGoal':'Daily goal','settings.dailyGoalDesc':'Used for progress visualization, never to punish missed days.','settings.themeDesc':'System, light, or dark.','settings.langDesc':'Switch the entire interface and built-in course content. Imported courses keep their source language.','settings.examDate':'Exam date','settings.examDateDesc':'Changes urgency in the priority ranking.','settings.data':'Data','settings.dataDesc':'Your progress, imported courses, and settings are stored in browser localStorage. Uploaded source files are parsed locally and are not persisted as raw files.','settings.export':'Export backup','settings.import':'Import backup','settings.reset':'Reset all','settings.install':'Install Pathline','settings.installHint':'Use your browser’s “Add to Home Screen” / install command if available.',
      'study.before':'Before you look anything up','study.beforeDesc':'Close your notes and explain the central idea in one minute. Retrieval is the diagnostic; rereading is only the repair step.','study.start':'Start quick check','study.why':'Why this topic now','study.current':'Current mastery','study.correctNext':'{c}/{a} correct · next review {when}','study.noEvidence':'No retrieval evidence yet','study.focus':'Estimated focus time','study.minutes':'{n} minutes',
      'quiz.label':'Quick check · {i} of {n}','quiz.confidence':'How confident are you?','quiz.correct':'Correct.','quiz.notQuite':'Not quite.','quiz.finish':'Finish','quiz.next':'Next question','quiz.check':'Check answer','quiz.resultPerfect':'Clean retrieval.','quiz.resultOkay':'Useful signal.','quiz.resultRepair':'Repair the model, then retry.','quiz.resultDesc':'Your mastery is now {m}%. Next review is {when}. The interval changed from your accuracy and confidence, not from a fixed streak bonus.','quiz.backOverview':'Back to overview','quiz.reviewTopic':'Review topic',
      'modal.switch':'Switch course','modal.switchDesc':'Each course keeps separate mastery and review timing.','modal.create':'Create custom course','modal.resetTitle':'Reset Pathline?','modal.resetDesc':'This clears all local mastery, review schedules, custom courses, and settings from this browser.','modal.resetEverything':'Reset everything',
      'toast.moreMaterial':'Add more source material before generating the course.','toast.pathGenerated':'Learning path generated.','toast.readFile':'Read {name}','toast.goalUpdated':'Daily goal updated.','toast.examUpdated':'Exam pressure updated.','toast.backupExported':'Backup exported.','toast.backupImported':'Backup imported.','toast.backupFailed':'That backup file could not be read.',
      'reason.low mastery':'low mastery','reason.review due':'review due','reason.memory decay':'memory decay','reason.unlocks later topics':'unlocks later topics','reason.low confidence':'low confidence','reason.prerequisites not ready':'prerequisites not ready','reason.best next gain':'best next gain',
      'parser.server':'This format needs the included local server. Run “python3 server.py”, then reopen http://localhost:8787.','parser.pdfDep':'PDF support needs one small dependency. Run: python3 -m pip install pypdf','parser.unsupported':'Unsupported file type','parser.empty':'The uploaded file is empty.','parser.large':'File exceeds the 30 MB limit.','parser.noText':'No readable text was found in this file. Scanned PDFs need OCR before import.'
    },
    zh: {
      'nav.study':'学习','nav.overview':'总览','nav.pathway':'学习路径','nav.review':'复习','nav.progress':'进度','nav.import':'导入','nav.settings':'设置',
      'route.overview':'总览','route.pathway':'学习路径','route.review':'复习队列','route.progress':'学习进度','route.import':'导入材料','route.settings':'设置','route.study':'学习','route.quiz':'快速检测',
      'common.switchCourse':'切换课程','common.language':'语言','common.theme':'主题','common.target':'目标','common.unit':'单元','common.mastery':'掌握度','common.minutes':'分钟','common.minuteWord':'分钟','common.checks':'次检测','common.last':'上次','common.newTopic':'新知识点','common.readiness':'准备度','common.back':'返回','common.topic':'知识点','common.review':'复习','common.cancel':'取消','common.system':'跟随系统','common.light':'浅色','common.dark':'深色','common.local':'本地','common.custom':'自定义','common.now':'现在','common.notStudied':'尚未学习','common.dueNow':'现在复习','common.inHours':'{n} 小时后','common.inDays':'{n} 天后',
      'onboard.eyebrow':'自适应学习系统','onboard.title':'永远知道下一步最该学什么。','onboard.desc':'把考纲或你自己的材料变成会随着学习表现实时变化的学习路径。主动提取、间隔复习，以及你能真正理解的学习优先级。','onboard.name':'你的名字','onboard.start':'从 AP Statistics 开始','onboard.choose':'选择课程','onboard.step1.title':'集中攻克一个概念','onboard.step1.sub':'18–30 分钟 · 先明确学习目标','onboard.step2.title':'从记忆中主动提取','onboard.step2.sub':'快速检测，而不是被动重读','onboard.step3.title':'路径实时重算','onboard.step3.sub':'薄弱度 + 遗忘 + 前置知识 + 考试压力','onboard.step4.title':'在最该复习时复习','onboard.step4.sub':'复习队列会随表现自动扩张或收缩',
      'overview.title':'系统已经排好了你下一步最值得做的事。','overview.desc':'Pathline 会综合掌握度、遗忘风险、自信度、前置知识、到期复习和距离考试的时间，实时重算优先级。','overview.next':'当前最高价值任务','overview.studyNow':'现在学习','overview.seePath':'查看路径','overview.priorityScore':'优先级分数','overview.courseReadiness':'课程准备度','overview.courseReadinessSub':'按各知识点掌握度加权','overview.reviewsDue':'待复习','overview.reviewsDueSub':'间隔提取复习队列','overview.topicsTouched':'已接触知识点','overview.topicsTouchedSub':'至少完成过一次主动检测','overview.minutesToday':'今日学习分钟','overview.goal':'目标 {n} 分钟','overview.queue':'优先级队列','overview.queueSub':'不是固定按章节推进——排序会跟着你的表现变化。','overview.openReview':'打开复习队列','overview.courses':'课程','overview.coursesSub':'内置课程，以及你自己导入的任何课程。','overview.createMaterial':'从材料创建','overview.adaptivePath':'自适应学习路径',
      'greeting.morning':'早上好','greeting.afternoon':'下午好','greeting.evening':'晚上好',
      'path.eyebrow':'学习路径','path.desc':'课程结构仍按原有单元组织，但优先级排名会告诉你现在最值得把注意力放在哪里。','path.defaultMap':'你的自适应课程地图',
      'review.eyebrow':'间隔复习','review.due.one':'有 1 个知识点需要复习。','review.due.many':'有 {n} 个知识点需要复习。','review.none':'目前没有逾期复习。','review.descDue':'先清掉已到期知识点。答对且有把握会拉长下次间隔；答错则会让它更快回到复习队列。','review.descNone':'如果还想继续学习，可以使用下面的推荐队列。','review.dayStreak':'连续学习 {n} 天','review.dueLabel':'{when}','review.how':'复习调度如何工作','review.explainable':'可解释','review.howDesc':'答对会提高掌握度并延长下次复习间隔；答错会缩短间隔。自信度也会参与判断：如果你非常自信却答错，说明当前心智模型更需要修正。知识点薄弱、正在遗忘、具有关键前置价值、已经到期，或考试临近时，优先级都会提高。',
      'progress.eyebrow':'学习进度','progress.title':'看真实学习信号，而不只是连续打卡。','progress.desc':'掌握度、主动提取正确率、自信度和复习时机被分别记录，让你能判断进步是真的，还是只是“看起来熟悉”。','progress.accuracy':'主动提取正确率','progress.correct':'答对 {c}/{a} 次','progress.confidence':'平均自信度','progress.confidenceSub':'每次检测后持续校准','progress.strong':'强项知识点','progress.strongSub':'掌握度 ≥ 75%','progress.streak':'连续学习天数','progress.streakSub':'只记录活动，不作为惩罚机制','progress.last14':'最近 14 天','progress.minutes':'分钟','progress.diagnostic':'课程诊断',
      'import.eyebrow':'从你的材料创建课程','import.title':'导入你自己的考纲或资料。','import.desc':'TXT、Markdown、CSV 和 JSON 可直接在浏览器中解析。原版源码未附带 PDF、DOCX、PPTX 解析服务，这三种格式暂不可导入；可改为粘贴文字。','import.upload':'上传材料','import.localFirst':'本地优先','import.drop':'把课程文件拖到这里','import.formats':'TXT · MD · CSV · JSON · HTML · 最大 30 MB','import.choose':'选择文件','import.build':'生成学习路径','import.courseName':'课程名称','import.coursePlaceholder':'例如：Biology — Cells & Membranes','import.examDate':'考试日期','import.paste':'或直接粘贴材料','import.pastePlaceholder':'粘贴考纲标题、课堂笔记或章节提纲……','import.generate':'生成学习路径','import.clear':'清空','import.what':'系统会生成什么','import.topicMap':'1. 知识点地图','import.topicMapDesc':'标题与清晰的概念边界会被整理为有先后依赖关系的知识点。','import.checks':'2. 主动提取检测','import.checksDesc':'导入段落保留在学习页，学习后使用 Mind Flow 回忆和修正；生成结果仍需你核对。','import.queue':'3. 自适应队列','import.queueDesc':'导入课程同样使用完整排序引擎，包括遗忘风险和考试临近压力。','import.materialLoaded':'材料已读取','import.reading':'正在读取文本……','import.characters':'已提取 {n} 个字符 · {source}',
      'settings.eyebrow':'设置','settings.title':'把系统保持成真正属于你的样子。','settings.desc':'Pathline 默认只把学习状态保存在当前浏览器中。你可以随时导出一份可迁移备份。','settings.study':'学习设置','settings.dailyGoal':'每日目标','settings.dailyGoalDesc':'仅用于进度可视化，不会因为断签而惩罚你。','settings.themeDesc':'跟随系统、浅色或深色。','settings.langDesc':'切换整个界面与内置课程内容。导入课程保留原始材料语言。','settings.examDate':'考试日期','settings.examDateDesc':'会改变优先级排序中的紧迫程度。','settings.data':'数据','settings.dataDesc':'你的学习进度、导入课程与设置保存在浏览器 localStorage 中。上传的源文件在本地解析，不会以原始文件形式长期保存。','settings.export':'导出备份','settings.import':'导入备份','settings.reset':'重置全部','settings.install':'安装 Pathline','settings.installHint':'如果浏览器支持，也可以使用“添加到主屏幕”或安装命令。',
      'study.before':'先别查资料','study.beforeDesc':'合上笔记，用一分钟解释这个知识点的核心逻辑。主动提取负责诊断；重读只负责修补漏洞。','study.start':'开始快速检测','study.why':'为什么现在学这个','study.current':'当前掌握度','study.correctNext':'答对 {c}/{a} 次 · 下次复习 {when}','study.noEvidence':'还没有主动提取证据','study.focus':'预计专注时间','study.minutes':'{n} 分钟',
      'quiz.label':'快速检测 · 第 {i}/{n} 题','quiz.confidence':'你对这个答案有多确定？','quiz.correct':'正确。','quiz.notQuite':'还差一点。','quiz.finish':'完成','quiz.next':'下一题','quiz.check':'检查答案','quiz.resultPerfect':'提取非常干净。','quiz.resultOkay':'这次结果很有价值。','quiz.resultRepair':'先修正心智模型，再重新尝试。','quiz.resultDesc':'当前掌握度为 {m}%。下次复习时间：{when}。复习间隔由正确率与自信度共同改变，而不是固定的连续打卡奖励。','quiz.backOverview':'返回总览','quiz.reviewTopic':'复习这个知识点',
      'modal.switch':'切换课程','modal.switchDesc':'每门课程都会独立保存掌握度与复习时间。','modal.create':'创建自定义课程','modal.resetTitle':'重置 Pathline？','modal.resetDesc':'这会清除此浏览器中的全部掌握度、复习计划、自定义课程和设置。','modal.resetEverything':'全部重置',
      'toast.moreMaterial':'请先添加更多源材料，再生成课程。','toast.pathGenerated':'学习路径已生成。','toast.readFile':'已读取 {name}','toast.goalUpdated':'每日目标已更新。','toast.examUpdated':'考试紧迫度已更新。','toast.backupExported':'备份已导出。','toast.backupImported':'备份已导入。','toast.backupFailed':'无法读取这份备份文件。',
      'reason.low mastery':'掌握度偏低','reason.review due':'复习已到期','reason.memory decay':'存在遗忘风险','reason.unlocks later topics':'可解锁后续知识点','reason.low confidence':'自信度偏低','reason.prerequisites not ready':'前置知识尚未准备好','reason.best next gain':'当前收益最高',
      'parser.server':'当前缺少原版 PDF / DOCX / PPTX 解析服务。请改用文本文件或粘贴材料。','parser.pdfDep':'PDF 解析需要一个很小的依赖。请运行：python3 -m pip install pypdf','parser.unsupported':'不支持的文件类型','parser.empty':'上传的文件为空。','parser.large':'文件超过 30 MB 限制。','parser.noText':'没有在文件中找到可读取的文本。扫描版 PDF 需要先进行 OCR。'
    }
  };

  const zh = {
    courses:{
      stats:{title:'AP Statistics',subtitle:'2026–27 新版课程框架'},
      micro:{title:'AP Microeconomics',subtitle:'官方 6 单元课程框架'},
      sat:{title:'Digital SAT',subtitle:'阅读与写作 + 数学官方能力域'},
      ielts:{title:'IELTS Academic',subtitle:'听力、阅读、写作、口语'}
    },
    units:{
      s1:{title:'探索单变量数据与数据收集'},s2:{title:'概率、随机变量与概率分布'},s3:{title:'分类数据推断：比例'},s4:{title:'定量数据推断：均值'},s5:{title:'回归分析'},
      m1:{title:'经济学基本概念'},m2:{title:'供给与需求'},m3:{title:'生产、成本与完全竞争模型'},m4:{title:'不完全竞争'},m5:{title:'要素市场'},m6:{title:'市场失灵与政府作用'},
      'sat-rw':{title:'阅读与写作',weight:'约 64 分钟'},'sat-m':{title:'数学',weight:'约 70 分钟'},
      il:{title:'听力',weight:'40 道题'},ir:{title:'阅读',weight:'60 分钟'},iw:{title:'写作',weight:'Task 1 + Task 2'},is:{title:'口语',weight:'11–14 分钟'}
    },
    topics:{
      s1t1:{title:'变量、分布与统计研究问题',summary:'把现实问题转化为变量、个体与可执行的统计调查。',objectives:['区分分类变量与定量变量','结合情境描述数据分布','写出聚焦且可研究的问题'],questions:[
        {prompt:'学校记录每位学生最喜欢的午餐选项。这属于哪类变量？',choices:['定量变量','分类变量','连续变量','配对变量'],explanation:'“最喜欢的午餐选项”记录的是类别标签，因此属于分类变量。'},
        {prompt:'描述一个定量变量的分布时，哪组信息最有价值？',choices:['只看均值','形状、中心、离散程度和异常特征','只看样本量','列出每一个数值'],explanation:'完整的分布描述应结合情境讨论形状、中心、离散程度和异常特征。'}]},
      s1t2:{title:'抽样、实验与偏差',summary:'判断数据如何被收集，以及研究设计允许你得出什么层级的结论。',objectives:['区分抽样研究与实验','识别常见偏差来源','把随机化与有效推断联系起来'],questions:[
        {prompt:'随机分配主要用来支持哪类结论？',choices:['推广到总体','因果关系','获得更大样本量','消除全部变异'],explanation:'随机分配有助于在处理组之间平衡潜在混杂变量，因此支持因果推断。'},
        {prompt:'关于学校午餐的自愿在线调查，最直接面临哪种问题？',choices:['仅仅是覆盖不足','自愿回应偏差','区组设计','配对设计'],explanation:'意见特别强烈的人更可能主动参与，因此容易产生自愿回应偏差。'}]},
      s2t1:{title:'概率规则与条件概率',summary:'用事件、补集、交集和条件概率对不确定性进行建模。',objectives:['应用加法与乘法规则','解释条件概率','识别独立事件'],questions:[
        {prompt:'若 P(A)=0.4，P(B)=0.5，且 A 与 B 独立，则 P(A 且 B)=？',choices:['0.1','0.2','0.45','0.9'],explanation:'独立事件的交集概率相乘：0.4×0.5=0.20。'},
        {prompt:'若 P(A|B)=P(A)，则 A 与 B 是……',choices:['互斥的','独立的','互为补集','不可能事件'],explanation:'在概率有定义的前提下，这个等式是独立性的一个判定条件。'}]},
      s2t2:{title:'随机变量与模拟',summary:'用数值表示随机结果，并通过模拟估计长期行为。',objectives:['计算期望值','解释随机变量的标准差','设计有效模拟'],questions:[{prompt:'期望值最合理的解释是……',choices:['最可能出现的一次结果','大量重复试验后的长期平均值','结果的中位数','可能出现的最大值'],explanation:'期望值描述的是重复很多次后结果的长期平均。'}]},
      s3t1:{title:'样本比例的抽样分布',summary:'利用抽样变异，把样本比例与总体比例联系起来。',objectives:['检查适用条件','描述中心与离散程度','恰当地使用正态近似'],questions:[{prompt:'对于样本比例，增大 n 通常会使抽样分布……',choices:['偏差更大','变异更小','无论 p 为何都更偏斜','以 0 为中心'],explanation:'样本量增大时，样本比例的标准差会减小。'}]},
      s3t2:{title:'比例的置信区间与假设检验',summary:'在满足条件的前提下，对总体比例进行估计与检验，并正确解释结果。',objectives:['构造并解释置信区间','写出原假设与备择假设','结合情境解释 p 值'],questions:[{prompt:'对一个 95% 置信区间，哪种解释最准确？',choices:['95% 的样本值都位于区间内','长期重复抽样时，该方法约有 95% 的区间会包含真实参数','这个固定参数有 95% 概率移动进当前区间','总体中 95% 的个体都位于区间内'],explanation:'置信水平描述的是重复抽样方法的长期覆盖率，而不是区间算出后给固定参数赋一个概率。'}]},
      s4t1:{title:'t 分布与均值推断',summary:'在检查研究设计与分布形态条件后，使用 t 方法估计和检验均值。',objectives:['选择单样本或双样本程序','解释 t 统计量','写出与参数对应的结论'],questions:[{prompt:'当总体标准差 σ 未知时，为什么使用 t 分布？',choices:['它能消除所有抽样变异','用样本标准差 s 估计 σ 会增加额外不确定性，t 分布对此进行修正','它能保证原始数据一定正态','它会把参数从 μ 变成 p'],explanation:'用样本标准差估计总体离散程度会引入额外不确定性，t 分布正是对此进行调整。'}]},
      s5t1:{title:'线性回归与残差',summary:'建立两个定量变量之间的关系模型，并判断线性模型是否合适。',objectives:['解释斜率与截距','使用残差分析','区分相关与因果'],questions:[
        {prompt:'残差等于……',choices:['观测 y − 预测 y','预测 y − 观测 y','相关系数的平方','斜率除以截距'],explanation:'残差 = 实际观测响应值 − 模型预测响应值。'},
        {prompt:'仅凭很强的相关性可以证明……',choices:['存在因果关系','不存在任何潜在变量','以上两项都不能证明','一定进行了随机分配'],explanation:'相关性衡量的是关联；因果关系还需要合适的研究设计与论证。'}]},
      m1t1:{title:'稀缺、机会成本与 PPC',summary:'用稀缺性和权衡来分析生产可能性。',objectives:['计算机会成本','解释 PPC 上的点与曲线移动','识别比较优势'],questions:[
        {prompt:'沿着向外弯曲的 PPC 移动，通常意味着机会成本……',choices:['保持不变','递增','为零','为负'],explanation:'向外弯曲的 PPC 反映了递增机会成本：资源越被转移到另一种生产活动，适配程度通常越低。'},
        {prompt:'比较优势由什么决定？',choices:['绝对产量','更低的机会成本','更高工资','更大人口'],explanation:'比较优势的核心是较低的机会成本。'}]},
      m2t1:{title:'需求、供给与均衡',summary:'区分沿曲线移动与整条曲线移动，并预测均衡变化。',objectives:['识别需求和供给的决定因素','分析需求与供给同时移动','计算短缺与过剩'],questions:[{prompt:'对于正常品，消费者收入上升使需求曲线右移。在原价格下，市场最初会出现……',choices:['过剩','短缺','有约束力的价格下限','只有无谓损失'],explanation:'需求增加，而原价格下的供给暂未变化，因此需求量会超过供给量，形成短缺。'}]},
      m2t2:{title:'弹性与政府政策',summary:'衡量市场反应程度，并分析税收、价格上限和价格下限。',objectives:['计算弹性','把弹性与总收益联系起来','分析税负归宿'],questions:[{prompt:'当需求相对缺乏弹性时，单位税的税负往往更多落在……',choices:['消费者','生产者','政府','只有外国企业'],explanation:'市场中弹性更小的一方通常承担更大比例的税负。'}]},
      m3t1:{title:'成本与利润最大化',summary:'把生产决策连接到成本曲线，并选择使利润最大化的产量。',objectives:['区分会计利润与经济利润','理解 MC、AVC 与 ATC 的关系','应用 MR=MC'],questions:[{prompt:'对完全竞争厂商而言，利润最大化的产量通常满足……',choices:['只有 P=ATC','MR=MC，且继续生产优于停产','无论成本如何只要 TR 最大','AVC 最小'],explanation:'厂商在 MR=MC 处选择产量，同时还要结合停产条件判断是否生产。'}]},
      m4t1:{title:'垄断与价格歧视',summary:'比较垄断市场与完全竞争市场的决策和结果。',objectives:['使用需求曲线和 MR 曲线','识别配置无效率','分析价格歧视'],questions:[{prompt:'单一价格垄断者选择产量的位置是……',choices:['P=MC','MR=MC','ATC 最小','需求弹性恰好为 1'],explanation:'垄断者先在 MR=MC 处确定利润最大化产量，再回到需求曲线上找到价格。'}]},
      m5t1:{title:'劳动需求与资源市场',summary:'把劳动需求理解为派生需求，并分析利润最大化的资源投入。',objectives:['计算 MRP','使用 MRP=MRC','解释劳动需求曲线移动'],questions:[{prompt:'利润最大化的竞争性厂商会雇佣劳动直到……',choices:['工资 = 产品价格','MRP = MRC','MP = 0','总产量最大'],explanation:'只要新增一单位劳动带来的边际收益产品仍能覆盖边际资源成本，厂商就会继续雇佣。'}]},
      m6t1:{title:'外部性、公共物品与不平等',summary:'识别市场为何会错误配置资源，并评估政策应对方式。',objectives:['区分私人成本与社会成本','识别公共物品','分析纠正性政策'],questions:[{prompt:'负的生产外部性意味着边际社会成本通常……',choices:['低于边际私人成本','高于边际私人成本','等于边际收益','为零'],explanation:'外部成本使社会承担的真实成本高于生产者自己承担的私人成本。'}]},
      'sat-i':{title:'信息与观点',summary:'精读、推断、中心思想与证据。',objectives:['找出中心思想','做出有文本依据的推断','使用文字与定量证据'],questions:[{prompt:'SAT 推断题中，最强的答案通常是……',choices:['加入合理的课外知识','被文章最直接支持的选项','词汇最复杂的选项','重复标题的选项'],explanation:'SAT 推断必须建立在文本已经提供的证据上，而不是依赖外部假设。'}]},
      'sat-c':{title:'文本结构与修辞',summary:'语境词义、作者目的、结构与跨文本关系。',objectives:['根据语境推断词义','识别修辞目的','比较相关文本'],questions:[{prompt:'做 Words in Context 题时，最先应该关注……',choices:['词典里最罕见的释义','所在句及其前后的逻辑','最长的选项','听起来最积极的选项'],explanation:'真正决定词义的是上下文逻辑，而不是词典中最少见或最“高级”的释义。'}]},
      'sat-e':{title:'观点表达',summary:'修辞综合与逻辑衔接。',objectives:['选择与写作目标匹配的证据','使用逻辑准确的过渡词'],questions:[{prompt:'选择最佳过渡词时，最重要的依据是……',choices:['句子长度','前后观点之间的逻辑关系','听起来是否正式','词是否少见'],explanation:'过渡词编码的是对比、延续、因果、举例等逻辑关系。'}]},
      'sat-g':{title:'标准英语规范',summary:'句子边界、主谓一致、修饰语与标点。',objectives:['控制从句与句子边界','保持语法一致','按结构使用标点'],questions:[{prompt:'两个独立分句可以正确地用什么连接？',choices:['只用逗号','分号','完全不加标点','任何情况下都用冒号'],explanation:'分号可以连接两个意义紧密相关的独立分句。'}]},
      'sat-a':{title:'代数',summary:'一次方程、函数、方程组与不等式。',objectives:['解一次方程','解释斜率和截距','解方程组'],questions:[{prompt:'若 3x+5=20，则 x 等于……',choices:['3','5','8','15'],explanation:'两边先减 5，再除以 3，得到 x=5。'}]},
      'sat-am':{title:'高等数学',summary:'非线性表达式、函数与方程。',objectives:['因式分解并改写表达式','解二次方程','分析指数关系'],questions:[{prompt:'若 x²−9=0，则解为……',choices:['只有 3','只有 −3','±3','9'],explanation:'x²=9，因此 x=3 或 x=−3。'}]},
      'sat-p':{title:'问题解决与数据分析',summary:'比率、百分比、数据、概率与推断。',objectives:['使用比例和单位','分析数据','解释抽样结论'],questions:[{prompt:'价格从 80 上升到 100，百分比增长是多少？',choices:['20%','25%','80%','125%'],explanation:'增加量为 20，基数为 80，因此 20/80=25%。'}]},
      'sat-gt':{title:'几何与三角',summary:'面积、体积、三角形、圆与三角函数。',objectives:['应用几何关系','使用直角三角函数','分析圆'],questions:[{prompt:'在直角三角形中，sin θ 等于……',choices:['邻边/斜边','对边/斜边','对边/邻边','斜边/对边'],explanation:'正弦定义为对边除以斜边。'}]},
      il1:{title:'预测、信号词与答案形式',summary:'听结构，而不是试图追上每一个单词。',objectives:['预测答案类型','跟踪信号词','检查拼写与数字形式'],questions:[{prompt:'音频开始前，通常最有价值的第一步是什么？',choices:['翻译每一个词','预测每个空需要什么类型的答案','忽略题目说明','记住所有选项'],explanation:'提前预测答案类型可以降低处理负担，并帮助你在音频中更快捕捉目标信息。'}]},
      ir1:{title:'文章地图与证据定位',summary:'先掌握段落功能，再基于证据作答，而不是凭印象。',objectives:['快速浏览文章结构','定位同义改写后的证据','区分 Not Given 与 False'],questions:[{prompt:'在 True/False/Not Given 中，“Not Given”意味着……',choices:['陈述大概率是错的','文章没有提供足够信息判断','陈述用了不同措辞','答案藏在另一篇文章里'],explanation:'Not Given 表示文章没有建立题目所需要的那层信息关系。'}]},
      iw1:{title:'Task 1：信息筛选、概述与比较',summary:'筛选主要特征并组织比较，而不是逐个罗列所有数字。',objectives:['写出清晰 overview','有逻辑地分组数据','使用准确的比较表达'],questions:[{prompt:'优秀的 Academic Task 1 overview 主要应该……',choices:['列出所有数值','概括最主要的趋势或关键特征','解释图表没有给出的原因','表达个人观点'],explanation:'Overview 应抓住主要特征，既不虚构原因，也不需要把全部数据逐一复述。'}]},
      iw2:{title:'Task 2：论证结构',summary:'建立清晰立场，用有逻辑的段落功能和充分展开的证据支撑论点。',objectives:['回答题目每一个部分','展开因果推理','保持精确一致的立场'],questions:[{prompt:'例子能提升 Task 2 段落质量，最主要是因为它们……',choices:['自动增加字数','让推理变得具体且可检验','可以代替解释','保证使用 Band 9 词汇'],explanation:'例子的价值在于澄清并支撑推理，而不是单纯增加篇幅。'}]},
      is1:{title:'流利度、展开能力与灵活语言',summary:'自然回答、补充相关细节，并在表达卡住时顺畅恢复。',objectives:['不依赖背诵模板展开回答','灵活改述','使用例子和小故事'],questions:[{prompt:'Speaking 中，背诵答案最大的风险是什么？',choices:['考官讨厌一切准备','回答可能显得僵硬，无法自然回应当前具体问题','长答案被禁止','使用习语会降分'],explanation:'提前准备表达没有问题，但僵硬脚本往往会降低回应性与自然展开能力。'}]}
    }
  };

  function format(str, vars={}){return String(str).replace(/\{(\w+)\}/g,(_,k)=>vars[k] ?? `{${k}}`)}
  function t(lang,key,vars={}){const pack=ui[lang]||ui.en;return format(pack[key] ?? ui.en[key] ?? key,vars)}
  function course(lang,c,field){if(lang!=='zh'||!c||!zh.courses[c.id])return c?.[field];return zh.courses[c.id][field] ?? c[field]}
  function unit(lang,u,field){if(lang!=='zh'||!u||!zh.units[u.id])return u?.[field];return zh.units[u.id][field] ?? u[field]}
  function topic(lang,tpc,field){if(lang!=='zh'||!tpc||!zh.topics[tpc.id])return tpc?.[field];return zh.topics[tpc.id][field] ?? tpc[field]}
  function objectives(lang,tpc){if(lang!=='zh'||!tpc||!zh.topics[tpc.id]?.objectives)return tpc?.objectives||[];return zh.topics[tpc.id].objectives}
  function question(lang,tpc,index,q){if(lang!=='zh'||!tpc||!zh.topics[tpc.id]?.questions?.[index])return q;const z=zh.topics[tpc.id].questions[index];return {...q,...z,answer:q.answer}}
  function reason(lang,r){return t(lang,`reason.${r}`)}
  return {t,course,unit,topic,objectives,question,reason,ui,zh};
})();
