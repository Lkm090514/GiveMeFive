import test from 'node:test';
import assert from 'node:assert/strict';
import {focusMarkup,dialogMarkup,recordsModel} from '../dist/mind-flow/v3/view.mjs';
import {createSession,transition} from '../dist/mind-flow/v3/core/session.mjs';
import {empty,calendar} from '../dist/mind-flow/v3/host.mjs';

const setup={mode:'free',focus_min:25,rest_min:5,task_id:null};
const stamp=(n=0)=>({runtime_id:'ui',wall_ms:1800000000000+n,mono_ms:n});
const render=(session=null,overrides={})=>focusMarkup({session,tasks:[],setup,guide:false,...overrides});

test('MF free mode starts with one primary action and hides timed fields',()=>{
 const html=render();
 assert.match(html,/id="mf-mode"/);
 assert.match(html,/data-timed-settings hidden/);
 assert.match(html,/data-mf="start">开始专注/);
 assert.doesNotMatch(html,/mf-blocker-form|id="mf-rest-min"[^>]*required[^<]*<\/form>/);
 const timed=render(null,{setup:{...setup,mode:'pomodoro'}});
 assert.match(timed,/data-timed-settings[^>]*><label>/);
 assert.doesNotMatch(timed,/data-timed-settings hidden/);
});

test('MF active and paused session has precise state-specific controls',()=>{
 let s=transition(createSession({session_id:'focus'},stamp()),{type:'start'},stamp());
 assert.match(render(s),/data-mf="pause"/);
 assert.doesNotMatch(render(s),/data-mf="start"/);
 assert.doesNotMatch(render(s),/id="mf-mode"/);
 s=transition(s,{type:'pause'},stamp(2000));
 assert.match(render(s),/data-mf="resume"/);
 assert.doesNotMatch(render(s),/data-mf="pause"/);
 s=transition(s,{type:'end'},stamp(3000));
 assert.match(render(s),/本次专注已保存/);
});

test('MF long task names are escaped and accessible through expandable heading',()=>{
 const s=transition(createSession({session_id:'task',task_id:'task-1'},stamp()),{type:'start'},stamp());
 const html=render(s,{tasks:[{task_id:'task-1',title:'<img src=x onerror=alert(1)>'}]});
 assert.match(html,/class="mf-task-title-wrap"/);
 assert.match(html,/&lt;img src=x onerror=alert\(1\)&gt;/);
 assert.doesNotMatch(html,/<img src=x/);
});

test('help dialog is informational only; editing keeps explicit save action',()=>{
 const html=dialogMarkup('使用帮助','<p>说明</p>',false);
 assert.match(html,/data-cancel>关闭/);
 assert.doesNotMatch(html,/保存|data-error/);
 const edit=dialogMarkup('编辑任务','<input name="title">');
 assert.match(edit,/data-cancel>取消/);
 assert.match(edit,/保存/);
 assert.match(dialogMarkup('<script>','',false),/&lt;script&gt;/);
});

test('historical hide is list-only and does not alter seven-day totals',()=>{
 const finished=transition(transition(createSession({session_id:'done'},stamp()),{type:'start'},stamp()),{type:'end'},stamp(2000));
 const row={...empty(),history:[finished]},keys=[calendar.dayKey(stamp().wall_ms)];
 const all=recordsModel(row,keys,calendar);
 const hidden=recordsModel({...row,hidden_ids:['done']},keys,calendar);
 assert.equal(all.visible.length,1);
 assert.equal(hidden.visible.length,0);
 assert.deepEqual(all.summary,hidden.summary);
 assert.equal(hidden.summary.focus_ms,2000);
});
