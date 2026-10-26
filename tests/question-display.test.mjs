import test from 'node:test';
import assert from 'node:assert/strict';
import {usesOriginalVisual,optionCaption} from '../dist/assessment/v4/question-display.mjs';
test('damaged formula and visual option text defers to original artwork',()=>{
  const q={assets:['crop'],has_visual:true,options:[{label:'A',text:'[Visual option A; inspect original question crop]'}]};
  assert.equal(usesOriginalVisual(q),true);assert.equal(optionCaption(q,q.options[0]),'选择 A（见原题选项）');
  assert.equal(usesOriginalVisual({...q,has_visual:false}),true);assert.equal(usesOriginalVisual({assets:['crop'],formula_fragments:['t²']}),true);
});
test('ordinary text choices and choices without artwork retain available text',()=>{
  const o={label:'B',text:'north'};assert.equal(optionCaption({assets:['crop']},o),'north');assert.equal(optionCaption({assets:[],has_visual:true},o),'north');
});
