// Candidate MF domain contract. No storage, UI, timers, network or Learning Ledger.
export const SCHEMA = 'gmf.mf.session.candidate/1';
export const clone = value => structuredClone(value);
export function requireId(value, name = 'id') {
  if (typeof value !== 'string' || !value.trim() || value.length > 500) throw Error(`Invalid ${name}`);
  return value;
}
function finite(value, name) {
  if (!Number.isFinite(value) || value < 0) throw Error(`Invalid ${name}`);
}
export function validateStamp(s) {
  requireId(s?.runtime_id, 'runtime_id');
  finite(s.wall_ms, 'wall_ms'); finite(s.mono_ms, 'mono_ms');
}
export function contextOf(input = {}) {
  const out = {};
  for (const key of ['course_id','unit_id','topic_id','exercise_id','source','return_to']) {
    out[key] = input[key] ?? null;
    if (out[key] !== null) requireId(out[key], key);
  }
  // return_to remains opaque metadata. Only a host allowlisted route resolver may navigate it.
  return out;
}
export function createSession({session_id, mode = 'free', focus_ms = 1500000,
  rest_ms = 300000, context = {}, task_id = null}, stamp) {
  validateStamp(stamp); requireId(session_id, 'session_id');
  if (!['free','pomodoro'].includes(mode)) throw Error('Invalid mode');
  for (const [key, value] of Object.entries({focus_ms,rest_ms})) {
    if (!Number.isSafeInteger(value) || value <= 0 || value > 86400000) throw Error(`Invalid ${key}`);
  }
  if (task_id !== null) requireId(task_id, 'task_id');
  return {schema:SCHEMA, session_id, revision:0, state:'Ready', mode, focus_ms, rest_ms,
    context:contextOf(context), task_id, created_at:stamp.wall_ms, ended_at:null,
    phase:0, phase_kind:null, notices:[], segments:[], anchor:null, pause_reason:null,
    timing_policy:{max_gap_ms:10000, clock_tolerance_ms:1000}};
}
export function validateSession(s) {
  if (!s || s.schema !== SCHEMA) throw Error('Unsupported session schema; preserve original');
  requireId(s.session_id); contextOf(s.context);
  if (!['Ready','Focusing','Paused','Resting','Ended'].includes(s.state)) throw Error('Invalid state');
  if (!['free','pomodoro'].includes(s.mode)) throw Error('Invalid mode');
  if (!Number.isSafeInteger(s.revision) || s.revision < 0) throw Error('Invalid revision');
  if (!Number.isSafeInteger(s.phase) || s.phase < 0) throw Error('Invalid phase');
  if (!['focus','rest',null].includes(s.phase_kind)) throw Error('Invalid phase kind');
  if ((s.state === 'Focusing' && s.phase_kind !== 'focus') || (s.state === 'Resting' && s.phase_kind !== 'rest')) throw Error('State/phase mismatch');
  if (s.state !== 'Ready' && s.state !== 'Ended' && s.phase === 0) throw Error('Missing phase');
  if (s.task_id !== null) requireId(s.task_id);
  for (const k of ['focus_ms','rest_ms']) if (!Number.isSafeInteger(s[k]) || s[k] <= 0 || s[k] > 86400000) throw Error('Invalid duration');
  finite(s.created_at, 'created_at');
  if (s.state === 'Ended') finite(s.ended_at, 'ended_at');
  if (!s.timing_policy || s.timing_policy.max_gap_ms !== 10000 || s.timing_policy.clock_tolerance_ms !== 1000) throw Error('Unknown timing policy');
  if (!Array.isArray(s.segments) || !Array.isArray(s.notices)) throw Error('Invalid lists');
  let end = -1;
  for (const p of s.segments) {
    for (const k of ['start_ms','end_ms','duration_ms']) finite(p[k], k);
    if (!['focus','rest'].includes(p.kind) || p.end_ms <= p.start_ms || p.duration_ms <= 0 || p.duration_ms > p.end_ms-p.start_ms || p.start_ms < Math.max(end,s.created_at) || !Number.isSafeInteger(p.phase) || p.phase < 1 || p.phase > s.phase) throw Error('Invalid segment');
    if (p.task_id !== null) requireId(p.task_id);
    if (p.kind === 'rest' && p.task_id !== null) throw Error('Rest cannot belong to task');
    end = p.end_ms;
  }
  if (s.anchor) {validateStamp(s.anchor);if (s.anchor.wall_ms < Math.max(end,s.created_at)) throw Error('Anchor precedes history');}
  const noticeIds=new Set();
  for (const n of s.notices) {
    requireId(n.id,'notice id');
    if (!['focus','rest'].includes(n.kind) || !Number.isSafeInteger(n.phase) || n.phase < 1 || n.phase > s.phase || noticeIds.has(n.id)) throw Error('Invalid notice');
    noticeIds.add(n.id);
  }
  if (['Ready','Paused','Ended'].includes(s.state) && s.anchor !== null) throw Error('Inactive anchor');
  if (['Focusing','Resting'].includes(s.state) && !s.anchor) throw Error('Missing anchor');
  return s;
}
export function totals(s) {
  let focus_ms = 0, rest_ms = 0; const tasks = Object.create(null);
  for (const p of s.segments) {
    if (p.kind === 'rest') rest_ms += p.duration_ms;
    else {focus_ms += p.duration_ms; if (p.task_id !== null) tasks[p.task_id] = (tasks[p.task_id] || 0) + p.duration_ms;}
  }
  return {focus_ms,rest_ms,tasks};
}
function phaseElapsed(s) {return s.segments.filter(p => p.phase === s.phase).reduce((n,p) => n+p.duration_ms,0);}
export function timerView(s) {
  const elapsed_ms = phaseElapsed(s), target = s.phase_kind === 'rest' ? s.rest_ms : s.mode === 'pomodoro' ? s.focus_ms : null;
  return {session_id:s.session_id, revision:s.revision, state:s.state, ...totals(s),
    phase_elapsed_ms:elapsed_ms, remaining_ms:target === null ? null : Math.max(0,target-elapsed_ms),
    overtime_ms:target === null ? 0 : Math.max(0,elapsed_ms-target),
    progress:target === null ? null : Math.min(1,elapsed_ms/target)};
}
function pause(s, reason) {s.state='Paused'; s.anchor=null; s.pause_reason=reason;}
function due(s) {
  const target = s.phase_kind === 'rest' ? s.rest_ms : s.mode === 'pomodoro' ? s.focus_ms : null;
  const id = `${s.session_id}:phase:${s.phase}:due`;
  if (target !== null && phaseElapsed(s) >= target && !s.notices.some(n => n.id === id)) {
    s.notices.push({id,kind:s.phase_kind,phase:s.phase});
  }
}
function settle(s, stamp) {
  if (!['Focusing','Resting'].includes(s.state)) return;
  const a = s.anchor, wall = stamp.wall_ms-a.wall_ms, mono = stamp.mono_ms-a.mono_ms;
  if (stamp.runtime_id !== a.runtime_id || wall < 0 || mono < 0 || wall > s.timing_policy.max_gap_ms || mono > s.timing_policy.max_gap_ms || Math.abs(wall-mono) > s.timing_policy.clock_tolerance_ms) {
    pause(s, 'unconfirmed_gap'); return;
  }
  const duration_ms = Math.min(wall,mono);
  if (duration_ms > 0) {
    const p = {kind:s.state === 'Focusing'?'focus':'rest', phase:s.phase,
      task_id:s.state === 'Focusing'?s.task_id:null, start_ms:a.wall_ms, end_ms:stamp.wall_ms, duration_ms};
    const last = s.segments.at(-1);
    if (last && last.kind === p.kind && last.phase === p.phase && last.task_id === p.task_id && last.end_ms === p.start_ms) {
      last.end_ms=p.end_ms; last.duration_ms+=duration_ms;
    } else s.segments.push(p);
  }
  s.anchor=clone(stamp); due(s);
}
function startPhase(s, kind, stamp) {
  s.phase++; s.phase_kind=kind; s.state=kind === 'focus'?'Focusing':'Resting';
  s.anchor=clone(stamp); s.pause_reason=null;
}
export function transition(original, command, stamp) {
  validateSession(original); validateStamp(stamp);
  const allowed = ['start','tick','pause','rest','resume','end','switch_task','suspend','recover','exam_start'];
  if (!allowed.includes(command?.type)) throw Error('Unknown command');
  if (original.state === 'Ended') {
    if (['tick','end','recover','exam_start'].includes(command.type)) return clone(original);
    throw Error('Session ended');
  }
  if (command.type === 'switch_task' && command.task_id !== null) requireId(command.task_id,'task_id');
  // Followers cannot heartbeat or accidentally steal a running clock.
  if (command.type === 'tick' && original.anchor && original.anchor.runtime_id !== stamp.runtime_id) return clone(original);
  const s=clone(original), before=s.state;
  if (command.type === 'recover') {
    if (s.state !== 'Ready') pause(s,'recovered');
  } else {
    settle(s,stamp);
    switch(command.type) {
      case 'start':
        if (before === 'Ready') startPhase(s,'focus',stamp);
        break; // Duplicate Start never replaces/resumes a session.
      case 'tick': break;
      case 'pause':
      case 'exam_start':
      case 'suspend':
        if (before !== 'Ready') pause(s,command.type);
        break;
      case 'rest':
        if (before !== 'Focusing') throw Error('Rest requires Focusing');
        if (s.state === 'Focusing') startPhase(s,'rest',stamp);
        break;
      case 'resume':
        if (!['Paused','Resting'].includes(before)) throw Error('Resume requires Paused/Resting');
        if (before === 'Resting' || s.phase_kind === 'rest') startPhase(s,'focus',stamp);
        else {s.state='Focusing'; s.anchor=clone(stamp); s.pause_reason=null;}
        break;
      case 'end': s.state='Ended'; s.ended_at=stamp.wall_ms; s.anchor=null; break;
      case 'switch_task': s.task_id=command.task_id; break;
    }
  }
  // A clock rollback must not allow new segments overlapping confirmed history.
  if (s.anchor && stamp.wall_ms < (s.segments.at(-1)?.end_ms ?? s.created_at)) pause(s,'clock_rollback');
  s.revision++;
  return validateSession(s);
}
