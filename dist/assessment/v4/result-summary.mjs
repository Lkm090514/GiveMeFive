// Scores describe only questions with a reliable answer snapshot.
export function renderResultSummary(s) {
  if (!s) return '';
  const metric=(label,value)=>`<div><span>${label}</span><strong>${value}</strong></div>`;
  const percent=n=>`${Math.round(n*100)}%`;
  const time=Math.floor(s.elapsed_ms/60000)+' 分 '+Math.floor(s.elapsed_ms%60000/1000)+' 秒';
  const score=s.scoring_mode==='ungraded'
    ? '<p class="as-status">本卷不可评分：没有可靠原卷答案。作答已保存，成绩未知，不计入错题。</p>'
    : s.scoring_mode==='partial'
      ? `<p class="as-status">部分评分：${s.graded} / ${s.total} 题有可靠答案，评分覆盖 ${percent(s.coverage)}。整卷正确率未知；已评分部分正确率 ${percent(s.graded_accuracy)}。其余 ${s.ungraded} 题未评分，不视为错误。</p>`
      : `<p class="as-status">可评分考试 · 原卷答案覆盖 ${s.graded} / ${s.total} 题 · 正确率 ${percent(s.accuracy)}</p>`;
  const grades=s.graded ? metric('正确',s.correct)+metric('错误',s.incorrect)+metric('可评分题中未作答',s.graded_unanswered) : '';
  return `${score}<div class="as-metrics">${metric('已作答',`${s.answered} / ${s.total}`)}${metric('未作答',s.unanswered)}${metric('用时',time)}${metric('未评分',s.ungraded)}${grades}</div>`;
}
