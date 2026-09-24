#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const schema = JSON.parse(fs.readFileSync(path.join(root, 'templates/flow-document.schema.json'), 'utf8'));
const terminal = new Set(['success', 'failure', 'hold']);
const openBoundary = n => n.type === 'stream' && n.openEnded === true && typeof n.description === 'string' && n.description.trim().length > 0;
const hasEvidence = items => items?.some(s => [s.file,s.document].some(v => typeof v === 'string' && v.trim().length > 0));
const object = v => v !== null && typeof v === 'object' && !Array.isArray(v);
export function safeSourceUrl(value) {
  try { const u=new URL(value); return ['https:','http:'].includes(u.protocol) && !u.username && !u.password ? u.href : null; } catch { return null; }
}
const keywords = new Set(['$schema', 'title', 'description', 'type', 'required', 'properties', 'additionalProperties', 'items', 'enum', 'minLength', 'minItems', 'minimum', 'maximum', 'pattern']);

// Deliberately limited to the checked-in schema vocabulary; never silently ignore a new constraint.
function checkSchema(s) {
  for (const key of Object.keys(s)) if (!keywords.has(key)) throw Error(`Unsupported schema keyword: ${key}`);
  if (s.properties) Object.values(s.properties).forEach(checkSchema);
  if (s.items) checkSchema(s.items);
}
checkSchema(schema);

function shape(value, s, at, errors) {
  const types = { object, array: Array.isArray, string: v => typeof v === 'string', integer: Number.isSafeInteger, boolean: v => typeof v === 'boolean' };
  if (s.type && !types[s.type]?.(value)) { errors.push(`${at}: expected ${s.type}`); return; }
  if (s.enum && !s.enum.includes(value)) errors.push(`${at}: unknown value ${JSON.stringify(value)}`);
  if (typeof value === 'string') {
    if (s.minLength && value.trim().length < s.minLength) errors.push(`${at}: empty text`);
    if (s.pattern && !new RegExp(s.pattern).test(value)) errors.push(`${at}: invalid format`);
  }
  if (typeof value === 'number') {
    if (s.minimum !== undefined && value < s.minimum) errors.push(`${at}: below ${s.minimum}`);
    if (s.maximum !== undefined && value > s.maximum) errors.push(`${at}: above ${s.maximum}`);
  }
  if (Array.isArray(value)) {
    if (s.minItems && value.length < s.minItems) errors.push(`${at}: needs at least ${s.minItems} items`);
    if (s.items) value.forEach((v,i) => shape(v,s.items,`${at}[${i}]`,errors));
  }
  if (object(value)) {
    for (const key of s.required || []) if (!Object.hasOwn(value,key)) errors.push(`${at}.${key}: required`);
    for (const [key,v] of Object.entries(value)) {
      if (s.properties && Object.hasOwn(s.properties,key)) shape(v,s.properties[key],`${at}.${key}`,errors);
      else if (s.additionalProperties === false) errors.push(`${at}.${key}: unknown property`);
    }
  }
}

function walk(seeds, links) {
  const reached = new Set(seeds), queue = [...seeds];
  for (let i=0; i<queue.length; i++) for (const id of links.get(queue[i]) || []) if (!reached.has(id)) { reached.add(id); queue.push(id); }
  return reached;
}

export function validateDocument(data) {
  const errors=[], warnings=[];
  shape(data,schema,'document',errors);
  if (errors.length) return {status:'FAIL',errors,warnings};
  const flowIds = new Set();
  const allFlowIds = new Set(data.flows.map(f=>f.id));
  const detailed = data.meta.detailLevel === 'detailed';
  const detailIssue = message => (detailed ? errors : warnings).push(message);
  const meaningful = v => typeof v === 'string' && v.trim().length > 0;
  for (const f of data.flows) {
    const prefix = f.id;
    if (flowIds.has(f.id)) errors.push(`${prefix}: duplicate flow id`);
    flowIds.add(f.id);
    const nodes = new Map(), edges = new Map(), places = new Set(), next = new Map(), prev = new Map();
    if (!f.scenarios?.length) detailIssue(`${prefix}: scenario coverage missing`);
    if (detailed && !f.coverage) detailIssue(`${prefix}: detailed flow requires coverage scope and basis`);
    const evidence=[...(f.sources||[]),...f.nodes.flatMap(n=>n.source||[]),...(f.failureCases||[]).flatMap(c=>c.source||[]),...(f.api?.schemas||[]).flatMap(s=>s.source||[])];
    for (const s of evidence) if(s.url && !safeSourceUrl(s.url)) errors.push(`${prefix}: unsafe source URL`);
    for (const n of f.nodes) {
      if (nodes.has(n.id)) errors.push(`${prefix}/${n.id}: duplicate node id`);
      nodes.set(n.id,n);
      if (n.openEnded && !openBoundary(n)) errors.push(`${prefix}/${n.id}: openEnded requires a stream and boundary description`);
      const place=`${n.row},${n.column}`;
      if (places.has(place)) errors.push(`${prefix}/${n.id}: overlapping node position`);
      places.add(place);
      if (n.title.length > 40) warnings.push(`${prefix}/${n.id}: long title; shorten chart label`);
      if (n.type !== 'note' && !(hasEvidence(n.source) || hasEvidence(f.sources))) warnings.push(`${prefix}/${n.id}: source evidence missing`);
      if(n.type!=='note') {
        if(!meaningful(n.description)) detailIssue(`${prefix}/${n.id}: description missing`);
        if(detailed && !meaningful(n.owner)) detailIssue(`${prefix}/${n.id}: owner missing`);
        if(detailed && !(n.outputs?.some(meaningful))) detailIssue(`${prefix}/${n.id}: outcome missing`);
        if(detailed && !hasEvidence(n.source)) detailIssue(`${prefix}/${n.id}: node evidence missing`);
        if(n.type==='decision' && !meaningful(n.condition)) detailIssue(`${prefix}/${n.id}: decision condition missing`);
      }
      if(n.flowRef && !allFlowIds.has(n.flowRef)) errors.push(`${prefix}/${n.id}: unknown detail flow ${n.flowRef}`);
      for(const value of [n.title,n.description,n.condition,...(n.inputs||[]),...(n.outputs||[])]) if(typeof value==='string' && /\b(TODO|TBD|undefined)\b|\uFFFD/.test(value)) detailIssue(`${prefix}/${n.id}: unfinished text`);
    }
    for (const e of f.edges) {
      if (edges.has(e.id)) errors.push(`${prefix}/${e.id}: duplicate edge id`);
      edges.set(e.id,e);
      if (!nodes.has(e.from) || !nodes.has(e.to)) { errors.push(`${prefix}/${e.id}: missing endpoint`); continue; }
      if (nodes.get(e.from).type === 'note' || nodes.get(e.to).type === 'note') errors.push(`${prefix}/${e.id}: note cannot be an execution endpoint`);
      if (!next.has(e.from)) next.set(e.from,[]);
      if (!prev.has(e.to)) prev.set(e.to,[]);
      next.get(e.from).push(e.to); prev.get(e.to).push(e.from);
    }
    const entries = f.nodes.filter(n => n.type === 'start' || n.entry === true).map(n => n.id);
    const ends = f.nodes.filter(n => terminal.has(n.type) || openBoundary(n)).map(n => n.id);
    if (!entries.length) errors.push(`${prefix}: no entry node`);
    if (!ends.length) errors.push(`${prefix}: no terminal node`);
    const reachable = walk(entries,next), terminating = walk(ends,prev);
    for (const n of f.nodes) {
      if (n.type === 'note') { if(n.entry) errors.push(`${prefix}/${n.id}: note cannot be entry`); continue; }
      if (!reachable.has(n.id)) errors.push(`${prefix}/${n.id}: unreachable from entry`);
      if (!terminating.has(n.id)) errors.push(`${prefix}/${n.id}: no path to terminal`);
      const outgoing = f.edges.filter(e => e.from === n.id);
      if (terminal.has(n.type) && outgoing.length) errors.push(`${prefix}/${n.id}: terminal has outgoing edge`);
      if (n.type === 'decision') {
        if (outgoing.length < 2) errors.push(`${prefix}/${n.id}: decision needs two branches`);
        const labels = outgoing.map(e => e.label?.trim() || '');
        if (labels.some(x => !x) || new Set(labels).size !== labels.length) errors.push(`${prefix}/${n.id}: decision labels must be nonempty and distinct`);
      }
    }
    const scenarioIds = new Set();
    for (const s of f.scenarios || []) {
      const at=`${prefix}/${s.id}`;
      if (scenarioIds.has(s.id)) errors.push(`${at}: duplicate scenario id`);
      scenarioIds.add(s.id);
      if (!entries.includes(s.path[0])) errors.push(`${at}: scenario must start at entry`);
      const last=nodes.get(s.path.at(-1));
      if (s.kind==='ongoing' ? !last || !openBoundary(last) : last?.type !== s.kind) errors.push(`${at}: scenario terminal kind mismatch`);
      for (const id of s.path) if (!nodes.has(id) || nodes.get(id).type === 'note') errors.push(`${at}: invalid scenario node ${id}`);
      if (s.edgePath && s.edgePath.length !== s.path.length-1) errors.push(`${at}: edgePath length mismatch`);
      for (let i=1; i<s.path.length; i++) {
        const matches=f.edges.filter(e => e.from === s.path[i-1] && e.to === s.path[i]);
        if (!matches.length) errors.push(`${at}: disconnected scenario step ${s.path[i-1]} -> ${s.path[i]}`);
        if (s.edgePath) { if (!matches.some(e => e.id === s.edgePath[i-1])) errors.push(`${at}: edgePath does not match path`); }
        else if (matches.length > 1) errors.push(`${at}: ambiguous step requires edgePath`);
      }
    }
    const covered=new Set((f.scenarios||[]).flatMap(s=>s.path));
    for(const n of f.nodes) if(terminal.has(n.type) && !covered.has(n.id)) detailIssue(`${prefix}/${n.id}: terminal has no scenario`);
    const caseIds=new Set();
    for(const c of f.failureCases||[]) {
      const at=`${prefix}/${c.id}`;
      if(caseIds.has(c.id)) errors.push(`${at}: duplicate failure case`);
      caseIds.add(c.id);
      const scenario=(f.scenarios||[]).find(s=>s.id===c.scenarioId);
      if(!nodes.has(c.nodeId)) errors.push(`${at}: failure origin missing`);
      if(!scenario || !scenario.path.includes(c.nodeId)) errors.push(`${at}: failure case does not match scenario`);
      else {
        const idx=scenario.path.indexOf(c.nodeId),edge= f.edges.find(e=>e.from===c.nodeId&&e.to===scenario.path[idx+1]&&(!scenario.edgePath||e.id===scenario.edgePath[idx]));
        if(!edge || !['failure','compensation'].includes(edge.kind)) errors.push(`${at}: failure scenario must leave origin on failure/compensation edge`);
      }
    }
    if(detailed) for(const s of f.scenarios||[]) if(s.kind==='failure' && !(f.failureCases||[]).some(c=>c.scenarioId===s.id)) detailIssue(`${prefix}/${s.id}: failure details missing`);
    if(f.edges.some(e=>['async','callback'].includes(e.kind)) && !f.completion) detailIssue(`${prefix}: asynchronous completion contract missing`);
  }
  return {status:errors.length?'FAIL':warnings.length?'WARN':'PASS',errors,warnings};
}

const escapeHtml = value => String(value).replace(/[&<>"']/g,c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

export function buildHtml(data) {
  const result=validateDocument(data);
  if (result.errors.length) throw Error(result.errors.join('\n'));
  const css=fs.readFileSync(path.join(root,'styles/flow.css'),'utf8');
  const js=fs.readFileSync(path.join(root,'scripts/flow-viewer.js'),'utf8');
  const payload=JSON.stringify(data).replaceAll('<','\\u003c').replaceAll('\u2028','\\u2028').replaceAll('\u2029','\\u2029');
  return `<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>${escapeHtml(data.meta.title)}</title><style>${css}</style></head>
<body><a class="skip" href="#main">본문으로 이동</a><header><strong id="brand"></strong><span id="stamp"></span></header>
<button id="menu" type="button" aria-controls="sidebar" aria-expanded="false">흐름 검색·목록</button>
<div class="layout"><aside id="sidebar" aria-label="흐름 검색과 목록"><div class="side-head"><h2>백엔드 흐름</h2><label for="search">흐름 검색</label><div class="search-row"><input id="search" type="search" placeholder="로그인, POST, /api/payments"><button id="search-clear" type="button" aria-label="검색어 지우기">지우기</button></div><label for="category">분류</label><select id="category"></select><div class="search-meta"><p id="search-status" role="status"></p><button id="filter-reset" type="button" hidden>검색·필터 초기화</button></div></div><nav id="flows" aria-label="검색된 흐름"></nav></aside>
<main id="main" tabindex="-1"><p id="provenance" class="source"></p><h1 id="title" tabindex="-1"></h1><p id="summary"></p><p id="implementation"></p><dl id="facts"></dl><div id="coverage"></div><div id="completion"></div><section class="chart-card" aria-label="흐름 탐색"><div class="toolbar"><div class="scenario-controls"><div id="result-buttons" class="result-buttons" role="group" aria-label="결과별 흐름 보기"></div><div id="scenario-picker" class="scenario-picker" hidden><label id="scenario-label" for="scenario">세부 경로</label><select id="scenario"></select></div></div><div class="zoom-tools" aria-label="차트 확대 도구"><button id="zoom-out" aria-label="차트 축소">−</button><output id="zoom-label"></output><button id="zoom-in" aria-label="차트 확대">＋</button><button id="zoom-fit">맞춤</button><button id="zoom-reset">100%</button></div></div><p id="scenario-summary" role="status" aria-live="polite"></p><div id="failure-detail"></div><p class="legend">◇ 판단 · ▱ 입출력 · 원통 저장소 · 이중 테두리 외부 시스템 · 점선 비동기/콜백/보상 · 보류는 실패와 구분</p><div id="chart" tabindex="0" role="region" aria-label="플로우차트, 가로 스크롤 가능"></div></section><h2>단계별 설명</h2><div id="details"></div><details id="api-contract" hidden><summary>API 계약·요청 구조</summary><div id="api-details"></div></details><details><summary>흐름 근거</summary><ul id="sources"></ul></details></main></div>
<script type="application/json" id="flow-data">${payload}</script><script>${js}</script></body></html>`;
}

export function main(args) {
  try {
    const [command,input,output,...flags]=args;
    if (!['validate','build'].includes(command) || !input || (command==='validate' && args.length!==2) || (command==='build' && (!output || flags.some(f=>f!=='--overwrite') || flags.length>1))) throw Error('usage: flow-document.mjs validate <flow.json> | build <flow.json> <output.html> [--overwrite]');
    const data=JSON.parse(fs.readFileSync(input,'utf8').replace(/^\uFEFF/,''));
    const result=validateDocument(data);
    if (result.errors.length) { console.log(JSON.stringify(result,null,2)); return 1; }
    if (command==='build') {
      const target=path.resolve(output), source=fs.realpathSync(input);
      if (!['.html','.htm'].includes(path.extname(target).toLowerCase())) throw Error('Output must be .html or .htm');
      let ancestor=target;const suffix=[];
      while (!fs.existsSync(ancestor)) { suffix.unshift(path.basename(ancestor));const parent=path.dirname(ancestor);if(parent===ancestor)throw Error('No existing output ancestor');ancestor=parent; }
      const resolved=path.join(fs.realpathSync(ancestor),...suffix);
      const same=(a,b)=>process.platform==='win32'?a.toLowerCase()===b.toLowerCase():a===b;
      if (same(resolved,source)) throw Error('Input and output must differ');
      if (fs.existsSync(target)) {
        const inputStat=fs.statSync(input), outputStat=fs.statSync(target);
        if (inputStat.ino===outputStat.ino && inputStat.dev===outputStat.dev) throw Error('Input and output must not alias the same file');
      }
      const rel=path.relative(fs.realpathSync(root),resolved);
      if (rel==='' || (!rel.startsWith('..'+path.sep) && rel!=='..' && !path.isAbsolute(rel))) throw Error('Output cannot overwrite skill resources');
      fs.mkdirSync(path.dirname(target),{recursive:true});
      // wx preserves an existing output unless the caller explicitly chose overwrite.
      fs.writeFileSync(target,buildHtml(data),{encoding:'utf8',flag:flags.includes('--overwrite')?'w':'wx'});
      result.output=output;
    }
    console.log(JSON.stringify(result,null,2)); return 0;
  } catch (error) { console.error(JSON.stringify({status:'FAIL',errors:[error.message],warnings:[]})); return 1; }
}
if (process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) process.exitCode=main(process.argv.slice(2));
