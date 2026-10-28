import {clone} from '../src/session.mjs';

// TEST DOUBLE ONLY. A Promise queue inside a tab is NOT a cross-tab production lock.
export class AtomicTestPort {
  constructor() {this.rows=new Map();this.archives=new Map();this.queue=Promise.resolve();this.failNext=false;}
  async read(scope) {await this.queue.catch(()=>{});return clone(this.rows.get(scope) ?? null);}
  transact(scope, reduce) {
    const job=this.queue.catch(()=>{}).then(() => {
      const before=this.rows.get(scope), next=reduce(clone(before ?? null));
      if (this.failNext) {this.failNext=false;throw Error('Injected durable commit failure');}
      if (next.current && next.current.session_id !== before?.current?.session_id) {
        if (this.archives.has(scope+':'+next.current.session_id)) throw Error('Session id reused');
        if (before?.current && before.current.state !== 'Ended') throw Error('Cannot replace active session');
        if (before?.current) this.archives.set(scope+':'+before.current.session_id,clone(before.current));
      }
      this.rows.set(scope,clone(next));return clone(next);
    });
    this.queue=job;return job;
  }
}
