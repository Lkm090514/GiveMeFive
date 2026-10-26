import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {validatePDF, bindPDFPicker, uploadPDF} from '../dist/assessment/v4/upload.mjs';

const file = (name = 'paper.pdf', size = 123, type = 'application/pdf') => ({name, size, type});
test('PDF selection rejects empty, wrong type, oversized and multiple files', () => {
  for (const files of [[], [file(), file()], [file('x.txt')], [file('x.pdf', 0)], [file('x.pdf', 51 * 1024 ** 2)], [file('x.pdf', 1, 'image/png')]]) assert.throws(() => validatePDF(files));
  assert.equal(validatePDF([file('PAPER.PDF', 1, '')]).name, 'PAPER.PDF');
});

test('dragging a PDF uses the same selection and invalidates an older upload request', () => {
  const handlers = {}, note = {dataset:{}}, input = {files:[], value:'', addEventListener(type, fn){handlers['input:'+type]=fn;}};
  const zone = {classList:{add(){},remove(){}}, contains(){return false;}, addEventListener(type, fn){handlers[type]=fn;}};
  const form = {elements:{file:input}, dataset:{requestKey:'old'}, querySelector(s){return s==='[data-pdf-drop]'?zone:note;}};
  const selected = bindPDFPicker(form), pdf = file();
  let prevented = false;
  handlers.drop({preventDefault(){prevented=true;},dataTransfer:{files:[pdf]}});
  assert.equal(prevented,true);assert.equal(selected(),pdf);assert.equal(form.dataset.requestKey,'');
  assert.match(note.textContent,/paper.pdf/);
  handlers.drop({preventDefault(){},dataTransfer:{files:[file('x.txt')]}});
  assert.throws(selected,/选择/);assert.equal(note.dataset.error,'true');
});

test('upload reports actual progress and surfaces server/network failures', async () => {
  let xhr;
  const prior = globalThis.XMLHttpRequest;
  globalThis.XMLHttpRequest = class {constructor(){xhr=this;this.upload={};}open(...args){this.target=args;}setRequestHeader(k,v){this.header=[k,v];}send(body){this.body=body;}};
  try {
    const progress=[],body={},success=uploadPDF(body,n=>progress.push(n));
    xhr.upload.onprogress({lengthComputable:true,loaded:25,total:100});
    assert.deepEqual(xhr.target,['POST','/api/v4/papers/import']);assert.deepEqual(xhr.header,['X-GMF-Request','1']);assert.equal(xhr.body,body);
    xhr.status=200;xhr.responseText='{"batch_id":"one"}';xhr.onload();
    assert.deepEqual(await success,{batch_id:'one'});assert.deepEqual(progress,[25]);
    const rejected=uploadPDF(body,()=>{});xhr.status=422;xhr.responseText='{"detail":"bad PDF"}';xhr.onload();await assert.rejects(rejected,/bad PDF/);
    const offline=uploadPDF(body,()=>{});xhr.onerror();await assert.rejects(offline,/连接中断/);
  } finally { globalThis.XMLHttpRequest=prior; }
});

test('active module navigation preserves its current subpage, including rapid clicks', () => {
  let handler;
  const ctx={URL,document:{currentScript:{src:'http://localhost/shared-shell.js'},addEventListener(type,fn,capture){assert.equal(capture,true);handler=fn;}},window:{LearningStore:{}}};
  vm.runInNewContext(fs.readFileSync('dist/shared-shell.js','utf8'),ctx);
  for(let i=0;i<3;i++){
    let prevented=false,stopped=false;
    handler({target:{closest:()=>({})},button:0,preventDefault(){prevented=true;},stopImmediatePropagation(){stopped=true;}});
    assert.ok(prevented&&stopped);
  }
  for(const extra of [{ctrlKey:true},{metaKey:true},{button:1}]) handler({target:{closest:()=>({})},button:0,preventDefault(){assert.fail('modified click must remain native');},...extra});
  handler({target:{closest:()=>null},button:0,preventDefault(){assert.fail('another module must navigate');}});
});
