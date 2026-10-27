import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import fs from 'node:fs';
test('online Progress hides other Assessment users without deleting ledger facts or PL/MF',()=>{
 const window={location:{hostname:'gmf.example'}},context={window,document:{},structuredClone,Promise,Map,Set};
 vm.runInNewContext(fs.readFileSync('dist/learning-store.js','utf8'),context);
 const events=[{event_id:'a',user_id:'A',source:'Assessment',type:'ASSESSMENT',occurred_at:'2026-10-27'},{event_id:'b',user_id:'B',source:'Assessment',type:'ASSESSMENT',occurred_at:'2026-10-27'},{event_id:'mf',source:'MF',type:'MF_SESSION_COMPLETED',occurred_at:'2026-10-27'},{event_id:'pl',source:'PL',type:'EXPOSURE',occurred_at:'2026-10-27'}],before=JSON.stringify(events),store=window.LearningStore;
 assert.equal(store.projection(events).assessment.length,0);
 store.setIdentity({auth_mode:'password',owner_id:'A'});assert.equal(store.projection(events).assessment[0].event_id,'a');
 store.setIdentity({auth_mode:'password',owner_id:'B'});assert.equal(store.projection(events).assessment[0].event_id,'b');
 store.setIdentity(null);assert.equal(store.projection(events).assessment.length,0);
 assert.equal(store.projection(events).learning_repair.length,1);assert.equal(store.projection(events).exposure.length,1);assert.equal(JSON.stringify(events),before);
 store.setIdentity({auth_mode:'local',owner_id:'local-owner'});assert.equal(store.projection(events).assessment.length,2,'existing local projection preserved');
});
