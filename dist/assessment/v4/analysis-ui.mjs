import {request} from './api.mjs';
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function row(t,report){
 const qs=new URLSearchParams({course_id:'ap-physics-c-mechanics-2026-27',unit_id:t.topic_id.split('.')[0],topic_id:t.topic_id,return_to:location.href});
 const practice='/assessment/?'+qs+'#practice',pl='/?'+qs+'#topic/'+t.topic_id+'/reading';
 return `<article style="border-top:1px solid var(--line,#ddd);padding:16px 0"><h3>${esc(t.topic_id)} · ${esc(t.title)}</h3><p>${esc(t.evidence)}${t.priority?' · 可优先巩固':''}</p><p>独立已评分 ${t.independent_scored} 道 · 首次正确 ${t.first_correct} · 首次错误 ${t.first_incorrect} · 猜对但不确定 ${t.uncertain} 次</p><p>近 ${t.recent.days} 天：${t.recent.correct} / ${t.recent.unique_questions} 道独立题正确；重做：${t.retries.correct} / ${t.retries.attempts} 次正确（${t.retries.unique_questions} 道题，不增加独立样本）。</p><p>未作答 ${t.unanswered} · 未评分或答案待复核 ${t.ungraded} · 仅关联证据 ${t.associated_only}${t.legacy_independence_unknown?' · 旧记录独立性未知 '+t.legacy_independence_unknown:''}</p><details><summary>题型表现、日期变化与证据规则</summary><ul>${t.question_types.map(k=>`<li>${esc(k.type)}：${k.correct} / ${k.unique_questions} 道独立题正确</li>`).join('')||'<li>暂无可比较的题型证据。</li>'}</ul><ul>${t.timeline.map(d=>`<li>${esc(d.date)}：${d.correct} / ${d.unique_questions} 道首次独立题正确</li>`).join('')}</ul><p>仅单一核心 Topic 参与对错统计；综合题及关联 Topic 仅记录关联，不将一题错误归因于所有知识点。至少 5 道独立、无辅助且未标记不确定的题才显示证据较充分；这是描述性阈值，不是掌握概率。</p></details><p><a class="as-btn btn secondary small" href="${esc(practice)}">练习本知识点</a> <a class="as-btn btn secondary small" href="${esc(pl)}">查看 PL 教材</a></p></article>`;
}
export async function mountAnalysis(element,{sessionId=null}={}){
 try{
  const report=await request(sessionId?'/sessions/'+encodeURIComponent(sessionId)+'/analysis':'/analysis');
  if(!element.isConnected)return;
  const tested=report.topics.filter(t=>t.evidence!=='未评估'),unseen=report.topics.length-tested.length;
  element.innerHTML=`<div class="as-panel card pad"><h2>${sessionId?'本次':'长期'} Topic 学习证据</h2><p>已观察 ${tested.length} / ${report.topics.length} Topics · 未评估 ${unseen} · 未分类作答 ${report.unmapped_records} 次。</p><p class="muted">独立题量按稳定 Question ID 去重；重做与借助教材/提示后的正确另列。无可靠标准答案不参与对错统计。这里描述已有作答，不提供能力等级或掌握概率。</p>${tested.map(t=>row(t,report)).join('')||'<p>尚无知识点作答证据，未测的知识点保持“未评估”。</p>'}<details><summary>尚未评估的知识点（${unseen}）</summary>${report.topics.filter(t=>t.evidence==='未评估').map(t=>`<p>${esc(t.topic_id)} ${esc(t.title)} · 未评估</p>`).join('')}</details></div>`;
 }catch(error){if(element.isConnected)element.textContent='Topic 学习证据暂不可用：'+error.message;}
}
