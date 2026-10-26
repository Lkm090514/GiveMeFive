import {validateSession, totals} from './session.mjs';

export const utcCalendar = {
  dayKey:ms => new Date(ms).toISOString().slice(0,10),
  nextDayStart:ms => {const d=new Date(ms);return Date.UTC(d.getUTCFullYear(),d.getUTCMonth(),d.getUTCDate()+1);}
};
// Calendar port must use the user's timezone and real local midnight boundaries.
// No assumption that a local day is always 24 hours.
export function recordsSummary(sessions, dayKeys, calendar = utcCalendar) {
  const unique=new Map();
  for (const s of sessions) {
    validateSession(s);
    const prior=unique.get(s.session_id);
    if (prior?.revision === s.revision && JSON.stringify(prior) !== JSON.stringify(s)) throw Error('Conflicting session revision');
    if (!prior || prior.revision < s.revision) unique.set(s.session_id,s);
  }
  const days=Object.fromEntries(dayKeys.map(key => [key,{focus_ms:0,rest_ms:0}]));
  let focus_ms=0,rest_ms=0;
  for (const s of unique.values()) {
    const t=totals(s);focus_ms+=t.focus_ms;rest_ms+=t.rest_ms;
    for (const p of s.segments) {
      let cursor=p.start_ms;
      while (cursor < p.end_ms) {
        const boundary=calendar.nextDayStart(cursor);
        if (!Number.isFinite(boundary) || boundary <= cursor) throw Error('Invalid calendar boundary');
        const stop=Math.min(boundary,p.end_ms), key=calendar.dayKey(cursor);
        if (days[key]) days[key][p.kind === 'focus'?'focus_ms':'rest_ms'] += p.duration_ms*(stop-cursor)/(p.end_ms-p.start_ms);
        cursor=stop;
      }
    }
  }
  return {session_count:unique.size,focus_ms,rest_ms,days,
    selected_days_focus_ms:Object.values(days).reduce((n,d) => n+d.focus_ms,0),
    measure:'专注状态时间；不代表经过验证的有效学习时间'};
}
