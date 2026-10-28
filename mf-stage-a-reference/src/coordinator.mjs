import {createSession, transition, validateSession, clone, requireId} from './session.mjs';

// Host-owned port, NOT a new database or Ledger:
// transact(scope, synchronousReducer) atomically reads/writes {current, exam_ids}.
// It must serialize across tabs AND atomically archive an ended current session
// when replacing it. Resolve only after durable commit; failure must roll back.
export class SessionCoordinator {
  constructor(port, scope) {
    if (typeof port?.transact !== 'function' || typeof port?.read !== 'function') throw Error('Atomic host port required');
    this.port=port; this.scope=requireId(scope,'scope');
  }
  read() {return this.port.read(this.scope);}
  start(options, stamp) {
    return this.port.transact(this.scope, input => {
      const row=clone(input || {current:null,exam_ids:[]});
      if (row.exam_ids.length) throw Error('Formal exam owns timer');
      if (row.current && row.current.state !== 'Ended') return row;
      if (row.current?.session_id === options.session_id) throw Error('Session id reused');
      // IDs must be globally unique; host port rejects any archived session ID reuse.
      row.current=transition(createSession(options,stamp),{type:'start'},stamp);
      return row;
    });
  }
  dispatch(session_id, expectedRevision, command, stamp) {
    return this.port.transact(this.scope, input => {
      const row=clone(input);
      if (!row?.current || row.current.session_id !== session_id) throw Error('Session identity conflict');
      validateSession(row.current);
      if (row.current.revision !== expectedRevision) throw Error('Revision conflict; reload before retry');
      if (row.exam_ids.length && ['start','resume'].includes(command.type)) throw Error('Formal exam owns timer');
      row.current=transition(row.current,command,stamp); return row;
    });
  }
  examStart(exam_id, stamp) {
    requireId(exam_id,'exam_id');
    return this.port.transact(this.scope, input => {
      const row=clone(input || {current:null,exam_ids:[]});
      if (!row.exam_ids.includes(exam_id)) row.exam_ids.push(exam_id);
      if (row.current) row.current=transition(row.current,{type:'exam_start'},stamp);
      return row;
    });
  }
  examEnd(exam_id) {
    return this.port.transact(this.scope, input => {
      const row=clone(input || {current:null,exam_ids:[]});
      row.exam_ids=row.exam_ids.filter(id => id !== exam_id);
      return row; // Never auto-resume. Host must reconcile exam IDs after a crash.
    });
  }
}
