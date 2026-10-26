import {clone, requireId, contextOf} from './session.mjs';

function text(value, name) {
  if (typeof value !== 'string' || !value.trim() || value.length > 4000) throw Error(`Invalid ${name}`);
  return value.trim();
}
function estimate(value) {
  if (value !== null && (!Number.isSafeInteger(value) || value <= 0)) throw Error('Invalid estimated_ms');
  return value;
}
export function createTask(input, existing = []) {
  requireId(input.task_id,'task_id');
  if (existing.some(t => t.task_id === input.task_id)) throw Error('Duplicate task');
  const parent_id=input.parent_id ?? null;
  if (parent_id !== null) {
    const p=existing.find(t => t.task_id === parent_id);
    if (!p || p.parent_id !== null) throw Error('Only one subtask level allowed');
  }
  if (input.important !== undefined && typeof input.important !== 'boolean') throw Error('Invalid important');
  return {task_id:input.task_id, title:text(input.title,'title'),parent_id,
    completed:false,important:input.important ?? false,estimated_ms:estimate(input.estimated_ms ?? null),
    context:contextOf(input.context)};
}
export function editTask(task, patch) {
  const out=clone(task);
  for (const [k,v] of Object.entries(patch)) {
    if (k === 'title') out.title=text(v,'title');
    else if (k === 'estimated_ms') out.estimated_ms=estimate(v);
    else if (['completed','important'].includes(k) && typeof v === 'boolean') out[k]=v;
    else throw Error('Unsupported task change');
  }
  return out;
}
export function questionRef(input) {
  if (!input) return null;
  // AS module-local question_id is NOT a GMF exercise_id. Namespace is mandatory.
  return {source:'Assessment',namespace:requireId(input.namespace,'namespace'),
    question_id:requireId(input.question_id,'question_id'),
    version_id:input.version_id == null ? null : requireId(input.version_id,'version_id')};
}
export function upsertBlocker(existing, input) {
  const ref=questionRef(input.question_ref), session_id=input.session_id ?? null;
  if (session_id !== null) requireId(session_id);
  let found=ref ? existing.find(b => b.question_ref?.namespace === ref.namespace && b.question_ref?.question_id === ref.question_id) : null;
  if (found) {
    const out=clone(found);
    if (session_id && !out.session_ids.includes(session_id)) out.session_ids.push(session_id);
    if (ref.version_id && !out.seen_version_ids.includes(ref.version_id)) out.seen_version_ids.push(ref.version_id);
    return {created:false, blocker:out}; // Preserve title, original ref, notes and resolved state.
  }
  requireId(input.blocker_id,'blocker_id');
  if (existing.some(b => b.blocker_id === input.blocker_id)) throw Error('Duplicate blocker id');
  return {created:true, blocker:{blocker_id:input.blocker_id, title:text(input.title,'title'),
    notes:'', resolved:false, context:contextOf(input.context),question_ref:ref,
    seen_version_ids:ref?.version_id ? [ref.version_id] : [],session_ids:session_id?[session_id]:[]}};
}
export function editBlocker(blocker, patch) {
  const out=clone(blocker);
  for (const [k,v] of Object.entries(patch)) {
    if (k === 'title') out.title=text(v,'title');
    else if (k === 'notes' && typeof v === 'string' && v.length <= 20000) out.notes=v;
    else if (k === 'resolved' && typeof v === 'boolean') out.resolved=v;
    else throw Error('Unsupported blocker change');
  }
  return out;
}
export function routeIntent(blocker, target) {
  if (target === 'PL' && blocker.context.topic_id && blocker.context.course_id) {
    return {module:'Pathline',course_id:blocker.context.course_id,unit_id:blocker.context.unit_id,
      topic_id:blocker.context.topic_id,return_to:blocker.context.return_to};
  }
  if (target === 'AS' && blocker.question_ref) return {module:'Assessment',...clone(blocker.question_ref),return_to:blocker.context.return_to};
  throw Error('No confirmed link');
}

// A deletion plan only; host executes scoped deletion atomically after two UI confirmations.
// No access to shared course, Ledger, PL evidence or Assessment records is accepted here.
export function planClearMFHistory({sessions,blockers}, {confirmed,confirmedAgain}) {
  if (confirmed !== true || confirmedAgain !== true) throw Error('Two confirmations required');
  const ids=sessions.filter(s => s.schema === 'gmf.mf.session.candidate/1' && s.state === 'Ended').map(s => s.session_id);
  const removed=new Set(ids);
  return {delete_session_ids:ids,blockers:blockers.map(b => ({...clone(b),
    session_ids:b.session_ids.filter(id => !removed.has(id)),
    removed_session_ids:[...new Set([...(b.removed_session_ids || []),...b.session_ids.filter(id => removed.has(id))])]})),
    preserve_tasks:true,preserve_legacy_raw:true};
}
