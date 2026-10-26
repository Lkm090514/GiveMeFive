export function renderAdminBank({report,filters,registry,esc,button,qBody,topicLabels,typeLabels,jobsHTML}) {
  const pick=(name,label,items)=>`<label>${label}<select name="${name}"><option value="">全部</option>${items.map(([id,title])=>`<option value="${esc(id)}" ${String(filters[name]??'')===String(id)?'selected':''}>${esc(title)}</option>`).join('')}</select></label>`;
  const types=registry.question_types,totals=report.totals;
  const coverage=report.coverage,covered=coverage.filter(t=>t.published>0).length;
  const filenames=new Map(report.sources.map(s=>[s.document_id,s.filename]));
  return `<a href="#practice">← 返回练习</a><span class="eyebrow" style="display:block;margin-top:25px">ADMIN · PUBLIC BANK</span>
  <h1>公共题库管理</h1><p class="muted">管理员维护公共题库。学生自己的 PDF 保持私人，不计入下面的题库数量。</p>
  <div class="as-metrics">${[['全部题目',totals.total],['已发布',totals.published],['答案待确认',totals.total-totals.verified],['结构异常',totals.structural]].map(([label,n])=>`<div><span>${label}</span><strong>${n}</strong></div>`).join('')}</div>
  <details class="as-panel"><summary>核心知识点覆盖 ${covered} / ${coverage.length} · 未分类 ${totals.unclassified} · 缺少题型 ${totals.untyped}</summary>
  <p class="muted">按已发布题的核心 Topic 统计；多 Topic 题分别计入各 Topic，不代表学生掌握程度。答案未确认的题不会作确定评分。</p>
  <div class="as-table-wrap"><table class="as-table"><thead><tr><th>PL Topic</th><th>已发布题数</th><th>其中答案已核对</th></tr></thead><tbody>${coverage.map(t=>`<tr><td>${esc(t.topic_id)} · ${esc(t.title)}</td><td>${t.published}</td><td>${t.verified}</td></tr>`).join('')}</tbody></table></div></details>
  <section class="as-panel"><h2>导入 PDF / DOCX</h2><form id="admin-import" class="as-form"><label>混合试卷<input name="file" type="file" accept=".pdf,.docx" multiple required></label><label>来源或授权说明<input name="license_name" required placeholder="例如：自行编写，或来源提供的复用许可"></label><label class="check"><input name="reuse_confirmed" type="checkbox" required>我已确认来源允许在当前题库中使用</label><div><button class="as-btn primary">上传并解析</button></div><small>每批 1–20 份文件，可持续追加。原文件、题号、页码、图像/公式与版本保留；FRQ 不进入 MCQ 题库。</small></form></section>
  <section class="as-panel"><div class="as-row"><h2>导入任务</h2>${button('刷新导入进度','data-refresh-admin')}</div><div id="admin-jobs">${jobsHTML()}</div></section>
  <section class="as-panel"><h2>发布原卷 MCQ 模考</h2><form id="admin-set" class="as-form"><div class="as-grid"><label>试卷名称<input name="title" required></label><label>来源年份<input name="source_year" placeholder="例如 2024"></label><label>考试分钟<input name="duration_minutes" type="number" min="0.01" max="600" step="0.01" value="45" required></label><label>原始试卷<select name="document_id" required><option value="">请选择来源</option>${report.sources.filter(s=>s.published>0).map(s=>`<option value="${esc(s.document_id)}">${esc(s.filename)} · ${s.published} 道已发布 MCQ</option>`).join('')}</select></label></div><p class="muted">由服务端选择该来源的全部已发布 MCQ，按原题号固定题目与版本，不受下面筛选或分页影响。</p><div><button class="as-btn">发布 MCQ 试卷</button></div></form></section>
  <section class="as-panel"><h2>筛选公共题库</h2><form id="admin-bank-filter" class="as-form"><label>题干或选项内容<input name="text" value="${esc(filters.text||'')}" maxlength="300" placeholder="搜索题目内容"></label><div class="as-grid">
  ${pick('document_id','来源试卷',report.sources.map(s=>[s.document_id,s.filename]))}
  ${pick('unit_id','Unit',registry.units.map(u=>[u.unit_id,`Unit ${u.unit_id} · ${u.title}`]))}
  ${pick('topic_id','核心或关联 Topic',registry.topics.map(t=>[t.topic_id,`${t.topic_id} ${t.title}`]))}
  ${pick('method','解题方法',Object.entries(types.methods))}
  ${pick('structure','题目模型',Object.entries(types.structures))}
  ${pick('publication','发布状态',[['approved','已发布'],['draft','草稿']])}
  ${pick('answer','答案状态',[['verified','已核对'],['unconfirmed','待确认']])}
  ${pick('issue','需要处理',[['structural','结构异常'],['unclassified','未确认核心 Topic'],['untyped','缺少解题类型']])}
  </div><div class="as-actions"><button class="as-btn primary">应用筛选</button><button class="as-btn" type="button" data-bank-reset>清除筛选</button></div></form></section>
  <section id="admin-bank-results"><h2>匹配 ${report.total} 道题</h2><p class="muted">${report.total?`显示 ${report.offset+1}–${Math.min(report.offset+report.limit,report.total)}`:'当前范围没有题目'}；每页 ${report.limit} 题。</p>
  ${report.items.map(q=>`<details class="as-panel"><summary>${esc(filenames.get(q.document_id)||'来源待确认')} · 原题 ${esc(q.source_number)} · ${q.publication==='approved'?'已发布':'草稿'} · ${q.answer?.status==='Verified'?'答案已核对':'答案待确认'} · ${q.meta.issues?.length?esc(q.meta.issues.join('，')):'结构可用'}</summary>${qBody(q)}
  <p class="muted">来源页 ${[...new Set(q.spans.map(s=>s.page))].map(esc).join('、')||'待确认'} · ${esc(q.version_id)}</p><div>${topicLabels(q)}${typeLabels(q)||'<small>解题类型待确认</small>'}</div><p class="muted">题型来源：${q.types.source.startsWith('admin:')?'管理员核对':q.types.source==='explicit-equation'?'显式公式规则':'自动分析或未分类'}</p>
  <p>答案：${esc(q.answer?.label||'待确认')} · 来源：${esc(q.answer?.confirmed_by||'未确认')}</p><div class="as-actions">${button('Topic 标签',`data-admin-tags="${esc(q.question_id)}"`)}${button('解题类型',`data-admin-types="${esc(q.question_id)}"`)}${button('题型修订记录',`data-type-history="${esc(q.question_id)}"`)}${button('修订答案',`data-admin-answer="${esc(q.question_id)}"`)}${button('修订题干 / 选项',`data-admin-edit="${esc(q.question_id)}"`)}${q.publication==='approved'?button('撤回',`data-admin-withdraw="${esc(q.question_id)}"`):button('审核并发布',`data-admin-publish="${esc(q.question_id)}"`)}</div></details>`).join('')||'<p class="as-empty">没有匹配的公共题目。可调整筛选，或导入新的管理员试卷。</p>'}
  <div class="as-actions">${button('上一页',`data-bank-page="${Math.max(0,report.offset-report.limit)}" ${report.offset===0?'disabled':''}`)}${button('下一页',`data-bank-page="${report.offset+report.limit}" ${report.offset+report.limit>=report.total?'disabled':''}`)}</div></section>`;
}
