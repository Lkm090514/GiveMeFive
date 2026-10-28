import {createSession,transition,timerView} from '../src/session.mjs';
const at=t=>({runtime_id:'demo',wall_ms:1800000000000+t,mono_ms:t});
let s=createSession({session_id:'example',mode:'pomodoro',focus_ms:5000},at(0));
for (const [time,command] of [[0,{type:'start'}],[6000,{type:'tick'}],[7000,{type:'rest'}],[9000,{type:'resume'}],[10000,{type:'end'}]]) {
  s=transition(s,command,at(time));console.log(JSON.stringify(timerView(s)));
}
