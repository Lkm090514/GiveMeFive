import test from 'node:test';
import assert from 'node:assert/strict';
import {cachedExamLock} from '../dist/assessment/v4/session-navigation.mjs';
test('completed exam releases stale navigation lock on first results-to-mistakes click',()=>{
  assert.equal(cachedExamLock('exam1',{id:'exam1',mode:'exam',status:'submitted'}),null);
});
test('active exams and a different exam cannot be released by unrelated results',()=>{
  assert.equal(cachedExamLock('exam1',{id:'exam1',mode:'exam',status:'active'}),'exam1');
  assert.equal(cachedExamLock('exam2',{id:'exam1',mode:'exam',status:'submitted'}),'exam2');
  assert.equal(cachedExamLock('exam1',{id:'exam1',mode:'practice',status:'submitted'}),'exam1');
});
