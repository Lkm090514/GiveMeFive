(async () => {
  'use strict';
  // Task logic stays independent of the page so core transitions can be checked directly.
  const rangeOf = text => {
    const match = text.match(/(\d{1,4})\s*[-–—~～至到]\s*(\d{1,4})/);
    if (!match) return null;
    const a = Number(match[1]), b = Number(match[2]);
    return a >= 1 && b > a && b - a < 400 ? {a, b, match:match[0]} : null;
  };
  function suggest(goal, lang = 'zh') {
    const range = rangeOf(goal);
    if (range) {
      const count = range.b - range.a + 1;
      const size = count <= 3 ? count : count <= 12 ? 3 : Math.ceil(count / 6);
      const result = [];
      const pages = /页|pages?/i.test(goal);
      for (let i = range.a; i <= range.b; i += size) {
        const end = Math.min(i + size - 1, range.b), nums = i === end ? `${i}` : `${i}–${end}`;
        result.push(lang === 'zh' ? `${pages ? '阅读' : '完成'}第 ${nums} ${pages ? '页' : '题'}` : `${pages ? 'Read pages' : 'Questions'} ${nums}`);
      }
      return result;
    }
    if (/阅读|读|reading|read|chapter|biology/i.test(goal)) return lang === 'zh'
      ? ['读完第一个小节，标出不理解的地方', '读完剩余内容，标出需要再看的地方']
      : ['Read the first section and mark unclear points', 'Read the remaining sections and mark what to revisit'];
    if (/写|essay|writ|introduction/i.test(goal)) return lang === 'zh'
      ? ['写下这一段的核心观点', '围绕观点写出完整草稿', '读一遍，调整不清楚的句子']
      : ['Write the central idea for this section', 'Write a complete rough draft', 'Read it once and clarify unclear sentences'];
    return [lang === 'zh' ? `先推进「${goal}」中一个明确的小部分（请改成具体动作）` : `One concrete small part of “${goal}” (edit this into an action)`];
  }
  function createRun(goal, titles, mode, duration, now = Date.now()) {
    if (!goal.trim() || !titles.length || titles.length > 50 || titles.some(t => !t.trim() || t.length > 200)) throw new Error('Invalid task');
    if (!['free','focus'].includes(mode) || !Number.isInteger(duration) || duration < 1 || duration > 240) throw new Error('Invalid duration');
    return {goal, steps:titles.map((title,i) => ({id:i+1,title:title.trim(),status:'pending',micro:null,smallDone:[]})), current:1, nextId:titles.length+1, mode, duration, remaining:duration*60000, elapsed:0, clock:now, paused:false, expired:false,notes:[],started:true};
  }
  const currentStep = run => run.steps.find(s => s.id === run.current);
  function clockAdvance(run, now = Date.now()) {
    const delta = Math.max(0, now - run.clock); run.clock = now;
    if (run.paused) return;
    const spent = run.mode === 'focus' ? Math.min(delta, run.remaining) : delta;
    run.elapsed += spent;
    if (run.mode === 'focus') { run.remaining = Math.max(0,run.remaining-delta); if (!run.remaining) {run.paused=true;run.expired=true;} }
  }
  function completeStep(run) {
    const step = currentStep(run);
    if (!step || step.status !== 'pending' || run.paused) return false;
    if (step.micro) {step.smallDone.push(step.micro);step.micro=null;return 'micro';}
    step.status = 'done'; run.current = run.steps.find(s => s.status === 'pending')?.id ?? null;
    return 'done';
  }
  function skipStep(run) {
    const step = currentStep(run); if (!step || run.paused) return false;
    step.status = 'skipped';run.current = run.steps.find(s => s.status === 'pending')?.id ?? null;return true;
  }
  function shrinkStep(run, text, suggestion) {
    const step = currentStep(run);
    if (!step || step.micro || !text.trim() || text.length > 200 || step.smallDone.includes(text.trim())) return false;
    const range = rangeOf(step.title);
    // Numeric ranges are split without dropping or prematurely completing the remaining work.
    if (range && text.trim() === suggestion) {
      const rest = range.a+1 === range.b ? `${range.b}` : `${range.a+1}–${range.b}`;
      const remainder = {...step,id:run.nextId++,title:step.title.replace(range.match,rest),smallDone:[]};
      step.title = text.trim();run.steps.splice(run.steps.indexOf(step)+1,0,remainder);
    } else step.micro = text.trim();
    return true;
  }
  function methodHint(task, goal, language) {
    const methods = [
      [/用自己的话|解释|复述|讲清|说清|总结|归纳|回忆|复习|背诵|记忆|explain|recall|summari[sz]e|own words/i, ['暂时不看材料，试着说清最重要的关系，说不清的地方再回去看。', 'Explain the key idea without notes; revisit what you cannot explain.']],
      [/检查|核对|订正|修改|调整.*句|校对|review|revise|edit|check/i, ['先通读一遍，找出一处不清楚的地方，再针对它修改。', 'Read it through, find one unclear part, then revise that part.']],
      [/读.*要求|圈出.*条件|read.*requirements/i, ['先完整读一遍要求，圈出已知条件和需要解决的问题。', 'Read the task; circle what is given and what you need to find.']],
      [/题|例题|练习|习题|检验|question|exercise|problem|practice|test/i, ['先独立尝试，做完后再检查哪里没理解。', 'Try it on your own, then check what you did not understand.']],
      [/听|看完|观看|视频|课|lecture|watch|listen|video/i, ['先完整听或看这一小段，不懂的地方先标记，不急着马上查。', 'Go through this section once; mark unclear points to revisit.']],
      [/读|阅读|read|chapter/i, ['先连贯读完这一小段，标出不清楚的地方，读完再回看。', 'Read this section through; mark unclear points, then revisit.']],
      [/观点|提纲|构思|outline|central idea/i, ['先写下最想表达的一句话，再围绕它列出要点。', 'Write your main idea, then list the points that support it.']],
      [/写|草稿|essay|writ|draft|introduction/i, ['先写出粗糙但完整的一段，写完再调整表达。', 'Write a rough but complete paragraph, then refine the wording.']]
    ];
    const match = methods.find(([pattern]) => pattern.test(task)) || methods.find(([pattern]) => pattern.test(goal));
    return match ? match[1][language === 'en' ? 1 : 0] : language === 'en'
      ? 'Do the smallest concrete action; mark a blocker before moving on.'
      : '先做最小的一个具体动作，卡住的地方先标出来，再继续往下做。';
  }
  function completedEvents(records) {
    return Array.isArray(records) ? records.filter(item => item?.endedNormally !== false && typeof item?.date === 'string' && Array.isArray(item?.steps) && item.steps.length > 0).length : 0;
  }
  function prepareResume(session, now = Date.now()) {
    session.paused = true;
    session.clock = now;
    session.notes = Array.isArray(session.notes) ? session.notes.filter(note => typeof note?.text === 'string' && typeof note?.title === 'string') : [];
    session.started = session.started !== false;
    return session;
  }
  function carryRun(previous, now = Date.now()) {
    const remaining = previous.steps.filter(step => step.status !== 'done');
    if (!remaining.length) return null;
    const next = createRun(previous.goal,remaining.map(step => step.title),previous.mode,previous.duration,now);
    next.paused = true; next.started = false;
    next.steps.forEach((step,index) => { step.micro = remaining[index].micro || null; });
    next.notes = (previous.notes || []).filter(note => remaining.some(step => step.id === note.taskId)).map(note => ({...note,taskId:next.steps[remaining.findIndex(step => step.id === note.taskId)].id}));
    return next;
  }
  function taskType(task, goal) {
    const types = [[/背诵|记忆|单词|memor|vocab/i,'memory'],[/题|练习|检验|question|exercise|problem|practice/i,'practice'],[/读|阅读|听|课|看|read|chapter|lecture|watch|listen/i,'reading'],[/写|草稿|essay|writ|draft|introduction/i,'writing']];
    return (types.find(([pattern]) => pattern.test(task)) || types.find(([pattern]) => pattern.test(goal)))?.[1] || 'general';
  }
  if (typeof module !== 'undefined' && module.exports) {module.exports={suggest,createRun,currentStep,clockAdvance,completeStep,skipStep,shrinkStep,rangeOf,methodHint,completedEvents,prepareResume,carryRun,taskType};return;}

  const $ = id => document.getElementById(id);
  await GMFShared.init();GMFShared.mount('mindflow');
  const context=null,bridge=null,STORE='mindflow.session.v1',HISTORY='mindflow.history.v1',SETTINGS='flownext.settings.v1';
  let values=await LearningStore.getModule('mf-focus');
  if(!values){values={};for(const key of [STORE,HISTORY,SETTINGS,'mindflow.tutorial.v1']){try{values[key]=JSON.parse(localStorage.getItem(key));}catch{}}await LearningStore.putModule('mf-focus',values);}
  const read=(key,fallback)=>values[key]??fallback;
  const write=(key,value)=>{values[key]=value;LearningStore.commit('mf-focus',values,null,run?.study_session).catch(()=>{if(run)run.paused=true;toast(t('storageError'));});return true;};
  let lastInput=Date.now();
  const activeInput=()=>{lastInput=Date.now();};['pointerdown','keydown','wheel','touchstart'].forEach(e=>document.addEventListener(e,activeInput,{passive:true}));
  function advanceRun(){if(!run)return;const now=Date.now(),before=run.elapsed;
    if(run.paused||document.hidden||!navigator.onLine||now-lastInput>120000){run.paused=true;run.clock=now;return;}
    const start=run.clock;clockAdvance(run,Math.min(now,lastInput+120000));run.clock=now;
    if(run.study_session){PathlineSessions.credit(run.study_session,start,start+(run.elapsed-before),lastInput,true);}
  }
  const settings = GMFShared.preferences();
  let lang = settings.lang === 'en' ? 'en' : 'zh';
  const pt=(text,vars={})=>window.PathlineUI?window.PathlineUI.t(lang,text,vars):text;
  let theme = settings.theme === 'dark' ? 'dark' : 'light';
  let run = read(STORE,null), draft = null, record = null, page = 'setup-view', locked = false, toastTimer;
  if (run && (!Array.isArray(run.steps) || !run.steps.length || !Number.isFinite(run.clock) || !Number.isFinite(run.remaining) || !Number.isFinite(run.elapsed) || !['free','focus'].includes(run.mode) || run.steps.some(s => typeof s.title !== 'string' || !Array.isArray(s.smallDone) || !['pending','done','skipped'].includes(s.status)))) run=null;
  if(run){prepareResume(run);if(!run.study_session){run.study_session=GMFShared.session(run.shared_context||GMFShared.context,'learn');run.study_session.active_seconds=run.elapsed/1000;run.study_session.daily_seconds[PathlineSessions.dayKey()]=run.elapsed/1000;}}
  const TUTORIAL = 'mindflow.tutorial.v1';
  const zh = {};
  document.querySelectorAll('[data-i18n]').forEach(el => {zh[el.dataset.i18n]=el.innerHTML;});
  zh.goalPlaceholder = $('goal').placeholder;
  Object.assign(zh,{merge:'合并下一段',remove:'删除',step:'第 {n} 段',editStep:'第 {n} 段任务',limit:'最多添加 50 段；建议只安排这一轮能推进的内容。',needStep:'请至少写下一段具体任务。',freeModeInfo:'自由模式 · 不设倒计时',focusModeInfo:'专注模式 · {n} 分钟',doneCount:'已完成 {n} / {total} 段',remainingCount:'还剩 {n} 段',steady:'按自己的节奏，做完后再点完成。',original:'接着回来完成：{title}',microDone:'已推进：{title}',noNext:'完成这一段，就可以回看本轮推进。',returnNext:'还有 {n} 段，等你稍后回来。',paused:'已暂停',resume:'继续',resumeExtra:'继续 10 分钟',timeLeft:'本轮剩余',doneNotice:'这一段完成。',microNotice:'这个小动作完成。接着回到原任务。',skipNotice:'已放到「稍后回来」，没有算作完成。',pauseNotice:'休息一下。准备好后再继续。',summaryTime:'学习用时',summaryCompleted:'完成任务段',lessMinute:'不到 1 分钟',minutes:'{n} 分钟',noneDone:'这一轮还没有标记完成的任务。',nonePending:'这一轮安排的任务都已完成。',smallProgress:'小步推进：{title}',returnTo:'继续：{title}',noHistory:'还没有学习记录。结束第一轮后，真实推进会留在这里。',historyMeta:'完成 {done}/{total} 段 · {minutes}',details:'查看完成与待办',current:'当前：{title}',noCurrent:'还有任务留在「稍后回来」。',storageError:'浏览器暂时无法保存；本页仍可使用，关闭后进度可能丢失。',shrinkAgain:'先完成眼前这个小动作，或跳过后稍后回来。',readFirst:'先读懂「{title}」的要求，并标出一个不清楚的地方',hintRange:'先读当前第一题：圈出已知条件和要找的量，再写下能用上的一个关系。',hintRead:'先读当前小节的第一段，标出一句你还不理解的话。',hintWrite:'先写一句你最想表达的话，不急着修改。',hintGeneral:'先写下当前最需要解决的一个问题，再找出能立刻做的第一个动作。',waitPaused:'当前已暂停，准备好后点击继续。',stepDone:'已完成',stepPending:'待完成',stepSkipped:'稍后回来',themeDark:'切换到深色模式',themeLight:'切换到浅色模式',close:'关闭',emptySmall:'写一个具体的小动作，避免重复已完成的动作。'});
  const en = {history:'Study log',introIndex:'Find your own way forward',headline:'A little closer.<br>One step at a time.',introCopy:'You do not need to finish everything at once. Make the task smaller, then give this one part your attention.',pathCaption:'Every filled dot is a step you actually took.',goalLabel:'What is this session for?',goalPlaceholder:'e.g. AP Physics homework 1–12',tryExample:'Try',examplePhysics:'Physics 1–12',exampleReading:'Read chapter 3',exampleWriting:'Write an essay intro',modeLabel:'Your pace, your choice',freeMode:'Free mode',freeDesc:'No countdown. Just progress.',focusMode:'Focus mode',focusDesc:'A little structure for your time.',durationLabel:'Focus duration',custom:'Custom',minuteUnit:'min',planButton:'Break it into smaller steps',setupNote:'Review the suggestions and make them your own.',back:'Back to setup',planKicker:'Make the next step clear',planHeading:'One small part is enough.',planNote:'These suggestions use task keywords. Edit, merge or add steps so each has a clear finish.',addStep:'+ Add a step',begin:'Begin with the first step',currentRun:'Moving forward',stop:'End this session',onlyJob:'Your only task right now',pause:'Pause',complete:'Complete this step',stuck:"I'm stuck",rescueHeading:'How would you like to continue?',collapse:'Close',shrink:'Make this task smaller',hint:'Give me a next-step hint',skip:'Skip for now',smallLabel:'One small action you can finish',smallNote:'After this small action, the original task stays here for you to continue.',smallBegin:'Start with this',runProgress:'Your path',nextLabel:'Coming up',later:'Come back later',breathing:'Try another starting point',laterHeading:'They are still here.',laterDesc:'Skipped tasks are not completed. Pick one to return to, or end with the progress you made.',runComplete:'Session complete',summaryHeading:'This is your progress.',completed:'Completed',unfinished:'Still to do',newRun:'Another session',end:'Finish',footer:'A little help to begin. Space to focus.',gentleReminder:'A gentle reminder',timeUp:'This session’s time is up',timeDesc:'Time is only a guide. Every bit of work still counts.',extend:'Continue for 10 minutes',break:'Take a break',yourRuns:'The steps you actually took',storageNote:'Saved only in this browser. Not synced across devices.',merge:'Merge next',remove:'Delete',step:'Step {n}',editStep:'Task for step {n}',limit:'Up to 50 steps. Plan only what fits this session.',needStep:'Add at least one concrete task.',freeModeInfo:'Free mode · no countdown',focusModeInfo:'Focus mode · {n} min',doneCount:'{n} / {total} steps complete',remainingCount:'{n} steps remaining',steady:'Work at your pace. Mark it complete when it is done.',original:'Then return to: {title}',microDone:'Already progressed: {title}',noNext:'After this step, see what you moved forward.',returnNext:'{n} steps are waiting for you to come back.',paused:'Paused',resume:'Resume',resumeExtra:'Continue 10 minutes',timeLeft:'Session left',doneNotice:'This step is complete.',microNotice:'Small action done. Now return to the original task.',skipNotice:'Moved to Come back later. Not marked complete.',pauseNotice:'Take a breath. Resume when you are ready.',summaryTime:'Study time',summaryCompleted:'Steps completed',lessMinute:'Under 1 min',minutes:'{n} min',noneDone:'No tasks marked complete this session.',nonePending:'Every planned task is complete.',smallProgress:'Small progress: {title}',returnTo:'Return to: {title}',noHistory:'No sessions yet. Your progress will appear here after your first session.',historyMeta:'{done}/{total} steps · {minutes}',details:'View completed and remaining',current:'Current: {title}',noCurrent:'Some tasks are waiting in Come back later.',storageError:'Browser storage is unavailable. You can continue, but progress may be lost when this page closes.',shrinkAgain:'Finish this small action first, or skip and return later.',readFirst:'Read the requirements of “{title}” and mark one unclear point',hintRange:'Read the first question. Circle the known values and what you need to find, then write one useful relationship.',hintRead:'Read the first paragraph and mark one sentence that is not clear yet.',hintWrite:'Write one sentence that says what you mean. Do not edit yet.',hintGeneral:'Name the first problem you need to solve, then identify one action you can take now.',waitPaused:'Paused. Press Resume when you are ready.',stepDone:'Complete',stepPending:'To do',stepSkipped:'Come back later',themeDark:'Switch to dark mode',themeLight:'Switch to light mode',close:'Close',emptySmall:'Write one concrete action that is not already completed.'};
  Object.assign(zh,{completedEvents:'已完成事件',clearHistory:'清空记录',confirmClearHistory:'确定清空全部学习记录吗？\n此操作无法撤销。',clearHistoryError:'未能清空学习记录，请检查浏览器存储权限后再试。'});
  Object.assign(en,{completedEvents:'Completed events',clearHistory:'Clear history',confirmClearHistory:'Clear all study history?\nThis cannot be undone.',clearHistoryError:'Could not clear history. Check browser storage permissions and try again.'});
  Object.assign(en,{confirmClearHeading:'Clear all study history?',confirmClearWarning:'This cannot be undone.'});
  Object.assign(zh,{
    freeDesc:'正向计时，按自己的节奏',freeModeInfo:'自由模式 · 正向计时',focusMode:'定时模式',focusModeInfo:'定时模式 · {n} 分钟',begin:'开始这一轮',rescueHeading:'需要一点帮助？',hint:'给我一个小提示',skip:'先跳过，稍后回来',timeElapsed:'本轮已进行',moveUp:'上移',moveDown:'下移',cancel:'取消',leaveNote:'留一个卡点',noteLabel:'一句话，记下现在没弄懂的地方',notePlaceholder:'例如：不懂 chain rule 为什么要乘里面的导数',saveNote:'保存并继续',noteSaved:'卡点已留下，先继续眼前这一段。',sessionNotes:'本轮留下的卡点',welcomeBack:'从上次的地方接上',resumeHeading:'继续上一轮',endPrevious:'结束上一轮',resumeTime:'已学习 {time}',resumeRemaining:'定时模式 · 剩余 {time}',continueLater:'下次继续',nextReady:'下次从这里继续',hasUnfinished:'有未完成任务',allFinished:'本轮任务已完成',reviewTutorial:'重新查看教程',tutorialHeading:'用半分钟，认识 Mind Flow',skipTutorial:'跳过',tutorialTask:'写下这一轮要完成什么',tutorialTaskText:'例如 AP Physics 作业 1–12，先拆成几段，一次处理眼前的一段。',tutorialCard:'学习时，只看主任务卡片',tutorialCardText:'做好当前这一段，点“完成这一段”，下一段就会自然接上。',tutorialMode:'选择自己的时间节奏',tutorialModeText:'自由模式记录已学习多久；定时模式给这一轮设置时间边界。',tutorialHelp:'真正卡住时，再打开帮助',tutorialHelpText:'点“卡住了”获得简短提示，或留一句卡点，不会扣分或清空进度。',tutorialStart:'开始使用'
  });
  Object.assign(en,{
    freeDesc:'Count up, at your own pace',freeModeInfo:'Free mode · count up',focusMode:'Timed mode',focusModeInfo:'Timed mode · {n} min',begin:'Start this session',rescueHeading:'Need a little help?',hint:'Give me a small hint',skip:'Skip and come back later',timeElapsed:'Session elapsed',moveUp:'Move up',moveDown:'Move down',cancel:'Cancel',leaveNote:'Leave a blocker',noteLabel:'One sentence about what is unclear',notePlaceholder:'e.g. Why multiply by the inner derivative in the chain rule?',saveNote:'Save and continue',noteSaved:'Blocker saved. Continue with this step.',sessionNotes:'Blockers from this session',welcomeBack:'Pick up where you left off',resumeHeading:'Continue your last session',endPrevious:'End the previous session',resumeTime:'Studied {time}',resumeRemaining:'Timed mode · {time} left',continueLater:'Continue next time',nextReady:'Ready for next time',hasUnfinished:'Unfinished tasks remain',allFinished:'All planned tasks complete',reviewTutorial:'Review the tutorial',tutorialHeading:'Meet Mind Flow in half a minute',skipTutorial:'Skip',tutorialTask:'Write the task for this session',tutorialTaskText:'For example, AP Physics 1–12. Split it into smaller parts and work on one at a time.',tutorialCard:'Focus on the current task card',tutorialCardText:'Finish this part and press Complete this step. The next part follows naturally.',tutorialMode:'Choose your time boundary',tutorialModeText:'Free mode counts time studied. Timed mode gives this session a time boundary.',tutorialHelp:'Open help when you need it',tutorialHelpText:'Get a short hint or leave a blocker. Getting stuck never takes away progress.',tutorialStart:'Start using Mind Flow'
  });
  const helpCopy = {
    zh:{
      general:[['帮我理清思路','先写清你想得到什么结果，再找出眼前能做的第一个动作。'],['换一种方式理解','换一个你熟悉的例子，试着用它说明当前内容。'],['给我一个小提示','先指出你卡住的那一步，只处理它前面的一个小动作。']],
      reading:[['帮我找出没懂的部分','先指出一句没听懂或没读懂的话，再说清是哪个词或关系不明白。'],['换一种方式理解','试着用日常说法重述这一小段，再对照材料找出漏掉的关系。'],['给我一个小提示','先找这一小段最关键的一句话，其余细节稍后再看。']],
      practice:[['帮我整理已知条件','把已知条件和要求的结果分开写，先不急着计算。'],['提醒我应该先想什么','先画图或写出相关关系，看看哪一步能把已知条件连到目标。'],['给我一个小提示','只写下第一个可能用上的关系，再试着往下推一步。']],
      memory:[['帮我建立一个联想','把要记的内容和一个熟悉的画面联系起来，再试着回忆。'],['换一种方式记住','用要记的内容写一个与你有关的短句，再检查用法。'],['给我一个小提示','先遮住答案，只回忆一个关键词，再顺着它补全。']],
      writing:[['帮我理清思路','先写清这一段最想表达的一点，再围绕它补一句理由。'],['换一种方式表达','先像讲给同学听一样说出这段话，再写下来。'],['给我一个小提示','先写一句不完整的草稿，暂时不用修改措辞。']]
    },
    en:{
      general:[['Help me think it through','Name the result you want, then identify the first action you can take.'],['Try another way to understand','Use a familiar example to explain the idea to yourself.'],['Give me a small hint','Name the blocked step and do the small action just before it.']],
      reading:[['Find what I did not understand','Pick one unclear sentence and name the word or relationship that is unclear.'],['Try another way to understand','Restate this short section in everyday words, then compare with the material.'],['Give me a small hint','Find the key sentence in this section; leave the details for later.']],
      practice:[['Organize the given information','Write the known information and the target separately before calculating.'],['What should I think about first?','Draw a diagram or a relationship linking the given information to the target.'],['Give me a small hint','Write one relationship that might help and try one more step.']],
      memory:[['Build an association','Link the material to a familiar image, then try recalling it.'],['Try another way to remember','Use the material in a sentence about yourself and check its use.'],['Give me a small hint','Cover the answer, recall one keyword, then fill in the rest.']],
      writing:[['Help me think it through','Write the main point of this paragraph, then add one reason.'],['Try another way to express it','Say it as if explaining to a friend, then write it down.'],['Give me a small hint','Write one rough sentence and leave the wording for later.']]
    }
  };
  const t = (key,vars={}) => String((lang==='zh'?zh:en)[key] ?? zh[key] ?? key).replace(/\{(\w+)\}/g,(_,k)=>vars[k]??'');
  const el = (tag,text,className) => {const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node;};
  const button = (text,action,className='text-button') => {const node=el('button',text,className);node.type='button';node.addEventListener('click',action);return node;};
  const save = () => write(STORE,run);
  const timeText = ms => {const sec=Math.floor(ms/1000);return `${String(Math.floor(sec/60)).padStart(2,'0')}:${String(sec%60).padStart(2,'0')}`;};
  const minutesText = ms => ms<60000?t('lessMinute'):t('minutes',{n:Math.floor(ms/60000)});
  const show = name => {$('mf-home').classList.add('hidden');document.querySelector('.shell').classList.remove('hidden');page=name;for(const id of ['setup-view','plan-view','run-view','later-view','summary-view','resume-view'])$(id).classList.toggle('hidden',id!==name);};
  function toast(message){$('toast').textContent=message;$('toast').classList.add('show');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('show'),2600);}
  function applyTheme(){document.body.classList.toggle('dark',theme==='dark');document.querySelector('meta[name="theme-color"]').content=theme==='dark'?'#15181D':'#F5F7FB';$('theme-toggle').setAttribute('aria-label',t(theme==='dark'?'themeLight':'themeDark'));$('theme-toggle').title=t(theme==='dark'?'themeLight':'themeDark');}
  function applyLanguage(){
    document.querySelectorAll('[data-pl-aria]').forEach(e=>e.setAttribute('aria-label',pt(e.dataset.plAria)));
    document.querySelectorAll('[data-pl-text]').forEach(e=>e.textContent=pt(e.dataset.plText));document.querySelectorAll('[data-pl-placeholder]').forEach(e=>e.placeholder=pt(e.dataset.plPlaceholder));
    if(context&&run&&window.PathlineUI){const dictionary=window.PathlineUI.dictionary;for(const step of run.steps){const zh=Object.keys(dictionary).find(k=>dictionary[k]===step.title)||step.title;step.title=pt(zh);}}
    document.documentElement.lang=lang==='zh'?'zh-CN':'en';document.title=lang==='zh'?'Mind Flow · 一点点，向前走':'Mind Flow · One step at a time';
    document.querySelectorAll('[data-i18n]').forEach(node=>{if(node.dataset.i18n==='headline')node.innerHTML=t('headline');else node.textContent=t(node.dataset.i18n);});
    document.querySelectorAll('[data-i18n-placeholder]').forEach(node=>node.placeholder=t(node.dataset.i18nPlaceholder));
    $('language-toggle').textContent=lang==='zh'?'EN':'中';$('history-close').setAttribute('aria-label',t('close'));applyTheme();
    if(draft&&page==='plan-view')renderPlan();if(run){if(page==='resume-view')showResume();else if(page==='run-view'||page==='later-view')renderRun();}
    if(page==='summary-view'&&record)renderSummary();if($('history-dialog').open)renderHistory();
    if(run&&page==='run-view'){if(!$('rescue-panel').classList.contains('hidden'))renderHelp();if(!$('hint-panel').classList.contains('hidden'))$('hint-panel').textContent=helpCopy[lang][taskType(currentStep(run)?.title||'',run.goal)][Number($('hint-panel').dataset.helpIndex)][1];}
  }
  function renderPlan(){
    show('plan-view');$('plan-goal').textContent=draft.goal;$('plan-mode').textContent=t(draft.mode==='free'?'freeModeInfo':'focusModeInfo',{n:draft.duration});$('plan-list').replaceChildren();
    draft.titles.forEach((title,index)=>{
      const row=el('div',undefined,'plan-row'),input=el('input');input.value=title;input.maxLength=200;input.required=true;input.setAttribute('aria-label',t('editStep',{n:index+1}));input.addEventListener('input',()=>draft.titles[index]=input.value);
      row.append(el('span',String(index+1).padStart(2,'0'),'plan-number'),input);
      for(const [delta,label] of [[-1,'moveUp'],[1,'moveDown']]){const move=button(delta<0?'↑':'↓',()=>{const target=index+delta;[draft.titles[index],draft.titles[target]]=[draft.titles[target],draft.titles[index]];renderPlan();$('plan-list').children[target].querySelector('input').focus();},'text-button order-button');move.setAttribute('aria-label',t(label)+' '+t('step',{n:index+1}));move.title=t(label);move.disabled=index+delta<0||index+delta>=draft.titles.length;row.append(move);}
      const merge=button(t('merge'),()=>{const combined=draft.titles[index]+'；'+draft.titles[index+1];if(combined.length>200){$('plan-error').textContent=lang==='zh'?'合并后过长，请先缩短任务描述。':'Shorten the descriptions before merging.';return;}draft.titles.splice(index,2,combined);renderPlan();});merge.disabled=index===draft.titles.length-1;row.append(merge,button(t('remove'),()=>{draft.titles.splice(index,1);renderPlan();}));$('plan-list').append(row);
    });
  }
  function prepare(){const goal=$('goal').value.trim();if(!goal){$('goal').focus();return;}const mode=document.querySelector('input[name="mode"]:checked').value;const duration=Number($('duration').value==='custom'?$('custom-duration').value:$('duration').value);if(mode==='focus'&&(!Number.isInteger(duration)||duration<1||duration>240)){$('custom-duration').reportValidity();return;}draft={goal,mode,duration:mode==='free'?25:duration,titles:suggest(goal,lang)};$('plan-error').textContent='';renderPlan();}
  function begin(){if(!draft.titles.length||draft.titles.some(text=>!text.trim())){$('plan-error').textContent=t('needStep');return;}run=createRun(draft.goal,draft.titles,draft.mode,draft.duration);run.study_session=GMFShared.session(GMFShared.context,'learn');run.shared_context={...GMFShared.context};record=null;save();renderRun();}
  function renderRun(){if(!run)return;if(run.current!==null&&!currentStep(run))run.current=run.steps.find(s=>s.status==='pending')?.id??null;if(run.current===null){if(run.steps.every(s=>s.status==='done')){finish();return;}show('later-view');renderReturnList();return;}show('run-view');const step=currentStep(run),done=run.steps.filter(s=>s.status==='done').length,index=run.steps.indexOf(step);$('run-goal').textContent=run.goal;$('quest-kind').textContent=t('step',{n:index+1});$('mode-badge').textContent=t(run.mode==='free'?'freeMode':'focusMode');$('quest-heading').textContent=step.micro||step.title;$('quest-detail').textContent=methodHint(step.micro||step.title,run.goal,lang);$('progress-text').textContent=t('doneCount',{n:done,total:run.steps.length});$('progress-value').textContent=`${done}/${run.steps.length}`;$('progress-fill').style.width=`${done/run.steps.length*100}%`;$('checkpoint-track').replaceChildren();$('route-list').replaceChildren();run.steps.forEach((s,i)=>{if(i)$('checkpoint-track').append(el('span',undefined,'track-connector'));const dot=el('span',undefined,'track-item'+(s.id===run.current?' current':s.status==='done'?' done':s.status==='skipped'?' skipped':''));dot.setAttribute('role','listitem');dot.setAttribute('aria-label',`${s.title}: ${t(s.status==='done'?'stepDone':s.status==='skipped'?'stepSkipped':'stepPending')}`);$('checkpoint-track').append(dot);const item=el('li',undefined,s.id===run.current?'active':s.status==='done'?'finished':'');item.append(el('span',s.status==='done'?'✓':s.id===run.current?'●':s.status==='skipped'?'↶':'○','route-symbol'),el('span',s.title));$('route-list').append(item);});const next=run.steps.find(s=>s.status==='pending'&&s.id!==run.current),later=run.steps.filter(s=>s.status==='skipped');$('next-preview').textContent=step.micro?step.title:next?.title||(later.length?t('returnNext',{n:later.length}):t('noNext'));$('later-section').classList.toggle('hidden',!later.length);$('later-list').replaceChildren(...later.map(s=>button(s.title,()=>returnTo(s.id),'text-button later-button')));renderTimer();renderRetrieval();}
  function renderTimer(){if(!run)return;$('timer-label').textContent=t(run.mode==='focus'?'timeLeft':'timeElapsed');$('timer').textContent=timeText(run.mode==='focus'?run.remaining:run.elapsed);$('timer-toggle').textContent=t(run.paused?(run.expired?'resumeExtra':'resume'):'pause');$('complete-button').disabled=locked||run.paused;$('stuck-button').disabled=locked||run.paused;}
  function clearRescue(){for(const id of ['rescue-panel','hint-panel','note-form'])$(id).classList.add('hidden');$('inline-notice').textContent='';}
  function syncClock(){if(!run||page==='resume-view')return;advanceRun();save();renderTimer();if(run.expired&&!$('time-dialog').open&&page!=='later-view'&&page!=='summary-view'){renderTime();$('time-dialog').showModal();}}
  function complete(){if(!run||locked)return;if(context && run.current<=2 && !run.attempt_log.some(a=>a.step_id===run.current)){toast(pt('请先写下回忆并记录本次提取。'));return;}syncClock();if(run.paused)return;locked=true;
    if(context && run.current>2){const step=currentStep(run);run.repair_steps.push({kind:'consolidation',text:step.micro||step.title,at:new Date().toISOString()});}
    const outcome=completeStep(run);clearRescue();save();renderRun();$('inline-notice').textContent=t(outcome==='micro'?'microNotice':'doneNotice');$('quest-card').classList.remove('changed');void $('quest-card').offsetWidth;$('quest-card').classList.add('changed');setTimeout(()=>{locked=false;renderTimer();},650);}
  function skip(){if(!run||locked)return;syncClock();if(run.paused)return;skipStep(run);clearRescue();save();renderRun();$('inline-notice').textContent=t('skipNotice');}
  function returnTo(id){if(!run||locked)return;const target=run.steps.find(s=>s.id===id&&s.status==='skipped');if(!target)return;target.status='pending';run.current=id;clearRescue();save();renderRun();}
  function renderReturnList(){$('return-list').replaceChildren(...run.steps.filter(s=>s.status==='skipped').map(s=>button(t('returnTo',{title:s.title}),()=>returnTo(s.id),'secondary-button')));}
  function renderHelp(){
    const step=currentStep(run);if(!step)return;const type=taskType(step.micro||step.title,run.goal),copy=helpCopy[lang][type];
    ['clarify-button','reframe-button','hint-button'].forEach((id,index)=>$(id).textContent=copy[index][0]);
  }
  function giveHelp(index){
    if(!run||run.paused)return;const step=currentStep(run),type=taskType(step.micro||step.title,run.goal);
    if(context){run.hint_usage=(run.hint_usage||0)+1;run.repair_steps.push({kind:['clarify','reframe','hint'][index],text:helpCopy[lang][type][index][1],at:new Date().toISOString()});save();}
    $('hint-panel').dataset.helpIndex=index;
    $('hint-panel').textContent=helpCopy[lang][type][index][1];$('hint-panel').classList.remove('hidden');$('rescue-panel').classList.add('hidden');
  }
  function showResume(){
    show('resume-view');$('resume-heading').textContent=t(run.started===false?'nextReady':'resumeHeading');$('resume-goal').textContent=run.goal;
    $('resume-progress').textContent=t('doneCount',{n:run.steps.filter(step=>step.status==='done').length,total:run.steps.length});
    $('resume-time').textContent=t('resumeTime',{time:timeText(run.elapsed)})+(run.mode==='focus'?' · '+t('resumeRemaining',{time:timeText(run.remaining)}):'');
    const step=currentStep(run);$('resume-current').textContent=step?t('current',{title:step.micro||step.title}):t('noCurrent');
  }
  function resumeSession(){if(!run)return;run.started=true;run.paused=run.expired;run.clock=Date.now();lastInput=Date.now();save();renderRun();syncClock();}
  function openNote(){if(!run)return;$('rescue-panel').classList.add('hidden');$('note-form').classList.remove('hidden');$('blocker-note').value='';$('blocker-note').setCustomValidity('');$('blocker-note').focus();}
  function saveNote(){
    if(!run)return;const text=$('blocker-note').value.trim(),step=currentStep(run);if(!text||!step){$('blocker-note').setCustomValidity(lang==='zh'?'请写一句具体的卡点。':'Write one specific blocker.');$('blocker-note').reportValidity();return;}
    if(context)run.repair_steps.push({kind:'blocker',text,at:new Date().toISOString()});run.notes.push({taskId:step.id,title:step.title,text});if(!save()){run.notes.pop();return;}$('note-form').classList.add('hidden');$('inline-notice').textContent=t('noteSaved');
  }
  function openTutorial(){
    if($('history-dialog').open)$('history-dialog').close();write(TUTORIAL,true);
    if(run&&page!=='resume-view'&&!run.paused){advanceRun();run.paused=true;save();renderTimer();}
    $('tutorial-dialog').showModal();
  }
  function pauseResume(){if(!run)return;if(!run.paused){advanceRun();run.paused=true;}else{if(run.expired){run.remaining=600000;run.expired=false;}run.paused=false;}run.clock=Date.now();lastInput=Date.now();save();renderTimer();$('inline-notice').textContent=run.paused?t('pauseNotice'):'';}
  function renderTime(){$('time-progress').replaceChildren();for(const step of run.steps.filter(s=>s.status==='done'))$('time-progress').append(el('p',`✓ ${step.title}`));const current=currentStep(run);$('time-progress').append(el('p',current?t('current',{title:current.micro||current.title}):t('noCurrent')));}
  function closeTime(action){$('time-dialog').close();if(!run)return;if(action==='end'){finish();return;}if(action==='extend'){run.remaining=600000;run.expired=false;run.paused=false;}else{run.expired=false;run.remaining=600000;run.paused=true;}$('inline-notice').textContent=action==='break'?t('pauseNotice'):'';run.clock=Date.now();lastInput=Date.now();save();renderRun();}
  function completedLabels(item){return item.steps.flatMap(s=>[...(s.status==='done'?[s.title]:[]),...s.smallDone.map(title=>t('smallProgress',{title}))]);}
  async function finish(){
    if(!run)return;if(run.started===false){run=null;save();reset();return;}advanceRun();
    const finished={...run,date:new Date().toISOString(),endedNormally:true},saved=read(HISTORY,[]);
    finished.study_session.ended_at=finished.date;
    const nextValues={...values,[HISTORY]:[finished,...(Array.isArray(saved)?saved:[])].slice(0,100),[STORE]:null};
    try{await GMFShared.finishFocus(finished,nextValues);values=nextValues;}catch{run.paused=true;save();toast(t('storageError'));showResume();return;}
    record=finished;run=null;save();$('time-dialog').close();clearRescue();renderSummary();
  }
  function fillList(id,items,empty,prefix=''){$(id).replaceChildren(...(items.length?items.map(text=>el('li',prefix+text)):[el('li',t(empty))]));}
  function renderSummary(){
    show('summary-view');if(context){$('new-run-button').classList.add('hidden');$('end-button').classList.add('hidden');$('continue-later').classList.add('hidden');$('pl-session-note').textContent=pt('本轮过程已记录。自检成功与完成次数都不会直接增加掌握度。');} $('summary-goal').textContent=record.goal;const done=record.steps.filter(step=>step.status==='done');
    $('summary-stats').replaceChildren(...[['summaryTime',minutesText(record.elapsed)],['summaryCompleted',done.length+' / '+record.steps.length]].map(([label,value])=>{const node=el('div',undefined,'summary-stat');node.append(el('span',t(label)),el('strong',value));return node;}));
    fillList('summary-done',completedLabels(record),'noneDone','✓ ');fillList('summary-pending',record.steps.filter(step=>step.status!=='done').map(step=>step.title),'nonePending');
    const notes=record.notes||[];$('summary-note-section').classList.toggle('hidden',!notes.length);$('summary-notes').replaceChildren(...notes.map(note=>el('li',note.text)));
    $('continue-later').classList.toggle('hidden',done.length===record.steps.length);$('new-run-button').className=done.length===record.steps.length?'primary-button':'secondary-button';
  }
  function clearHistory() {
    $('clear-history-dialog').showModal();
  }
  async function confirmClearHistory() {
    try { values[HISTORY]=[];await LearningStore.putModule('mf-focus',values); }
    catch { toast(t('clearHistoryError')); return; }
    $('clear-history-dialog').close();
    renderHistory();
  }
  function renderHistory(){
    const records=read(HISTORY,[]);$('history-event-count').textContent=String(completedEvents(records));$('clear-history').disabled=!Array.isArray(records)||!records.length;$('history-list').replaceChildren();
    if(!Array.isArray(records)||!records.length){$('history-list').append(el('p',t('noHistory'),'history-empty'));return;}
    for(const item of records){
      if(!Array.isArray(item?.steps))continue;const row=el('article',undefined,'history-item'),done=item.steps.filter(step=>step.status==='done').length;
      row.append(el('span',new Date(item.date).toLocaleString(lang==='zh'?'zh-CN':'en-US',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}),'history-date'),el('h3',item.goal),el('p',t('historyMeta',{done,total:item.steps.length,minutes:minutesText(item.elapsed)})+' · '+t(done===item.steps.length?'allFinished':'hasUnfinished')));
      const details=el('details'),list=el('ul');for(const step of item.steps){list.append(el('li',(step.status==='done'?'✓':'○')+' '+step.title));for(const small of step.smallDone||[])list.append(el('li','✓ '+t('smallProgress',{title:small})));}details.append(el('summary',t('details')),list);
      if(item.notes?.length){const notes=el('ul');notes.append(...item.notes.map(note=>el('li',note.text)));details.append(el('p',t('sessionNotes')),notes);}
      row.append(details);$('history-list').append(row);
    }
  }
  function reset(){draft=null;$('goal').value='';home();}
  $('setup-form').addEventListener('submit',event=>{event.preventDefault();prepare();});
  $('plan-form').addEventListener('submit',event=>{event.preventDefault();begin();});
  $('note-form').addEventListener('submit',event=>{event.preventDefault();saveNote();});
  $('blocker-note').addEventListener('input',()=> $('blocker-note').setCustomValidity(''));
  $('note-button').onclick=openNote;$('note-cancel').onclick=()=>$('note-form').classList.add('hidden');
  $('add-step').onclick=()=>{if(draft.titles.length>=50){$('plan-error').textContent=t('limit');return;}draft.titles.push('');renderPlan();$('plan-list').lastElementChild.querySelector('input').focus();};
  $('back-setup').onclick=()=>show('setup-view');
  document.querySelectorAll('input[name="mode"]').forEach(input=>input.addEventListener('change',()=>{$('duration-options').classList.toggle('hidden',input.value!=='focus');$('custom-duration').disabled=input.value!=='focus'||$('duration').value!=='custom';}));
  $('duration').onchange=()=>{$('custom-duration-wrap').classList.toggle('hidden',$('duration').value!=='custom');$('custom-duration').disabled=$('duration').value!=='custom';};$('custom-duration').disabled=true;
  document.querySelectorAll('[data-example]').forEach(node=>node.onclick=()=>{$('goal').value=({physics:lang==='zh'?'AP Physics 作业 1–12':'AP Physics homework 1–12',reading:lang==='zh'?'读完 Biology Chapter 3':'Read Biology Chapter 3',writing:lang==='zh'?'写完 English Essay Introduction':'Write the English essay introduction'})[node.dataset.example];$('goal').focus();});
  $('complete-button').onclick=complete;$('skip-button').onclick=skip;$('clarify-button').onclick=()=>giveHelp(0);$('reframe-button').onclick=()=>giveHelp(1);$('hint-button').onclick=()=>giveHelp(2);$('timer-toggle').onclick=pauseResume;
  $('stuck-button').onclick=()=>{if(!run||run.paused)return;renderHelp();$('rescue-panel').classList.toggle('hidden');};$('rescue-close').onclick=()=>$('rescue-panel').classList.add('hidden');
  $('stop-button').onclick=finish;$('later-finish').onclick=finish;$('extend-button').onclick=()=>closeTime('extend');$('time-finish').onclick=()=>closeTime('end');$('break-button').onclick=()=>closeTime('break');$('time-dialog').addEventListener('cancel',event=>{event.preventDefault();closeTime('break');});
  $('new-run-button').onclick=reset;$('end-button').onclick=reset;
  $('continue-later').onclick=()=>{run=carryRun(record);if(!run)return;run.study_session=GMFShared.session(record.shared_context||GMFShared.context,'learn');run.shared_context=record.shared_context||GMFShared.context;save();showResume();};
  $('resume-session').onclick=resumeSession;$('end-previous').onclick=finish;
  $('tutorial-start').onclick=()=>$('tutorial-dialog').close();$('tutorial-skip').onclick=()=>$('tutorial-dialog').close();$('tutorial-review').onclick=openTutorial;
  $('brand-home').onclick=event=>{event.preventDefault();if(run){advanceRun();run.paused=true;save();}home();};
  const openHistory=()=>{renderHistory();$('history-dialog').showModal();};$('history-toggle').onclick=openHistory;$('history-close').onclick=()=>$('history-dialog').close();$('clear-history').onclick=clearHistory;
  $('clear-history-confirm').onclick=confirmClearHistory;$('clear-history-cancel').onclick=()=>$('clear-history-dialog').close();
  $('theme-toggle').onclick=()=>{theme=theme==='dark'?'light':'dark';write(SETTINGS,{lang,theme});applyTheme();};$('language-toggle').onclick=()=>{lang=lang==='zh'?'en':'zh';write(SETTINGS,{lang,theme});applyLanguage();};
  document.addEventListener('visibilitychange',()=>{if(run){if(document.hidden){advanceRun();run.paused=true;}run.clock=Date.now();lastInput=Date.now();save();renderTimer();}});window.addEventListener('offline',()=>{if(run){run.paused=true;run.clock=Date.now();lastInput=Date.now();save();renderTimer();}});window.addEventListener('pagehide',()=>{if(run){advanceRun();run.paused=true;save();}});
  function sendEvidence(evidence){if(!evidence)return;parent.postMessage({kind:'pl-mf-evidence',evidence},'*');$('pl-session-note').textContent=pt('正在把本轮学习证据写回 Pathline…');}
  function renderRetrieval(){
    if(!context||!run)return;const panel=$('pl-retrieval'),step=currentStep(run),active=step&&step.id<=2;panel.classList.toggle('hidden',!active);if(!active)return;
    if(panel.dataset.step!==String(step.id)){$('pl-response').value='';$('pl-success').checked=false;panel.dataset.step=String(step.id);}
    $('pl-retrieval-prompt').textContent=step.id===1?(context.goals[0]||pt('解释本 Topic 的核心关系和适用条件。')):pt('从刚学过的例题或教材习题中选一题，先回忆已知条件、目标和第一步关系。');
    const logs=run.attempt_log.filter(a=>a.step_id===step.id);$('pl-attempt-status').textContent=logs.length?pt('已记录 {n} 次尝试；成功由你对照教材自检，不是独立评分。',{n:logs.length}):pt('写下后点击“记录本次提取”，再继续这一段。');
  }
  function home(){
    page='home';$('mf-home').classList.remove('hidden');document.querySelector('.shell').classList.add('hidden');
    const txt=GMFShared.text,history=read(HISTORY,[]),ctx=GMFShared.context;
    $('mf-home').innerHTML=`<p class="gmf-context-copy">${GMFShared.esc(GMFShared.title())}</p><h1>Mind Flow</h1><p class="muted">${txt('把眼前这一段做好，再把没懂的地方修好。','Focus on one task. Return to what needs repair.')}</p>${run?`<section class="gmf-home-panel"><h2>${txt('继续上一轮','Continue your last session')}</h2><p>${GMFShared.esc(run.goal)}</p><button id="home-continue" class="primary-button">${txt('继续','Continue')}</button><p>${run.steps.filter(s=>s.status==='done').length} / ${run.steps.length} · ${timeText(run.elapsed)}</p></section>`:''}<div class="gmf-home-grid"><button id="home-free"><strong>${txt('自由学习','Free study')}</strong><small>${txt('正向计时，按自己的节奏','Count up, at your own pace')}</small></button><button id="home-timed"><strong>${txt('定时学习','Timed study')}</strong><small>${txt('给这一轮设置时间边界','Set a time boundary')}</small></button><a id="home-review" href="${GMFShared.esc(GMFShared.url('review'))}"><strong>${txt('复习与修正','Review & repair')}</strong><small>${txt('先提取，卡住就修，再独立试','Retrieve, repair, then try independently')}</small></a></div><section class="gmf-home-panel"><h2>${txt('当前 / 最近任务','Current / recent tasks')}</h2><div id="home-tasks"></div></section><section class="gmf-home-panel"><h2>${txt('近期记录与卡点','Recent sessions & blockers')}</h2><p>${txt('已完成事件','Completed events')} · ${completedEvents(history)}</p><div id="home-recent" class="gmf-home-list"></div><button id="home-history" class="text-button">${txt('查看全部历史','View history')}</button><button id="home-tutorial" class="text-button">${txt('重新查看教程','Review tutorial')}</button></section>`;
    $('home-tasks').textContent=(run?.steps||history[0]?.steps||[]).map(s=>(s.status==='done'?'✓ ':'○ ')+s.title).join(' · ')||txt('写下一个任务，就能开始。','Write a task to begin.');
    for(const item of history.slice(0,3)){const row=el('article');row.append(el('strong',item.goal),el('p',minutesText(item.elapsed)+' · '+(item.notes||[]).map(n=>n.text).join(' / ')));$('home-recent').append(row);}
    $('home-continue')?.addEventListener('click',resumeSession);const start=mode=>{if(run){showResume();return;}show('setup-view');const radio=document.querySelector(`input[name="mode"][value="${mode}"]`);radio.checked=true;radio.dispatchEvent(new Event('change'));if(ctx.topic_id)$('goal').value=GMFShared.title();$('goal').focus();};$('home-free').onclick=()=>start('free');$('home-timed').onclick=()=>start('focus');$('home-history').onclick=()=>{renderHistory();$('history-dialog').showModal();};$('home-tutorial').onclick=openTutorial;
    if(!['2.5','5.4','7.5'].includes(ctx.topic_id)){const link=$('home-review');link.removeAttribute('href');link.setAttribute('role','button');link.tabIndex=0;link.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();link.click();}};link.onclick=()=>{link.replaceWith(...['2.5','5.4','7.5'].map(tid=>{const a=el('a',tid);a.href=GMFShared.url('review',{course_id:'ap-physics-c-mechanics-2026-27',unit_id:tid.split('.')[0],topic_id:tid,return_to:location.href});a.style.padding='18px';return a;}));};}
  }
  document.addEventListener('gmf-preferences',event=>{lang=event.detail.lang;theme=event.detail.theme;applyLanguage();if(page==='home')home();});
  applyLanguage();home();if(!read(TUTORIAL,false))openTutorial();setInterval(syncClock,1000);
  document.querySelector('.brand-version').textContent='';
  // Optional browser agent integration: read the actual visible session; no automatic completion.
  if(document.modelContext?.registerTool){const life=new AbortController();try{Promise.resolve(document.modelContext.registerTool({name:'read_mind_flow_session',title:'Read Mind Flow session',description:'Read the current task, actual completed steps and deferred steps without changing progress.',inputSchema:{type:'object',properties:{},additionalProperties:false},annotations:{readOnlyHint:true,untrustedContentHint:true},execute(input){if(!input||typeof input!=='object'||Array.isArray(input)||Object.keys(input).length)throw new Error('Expected an empty object');return run?{goal:run.goal,current:currentStep(run)?.micro||currentStep(run)?.title||null,completed:run.steps.filter(s=>s.status==='done').map(s=>s.title),deferred:run.steps.filter(s=>s.status==='skipped').map(s=>s.title),paused:run.paused}:{active:false};}},{signal:life.signal})).catch(()=>{});}catch{}window.addEventListener('pagehide',()=>life.abort(),{once:true});}
})();
