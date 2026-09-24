import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { validateDocument, buildHtml, safeSourceUrl } from '../../skills/universal-flow-document/scripts/flow-document.mjs';

const skill=fileURLToPath(new URL('../../skills/universal-flow-document/',import.meta.url));
const cli=path.join(skill,'scripts/flow-document.mjs');
const fixture=()=>({meta:{title:'검증 흐름'},flows:[{id:'flow',title:'저장',summary:'입력을 확인해 저장합니다.',completion:{acceptance:'접수',processing:'처리',resultDelivery:'조회'},sources:[{document:'Test fixture; not production evidence'}],nodes:[
  {id:'start',type:'start',title:'요청',description:'입력을 받는다.',row:0,column:0},
  {id:'check',type:'decision',title:'유효?',description:'입력값을 검사한다.',condition:'입력의 필수값이 존재하는가?',row:1,column:0},
  {id:'ok',type:'success',title:'저장 완료',description:'저장한 결과를 반환한다.',row:2,column:-1},
  {id:'fail',type:'failure',title:'거부',description:'입력 오류를 반환한다.',row:2,column:1}
],edges:[{id:'entry',from:'start',to:'check',kind:'sync'},{id:'yes',from:'check',to:'ok',kind:'success',label:'예'},{id:'no',from:'check',to:'fail',kind:'failure',label:'아니오'}],scenarios:[{id:'success',label:'성공',kind:'success',path:['start','check','ok']},{id:'failure',label:'실패',kind:'failure',path:['start','check','fail']}]}]});
function fails(mutate,pattern){const d=fixture();mutate(d,d.flows[0]);const r=validateDocument(d);assert.equal(r.status,'FAIL');assert.match(r.errors.join('\n'),pattern);}
test('valid branching document and both scenarios pass',()=>assert.deepEqual(validateDocument(fixture()),{status:'PASS',errors:[],warnings:[]}));
test('empty and malformed input are rejected without throwing',()=>{for(const d of [null,[],{}, {meta:{title:'x'},flows:[]},{meta:{title:'x'},flows:[null]}])assert.equal(validateDocument(d).status,'FAIL');});
test('wrong field types and unknown semantic types fail',()=>{fails((d,f)=>{f.nodes[0].row='0';},/expected integer/);fails((d,f)=>{f.nodes[0].type='made-up';},/unknown value/);fails((d,f)=>{f.nodes[0].inputs='x';},/expected array/);});
test('blank titles, invalid IDs and unbounded coordinates fail',()=>{fails(d=>{d.meta.title=' ';},/empty text/);fails((d,f)=>{f.nodes[0].id='bad"id';},/invalid format/);fails((d,f)=>{f.nodes[0].column=101;},/above/);});
test('duplicate flow/node/edge/scenario IDs fail',()=>{
  fails(d=>d.flows.push(structuredClone(d.flows[0])),/duplicate flow/);
  fails((d,f)=>f.nodes.push({...f.nodes[0],row:5}),/duplicate node/);
  fails((d,f)=>f.edges.push({...f.edges[0]}),/duplicate edge/);
  fails((d,f)=>f.scenarios.push({...f.scenarios[0]}),/duplicate scenario/);
});
test('missing endpoint and overlapping layout fail',()=>{fails((d,f)=>{f.edges[0].to='missing';},/missing endpoint/);fails((d,f)=>{f.nodes[2].column=1;},/overlapping/);});
test('disconnected cycle with incoming edges is rejected',()=>fails((d,f)=>{f.nodes.push({id:'a',type:'process',title:'A',row:4,column:0},{id:'b',type:'process',title:'B',row:5,column:0});f.edges.push({id:'ab',from:'a',to:'b',kind:'sync'},{id:'ba',from:'b',to:'a',kind:'callback'});},/unreachable from entry/));
test('reachable dead end and terminal outgoing edges fail',()=>{fails((d,f)=>{f.nodes[2].type='process';},/no path to terminal/);fails((d,f)=>f.edges.push({id:'back',from:'ok',to:'check',kind:'callback'}),/terminal has outgoing/);});
test('missing entry and terminal fail',()=>{fails((d,f)=>{f.nodes[0].type='process';},/no entry/);fails((d,f)=>{f.nodes[2].type='process';f.nodes[3].type='process';},/no terminal/);});
test('ongoing streams require an explicit documented boundary and ongoing scenario',()=>{
  const d=fixture(),f=d.flows[0];f.nodes[2].type='stream';f.nodes[2].openEnded=true;f.nodes[2].description='Connection remains open; flow scope ends here.';f.scenarios[0].kind='ongoing';
  assert.equal(validateDocument(d).status,'PASS');f.scenarios[0].kind='success';assert.match(validateDocument(d).errors.join('\n'),/terminal kind/);
  delete f.nodes[2].description;assert.match(validateDocument(d).errors.join('\n'),/boundary description/);
});
test('decision needs multiple distinct nonempty labels',()=>{fails((d,f)=>f.edges.pop(),/two branches/);fails((d,f)=>{f.edges[2].label='예';},/distinct/);fails((d,f)=>{delete f.edges[2].label;},/nonempty/);});
test('scenario must use connected steps with correct start and outcome',()=>{fails((d,f)=>{f.scenarios[0].path=['start','ok'];},/disconnected/);fails((d,f)=>{f.scenarios[0].path=['check','ok'];},/start at entry/);fails((d,f)=>{f.scenarios[0].kind='failure';},/terminal kind/);});
test('parallel edges require exact scenario edgePath',()=>{
  const d=fixture(),f=d.flows[0];f.edges.push({id:'also',from:'start',to:'check',kind:'async'});
  assert.match(validateDocument(d).errors.join('\n'),/ambiguous/);
  f.scenarios[0].edgePath=['entry','yes'];f.scenarios[1].edgePath=['also','no'];assert.equal(validateDocument(d).status,'PASS');
  f.scenarios[0].edgePath=['no','yes'];assert.match(validateDocument(d).errors.join('\n'),/does not match/);
});
test('notes are documentation only',()=>{fails((d,f)=>{f.nodes[1].type='note';},/note cannot/);const d=fixture();d.flows[0].nodes.push({id:'note',type:'note',title:'설명',row:4,column:0});assert.equal(validateDocument(d).status,'PASS');});
test('lack of source evidence remains WARN, not semantic approval',()=>{const d=fixture();delete d.flows[0].sources;const r=validateDocument(d);assert.equal(r.status,'WARN');assert.equal(r.errors.length,0);assert.equal(r.warnings.length,4);d.flows[0].sources=[{}];assert.equal(validateDocument(d).status,'WARN');});
test('all reference graphs remain structurally valid and detailed API example is complete',()=>{const refs=fs.readdirSync(path.join(skill,'references')).filter(f=>f.endsWith('.json'));assert.ok(refs.includes('detailed-api.json'));for(const name of refs){const r=validateDocument(JSON.parse(fs.readFileSync(path.join(skill,'references',name),'utf8')));assert.deepEqual(r.errors,[],name);if(name==='detailed-api.json')assert.equal(r.status,'PASS');}});
test('HTML preserves one JSON payload and neutralizes script-closing text',()=>{
  const d=fixture();d.meta.title='</title><script>alert(1)</script>';d.flows[0].nodes[0].description='</script><img src=x onerror=alert(1)>';
  const html=buildHtml(d),payload=html.match(/<script type="application\/json" id="flow-data">([\s\S]*?)<\/script>/)[1];
  assert.deepEqual(JSON.parse(payload),d);assert.ok(!payload.includes('<'));assert.ok(html.includes('&lt;/title&gt;'));
  assert.equal((html.match(/id="flow-data"/g)||[]).length,1);
});
test('HTML exposes left search, result buttons, conditional scenario picker and reset controls',()=>{
  const html=buildHtml(fixture());
  for(const id of ['search','search-clear','category','search-status','filter-reset','result-buttons','scenario-picker','scenario'])assert.match(html,new RegExp(`id="${id}"`));
  assert.match(html,/aria-label="결과별 흐름 보기"/);
  assert.match(html,/흐름 검색·목록/);
  assert.doesNotMatch(html,/<label[^>]+for="scenario">시나리오<\/label>/);
});
test('invalid data cannot be rendered',()=>assert.throws(()=>buildHtml({}),/required/));

function detailedFixture(){const d=fixture();d.meta.detailLevel='detailed';const f=d.flows[0];f.coverage={scope:'입력 검증',basis:'테스트 계약'};for(const n of f.nodes){n.owner='테스트 주체';n.outputs=['관측 가능한 결과'];n.source=[{document:'Test fixture'}];}f.failureCases=[{id:'invalid',nodeId:'check',scenarioId:'failure',condition:'필수값 없음',effect:'저장하지 않음',nextAction:'필수값을 보완',status:'400',code:'MISSING'}];return d;}
test('empty explanation cannot silently pass even in legacy mode',()=>{const d=fixture();for(const n of d.flows[0].nodes)delete n.description;delete d.flows[0].scenarios;const r=validateDocument(d);assert.equal(r.status,'WARN');assert.match(r.warnings.join('\n'),/description missing/);assert.match(r.warnings.join('\n'),/scenario coverage missing/);});
test('detailed mode requires node-level explanation, owner, outcome, evidence and decisions',()=>{assert.equal(validateDocument(detailedFixture()).status,'PASS');for(const key of ['description','owner','outputs','source','condition']){const d=detailedFixture();delete d.flows[0].nodes[1][key];assert.equal(validateDocument(d).status,'FAIL',key);}});
test('detailed failure origin and linked scenario must describe actual failure branch',()=>{for(const mutate of [f=>{f.failureCases[0].nodeId='missing';},f=>{f.failureCases[0].scenarioId='success';},f=>{delete f.failureCases[0].nextAction;},f=>{f.failureCases=[];},f=>{f.failureCases.push({...f.failureCases[0]});}]){const d=detailedFixture();mutate(d.flows[0]);assert.equal(validateDocument(d).status,'FAIL');}});
test('hold is a separate terminal with a matching scenario',()=>{const d=detailedFixture(),f=d.flows[0];f.nodes[3].type='hold';f.scenarios[1].kind='hold';assert.equal(validateDocument(d).status,'PASS');f.scenarios[1].kind='failure';assert.equal(validateDocument(d).status,'FAIL');});
test('unsafe source URLs are rejected without weakening literal content escaping',()=>{for(const url of ['javascript:alert(1)','data:text/html,x','file:///etc/passwd','https://user:secret@example.com','//example.com']){assert.equal(safeSourceUrl(url),null);const d=fixture();d.flows[0].sources[0].url=url;assert.equal(validateDocument(d).status,'FAIL');}assert.equal(safeSourceUrl('https://example.com/code#L1'),'https://example.com/code#L1');});
test('detail flow references and asynchronous completion contracts are checked',()=>{const d=detailedFixture();d.flows[0].nodes[0].flowRef='absent';assert.equal(validateDocument(d).status,'FAIL');delete d.flows[0].nodes[0].flowRef;d.flows[0].edges[0].kind='async';delete d.flows[0].completion;assert.match(validateDocument(d).errors.join('\n'),/completion contract/);});
test('API contracts and incomplete text have meaningful validation',()=>{const d=detailedFixture();d.flows[0].api={method:'POST',path:'/items',request:'name',response:'201',schemas:[{name:'Request',body:'{"name":"<literal>"}'}]};assert.equal(validateDocument(d).status,'PASS');d.flows[0].nodes[1].description='TODO';assert.equal(validateDocument(d).status,'FAIL');delete d.flows[0].api.request;assert.match(validateDocument(d).errors.join('\n'),/request: required/);});

test('harness document title check supports skill frontmatter without accepting missing titles',t=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'harness-flow-test-'));
  t.after(()=>{assert.ok(path.dirname(dir)===os.tmpdir()&&path.basename(dir).startsWith('harness-flow-test-'));fs.rmSync(dir,{recursive:true,force:true});});
  fs.mkdirSync(path.join(dir,'skills'));fs.mkdirSync(path.join(dir,'scripts'));
  fs.writeFileSync(path.join(dir,'00.HARNESS_RULES.md'),'# Rules\n## 3. 충돌 해결 우선순위\n| rule | value |\n| a | b |\n');
  fs.writeFileSync(path.join(dir,'00.QUICK_REF.md'),'# Quick\n## 1. 충돌 우선순위\n00.HARNESS_RULES.md §3\n');
  const checker=fileURLToPath(new URL('../validate-docs.mjs',import.meta.url));
  for(const [body,expected]of [['# Skill\n',0],['---\r\nname: sample\r\n---\r\n\r\n# Skill\n',0],['---\nname: sample\n---\nNo title\n',1],['---\nname: sample\n# Skill\n',1]]){
    fs.writeFileSync(path.join(dir,'skills','SKILL.md'),body);assert.equal(spawnSync(process.execPath,[checker],{cwd:dir,encoding:'utf8'}).status,expected);
  }
});
test('CLI validates, refuses invalid writes, and preserves output by default',t=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'harness-flow-test-'));
  t.after(()=>{assert.ok(path.dirname(dir)===os.tmpdir()&&path.basename(dir).startsWith('harness-flow-test-'));fs.rmSync(dir,{recursive:true,force:true});});
  const input=path.join(dir,'flow.json'),output=path.join(dir,'result.html');fs.writeFileSync(input,JSON.stringify(fixture()));
  const run=(...args)=>spawnSync(process.execPath,[cli,...args],{encoding:'utf8'});
  assert.equal(run('validate',input).status,0);assert.equal(run('build',input,output).status,0);
  fs.writeFileSync(output,'preserve me');assert.notEqual(run('build',input,output).status,0);assert.equal(fs.readFileSync(output,'utf8'),'preserve me');
  assert.equal(run('build',input,output,'--overwrite').status,0);assert.match(fs.readFileSync(output,'utf8'),/<!doctype html>/);
  fs.writeFileSync(input,'{}');assert.notEqual(run('build',input,output,'--overwrite').status,0);assert.match(fs.readFileSync(output,'utf8'),/<!doctype html>/);
  fs.writeFileSync(input,'{');assert.notEqual(run('validate',input).status,0);assert.notEqual(run('unknown',input).status,0);
});
test('CLI prevents skill-resource overwrite and input alias overwrite',t=>{
  const dir=fs.mkdtempSync(path.join(os.tmpdir(),'harness-flow-test-'));
  t.after(()=>{assert.ok(path.dirname(dir)===os.tmpdir()&&path.basename(dir).startsWith('harness-flow-test-'));fs.rmSync(dir,{recursive:true,force:true});});
  const input=path.join(dir,'flow.html');fs.writeFileSync(input,JSON.stringify(fixture()));
  const run=(...args)=>spawnSync(process.execPath,[cli,...args],{encoding:'utf8'});
  assert.notEqual(run('build',input,input,'--overwrite').status,0);assert.deepEqual(JSON.parse(fs.readFileSync(input,'utf8')),fixture());
  const alias=path.join(dir,'alias.html');fs.linkSync(input,alias);assert.notEqual(run('build',input,alias,'--overwrite').status,0);assert.deepEqual(JSON.parse(fs.readFileSync(input,'utf8')),fixture());
  assert.notEqual(run('build',input,path.join(skill,'should-not-exist.html'),'--overwrite').status,0);assert.equal(fs.existsSync(path.join(skill,'should-not-exist.html')),false);
  const blockedDirectory=path.join(skill,'should-not-create-directory');assert.notEqual(run('build',input,path.join(blockedDirectory,'out.html')).status,0);assert.equal(fs.existsSync(blockedDirectory),false);
});
