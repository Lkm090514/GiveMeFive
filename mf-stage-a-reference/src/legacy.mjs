import {clone, requireId} from './session.mjs';
import {createTask,upsertBlocker} from './entities.mjs';

// Read-only projection of the ACTUALLY OBSERVED Fusion V2 app.js free/focus shape.
// Caller supplies a stable namespace identifying one immutable exported source record.
// Never writes to localStorage/IndexedDB; raw history is preserved byte-for-byte as raw_json.
export function projectLegacyRun(raw_json, source_key) {
  requireId(source_key,'source_key');
  const raw=JSON.parse(raw_json), prefix=`legacy:${encodeURIComponent(source_key)}`;
  if (!Array.isArray(raw?.steps) || typeof raw.goal !== 'string' || !['free','focus'].includes(raw.mode) || !Number.isFinite(raw.elapsed) || raw.elapsed < 0) {
    return {migration_id:prefix,raw_json,status:'UNSUPPORTED_PRESERVED',tasks:[],blockers:[]};
  }
  const tasks=[], blockers=[], root=createTask({task_id:prefix+':task',title:raw.goal});tasks.push(root);
  const seen=new Set();
  for (const step of raw.steps) {
    if (step.id == null || seen.has(String(step.id)) || typeof step.title !== 'string' || !['pending','done','skipped'].includes(step.status)) throw Error('Invalid legacy steps; preserve source and review');
    seen.add(String(step.id));
    const task=createTask({task_id:prefix+':step:'+encodeURIComponent(String(step.id)),title:step.title,parent_id:root.task_id},tasks);
    task.completed=step.status === 'done'; task.legacy_status=step.status;tasks.push(task);
  }
  root.completed=tasks.length>1 && tasks.slice(1).every(t => t.completed);
  for (const [i,note] of (Array.isArray(raw.notes)?raw.notes:[]).entries()) {
    if (typeof note.text !== 'string' || !note.text.trim()) continue; // Original always retained.
    const b=upsertBlocker(blockers,{blocker_id:prefix+':note:'+i,title:note.text}).blocker;
    b.legacy_task_id=seen.has(String(note.taskId))?prefix+':step:'+encodeURIComponent(String(note.taskId)):null;
    blockers.push(b);
  }
  return {migration_id:prefix,raw_json,status:'PROJECTED_REVIEW_REQUIRED',tasks,blockers,
    legacy_session:{source_key,legacy_elapsed_ms:raw.elapsed,legacy_date:raw.date ?? null,
      suggested_state:raw.endedNormally === true?'Ended':'Paused',
      trusted_v3_focus_ms:null,reason:'旧 elapsed 算法与 V3 不同，不能重建已确认时间段'},
    rollback:'Remove only this migration projection; original raw_json and source keys remain unchanged.'};
}
export function appendMigration(existing, projection) {
  const prior=existing.find(p => p.migration_id === projection.migration_id);
  if (prior) {
    if (prior.raw_json !== projection.raw_json) throw Error('Source changed; use an immutable export identity');
    return clone(existing);
  }
  return [...clone(existing),clone(projection)];
}
