#!/usr/bin/env node
// harness-stats: 프로젝트 reports/ 폴더의 Report 헤더를 집계해 "하네스 성적표"를 출력한다.
//
// 용도: 프로젝트 마무리 시점의 환류(ADR-041)와 skill-stocktake 판정을 데이터 기반으로 만든다.
// 챱챱 실사용 분석(2026-08-02)을 사람이 20~30분 걸려 수행했던 것을 자동화한 것이다.
//
// 이 스크립트는 통계 도구이며 판정 도구가 아니다 — 항상 exit 0으로 끝나고 CI 차단에
// 사용하지 않는다(검증은 validate-*.mjs가 담당). 출력의 ⚠ 표시는 stocktake·환류에서
// 사람이 판단할 후보를 표시한 것이다.
//
// 사용법:
//   node scripts/harness-stats.mjs                      # 하네스 루트의 reports/ 집계
//   node scripts/harness-stats.mjs --dir <경로>          # 부착 프로젝트의 reports/ 집계
//   node scripts/harness-stats.mjs --include-archive    # archive/ 포함
import fs from 'node:fs';
import path from 'node:path';

function isHarnessRoot(dir) {
  return fs.existsSync(path.join(dir, '00.HARNESS_RULES.md')) &&
    fs.existsSync(path.join(dir, 'skills')) &&
    fs.existsSync(path.join(dir, 'scripts'));
}
function resolveRoot() {
  const cwd = process.cwd();
  if (isHarnessRoot(cwd)) return cwd;
  const parent = path.dirname(cwd);
  if (isHarnessRoot(parent)) return parent;
  const preferred = path.join(cwd, 'GENERAL_HARNESS');
  if (isHarnessRoot(preferred)) return preferred;
  console.error('FAIL cannot locate GENERAL_HARNESS root. Run from the harness root or its parent directory.');
  process.exit(1);
}

const args = process.argv.slice(2);
const includeArchive = args.includes('--include-archive');
const dirFlag = args.indexOf('--dir');
const root = resolveRoot();
const reportsDir = dirFlag >= 0 && args[dirFlag + 1]
  ? path.resolve(args[dirFlag + 1])
  : path.join(root, 'reports');

if (!fs.existsSync(reportsDir)) {
  console.error(`FAIL reports directory not found: ${reportsDir}`);
  process.exit(1);
}

// 활성 스킬 목록(미등록 스킬명 탐지 기준). "Browser" 5회 기록 사고(P-03)의 재발 감시.
const knownSkills = new Set(
  fs.readdirSync(path.join(root, 'skills'), { withFileTypes: true })
    .filter(e => e.isDirectory() && fs.existsSync(path.join(root, 'skills', e.name, 'SKILL.md')))
    .map(e => e.name)
);

const reportNamePattern = /^\d{4}-\d{2}-\d{2}.*_report\.md$/;
function collectReports(dir, files = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === 'archive' && !includeArchive) continue;
      collectReports(full, files);
    } else if (reportNamePattern.test(entry.name)) {
      files.push(full);
    }
  }
  return files;
}

function headerValue(text, label) {
  const m = text.match(new RegExp(`^>\\s*${label}\\s*:\\s*(.+?)\\s*$`, 'm'));
  return m ? m[1].trim() : null;
}
function parseSkillNames(value) {
  if (!value) return [];
  // 코드 span이 있으면 그것만, 없으면 쉼표 분해 후 괄호 주석 제거
  const spans = [...value.matchAll(/`([^`]+)`/g)].map(m => m[1].trim());
  const items = spans.length > 0
    ? spans
    : value.split(',').map(s => s.replace(/\(.*?\)/g, '').trim()).filter(Boolean);
  return items
    .map(s => s.replace(/^skills\//, '').replace(/\/SKILL\.md$/, ''))
    .filter(s => s && !/^해당\s*없음/.test(s));
}
function unresolvedItems(text) {
  const m = text.match(/^##[^\n]*미해결[^\n]*$([\s\S]*?)(?=^##\s|\s*$(?![\s\S]))/m);
  if (!m) return [];
  return m[1].split(/\r?\n/)
    .map(l => l.trim())
    .filter(l => l.startsWith('- '))
    .map(l => l.slice(2).replace(/\s+/g, ' ').replace(/[.。]\s*$/, '').trim())
    .filter(l => l && l !== '없음' && !/^\.\.\./.test(l));
}

const files = collectReports(reportsDir);
if (files.length === 0) {
  console.log(`harness-stats: Report 파일이 없습니다 (${reportsDir}). 파일명 규칙: YYYY-MM-DD_{작업명}_report.md`);
  process.exit(0);
}

const scopeCount = {};
const skillCount = {};
const gateValueCount = {};
const unknownSkillHits = [];   // { file, name }
const riskGateMismatch = [];   // 위험도≠일반인데 Gate "해당 없음" (P-09)
const gitMissing = [];         // 브랜치/커밋 칸 누락 또는 L/XL 미커밋 (P-01)
const planningExpected = [];   // L/XL Report
let planningFired = 0;
const unresolvedFreq = new Map(); // 정규화 문장 → [파일들]

for (const file of files) {
  const rel = path.relative(reportsDir, file);
  const text = fs.readFileSync(file, 'utf8');

  const scope = (headerValue(text, '작업 범위') || '미기재').split(/[\s/]+/)[0];
  scopeCount[scope] = (scopeCount[scope] || 0) + 1;

  const skills = parseSkillNames(headerValue(text, '적용 스킬'));
  for (const s of skills) {
    skillCount[s] = (skillCount[s] || 0) + 1;
    if (!knownSkills.has(s)) unknownSkillHits.push({ file: rel, name: s });
  }

  const gate = headerValue(text, '적용 Gate') || '미기재';
  gateValueCount[gate] = (gateValueCount[gate] || 0) + 1;
  const risk = headerValue(text, '위험도') || '미기재';
  if (!/^일반/.test(risk) && risk !== '미기재' && /해당\s*없음/.test(gate)) {
    riskGateMismatch.push({ file: rel, risk });
  }

  const branch = headerValue(text, '작업 브랜치');
  const commit = headerValue(text, '커밋/PR');
  if (!branch || !commit) {
    gitMissing.push({ file: rel, why: 'Git 기록 칸 자체가 없음(구 템플릿)' });
  } else if ((scope === 'L' || scope === 'XL') && /미커밋/.test(commit)) {
    gitMissing.push({ file: rel, why: `L/XL인데 커밋/PR이 "미커밋"` });
  }

  if (scope === 'L' || scope === 'XL') {
    planningExpected.push(rel);
    if (skills.includes('planning')) planningFired++;
  }

  for (const item of unresolvedItems(text)) {
    if (!unresolvedFreq.has(item)) unresolvedFreq.set(item, []);
    unresolvedFreq.get(item).push(rel);
  }
}

const sortDesc = obj => Object.entries(obj).sort((a, b) => b[1] - a[1]);

console.log(`# 하네스 성적표 (${path.relative(process.cwd(), reportsDir) || reportsDir})`);
console.log(`\nReport ${files.length}건${includeArchive ? ' (archive 포함)' : ''}`);
console.log(`규모 분포: ${sortDesc(scopeCount).map(([k, v]) => `${k} ${v}`).join(', ')}`);

console.log('\n## 스킬 발동 빈도');
if (Object.keys(skillCount).length === 0) console.log('- (기록 없음)');
for (const [name, n] of sortDesc(skillCount)) {
  console.log(`- ${name}: ${n}회${knownSkills.has(name) ? '' : '  ⚠ 미등록 스킬명'}`);
}
const neverFired = [...knownSkills].filter(s => !skillCount[s]).sort();
if (neverFired.length) console.log(`- 0회 스킬(${neverFired.length}개): ${neverFired.join(', ')}`);

console.log('\n## 적용 Gate 값 분포');
for (const [g, n] of sortDesc(gateValueCount)) console.log(`- ${g}: ${n}회`);

console.log('\n## 자동 점검 (⚠ = stocktake·환류에서 사람이 판단할 후보)');
console.log(`- 미등록 스킬명 기록: ${unknownSkillHits.length}건` +
  (unknownSkillHits.length ? ` ⚠  ${unknownSkillHits.map(h => `${h.name}(${h.file})`).join(', ')}` : ''));
console.log(`- 위험도≠일반인데 Gate "해당 없음": ${riskGateMismatch.length}건` +
  (riskGateMismatch.length ? ` ⚠  ${riskGateMismatch.map(h => `${h.file}[${h.risk}]`).join(', ')}` : ''));
console.log(`- Git 기록 문제: ${gitMissing.length}건` +
  (gitMissing.length ? ` ⚠  ${gitMissing.map(h => `${h.file}(${h.why})`).join('; ')}` : ''));
console.log(`- L/XL에서 planning 발동: ${planningExpected.length}건 중 ${planningFired}건` +
  (planningExpected.length > planningFired ? ' ⚠' : ''));

const repeated = [...unresolvedFreq.entries()].filter(([, fs2]) => fs2.length >= 3);
console.log(`- 3회 이상 반복된 미해결 항목(프로젝트 상수 후보, 05.WORKING_CONTEXT.md §1-1): ${repeated.length}건`);
for (const [item, where] of repeated) console.log(`  ⚠ [${where.length}회] ${item}`);

console.log('\n(이 출력은 통계이며 판정이 아니다. 반복 항목의 처리 기준은 06.REPORT_TEMPLATE.md §5-2, 스킬 존폐 판단은 skills/skill-stocktake/SKILL.md를 따른다.)');
