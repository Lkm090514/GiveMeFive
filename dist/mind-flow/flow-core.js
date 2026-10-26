(() => {
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
  const api={suggest,createRun,currentStep,clockAdvance,completeStep,skipStep,shrinkStep,rangeOf,methodHint,completedEvents,prepareResume,carryRun,taskType};if(typeof module!=='undefined'&&module.exports)module.exports=api;else window.MindFlowCore=api;
})();
