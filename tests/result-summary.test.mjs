import test from 'node:test';
import assert from 'node:assert/strict';
import {renderResultSummary} from '../dist/assessment/v4/result-summary.mjs';

test('unknown grades never become zero percent or incorrect answers',()=>{
 const html=renderResultSummary({scoring_mode:'ungraded',total:3,answered:2,unanswered:1,graded:0,ungraded:3,accuracy:null,graded_accuracy:null,elapsed_ms:65000});
 assert.match(html,/成绩未知/);assert.match(html,/2 \/ 3/);assert.match(html,/1 分 5 秒/);
 assert.doesNotMatch(html,/%|<span>错误<\/span>/);
});
test('partial scores state their denominator and never claim a whole-paper rate',()=>{
 const html=renderResultSummary({scoring_mode:'partial',total:4,answered:3,unanswered:1,graded:2,ungraded:2,correct:1,incorrect:0,graded_unanswered:1,coverage:.5,accuracy:null,graded_accuracy:.5,elapsed_ms:0});
 assert.match(html,/2 \/ 4 题有可靠答案/);assert.match(html,/整卷正确率未知/);assert.match(html,/已评分部分正确率 50%/);
});
test('fully scored exams display their actual accuracy including zero',()=>{
 for (const accuracy of [0,1]) assert.match(renderResultSummary({scoring_mode:'graded',total:2,answered:2,unanswered:0,graded:2,ungraded:0,correct:accuracy*2,incorrect:(1-accuracy)*2,graded_unanswered:0,coverage:1,accuracy,elapsed_ms:0}),new RegExp(`正确率 ${accuracy*100}%`));
});
