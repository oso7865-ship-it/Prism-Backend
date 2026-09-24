#!/usr/bin/env node
// validate-references: 마크다운 문서 안의 백틱 경로 참조(*.md, *.mjs, skills/, gates/,
// checklists/, reports/ 등)가 실제 파일 구조와 일치하는지 검사한다.
//
// 다음은 의도적으로 검사 대상에서 제외한다:
// - `_PENDING_IMPORT_LIST.md`, `_SOURCE_MAPPING.md`, `10.ADR.md` 전체: 외부 원본 파일명이나
//   채택하지 않은 반입 후보, 반입 전 이름을 그대로 인용하는 근거 문서라 실제 파일이 없는 게 정상이다.
// - 디렉터리 구분자("/")가 없는 단독 파일명은, 우리 문서 번호 규칙(00~10로 시작)이나
//   알려진 루트 파일(_SOURCE_MAPPING.md 등)에 해당할 때만 검사한다. 그 외 단독 파일명은
//   외부 인용(예: CLAUDE.md 초안, 외부 감사 리포트)일 가능성이 높아 대상에서 뺀다.
//
// `reports/` 안의 문서도 검사 대상에 포함한다(과거에는 통째로 제외했으나, archive 이동으로
// 깨진 내부 경로를 실제로 못 잡는 문제가 외부 검수 M-04로 지적됨). 다만 `reports/YYYY-...` 형태
// 참조가 직접 경로에 없으면 `reports/archive/YYYY-...`로도 시도한다 — 오래된 Report가 나중에
// archive로 이동해도 그 시점에 쓴 문장을 소급 수정하지 않기로 했기 때문이다(06.REPORT_TEMPLATE.md §8).
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

const root = resolveRoot();
const EXCLUDED_FILES = new Set(['_PENDING_IMPORT_LIST.md', '10.ADR.md', '_SOURCE_MAPPING.md']);
const NUMBERED_DOC = /^(00|01|02|03|04|05|06|07|08|09|10)\.[A-Z_]+\.md$/;
const KNOWN_ROOT_FILES = new Set(['_SOURCE_MAPPING.md', '_PENDING_IMPORT_LIST.md']);
// 과거 리포트 안에서 실제 경로가 아니라 "가상의 파일명"(도입하지 않기로 한 초안)이나
// 압축 표기(스크립트 여러 개를 슬래시로 나열한 표 셀)로 쓰인 것들. 새로 추가하기 전에
// 정말 예외가 맞는지 먼저 확인한다.
const ALLOWED_MISSING = new Set([
  '05.WORKING_RULES.md', // Working Context 분리 시 쓰기로 했던 가상 파일명(도입 안 함, _PENDING_IMPORT_LIST.md 참고)
  '00.EXECUTOR_BOOT.md', // 실행자 분기 초안 파일명(도입 안 함, 10.ADR.md ADR-013/017 참고)
  'validate-harness/docs/skills/package/no-personal-paths/report-consistency/references.mjs', // 스크립트 7개를 슬래시로 압축 표기한 셀(실제 경로 아님)
]);

function walk(dir, files = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === 'node_modules' || entry.name === '.git') continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(full, files);
    } else if (entry.name.endsWith('.md')) {
      files.push(full);
    }
  }
  return files;
}

const refPattern = /`([^`]+\.(?:md|mjs))`/g;

function shouldCheck(ref) {
  if (ref.includes('{') || ref.includes('*') || ref.includes(' ')) return false;
  if (ALLOWED_MISSING.has(ref)) return false;
  if (ref.includes('/')) return true;
  return NUMBERED_DOC.test(ref) || KNOWN_ROOT_FILES.has(ref);
}

function existsWithFallback(root, ref) {
  const direct = path.join(root, ref);
  if (fs.existsSync(direct)) return true;
  if (!ref.includes('/')) {
    if (fs.existsSync(path.join(root, 'reports', ref))) return true;
  }
  // reports/YYYY-..._report.md 형태가 archive로 이동했을 수 있으니 archive/ 경로도 시도
  if (ref.startsWith('reports/') && !ref.startsWith('reports/archive/')) {
    const archived = ref.replace('reports/', 'reports/archive/');
    if (fs.existsSync(path.join(root, archived))) return true;
  }
  return false;
}

let failed = false;
const missing = [];
const files = walk(root);

for (const file of files) {
  const relFile = path.relative(root, file);
  const baseName = path.basename(file);
  if (EXCLUDED_FILES.has(baseName)) continue;

  const text = fs.readFileSync(file, 'utf8');
  let m;
  refPattern.lastIndex = 0;
  while ((m = refPattern.exec(text)) !== null) {
    const ref = m[1];
    if (!shouldCheck(ref)) continue;
    if (!existsWithFallback(root, ref)) {
      missing.push({ file: relFile, ref });
    }
  }
}

if (missing.length > 0) {
  console.error(`FAIL ${missing.length} internal reference(s) point to files that do not exist:`);
  for (const item of missing.slice(0, 30)) {
    console.error(`  - ${item.file} -> ${item.ref}`);
  }
  if (missing.length > 30) console.error(`  ... and ${missing.length - 30} more`);
  failed = true;
}

// 섹션 번호 참조 검사: `파일명.md §N` 형태가 실제로 그 파일에 "## N." 또는 "### N-M."
// 헤딩으로 존재하는지 확인한다(외부 검수 M-12). _PENDING_IMPORT_LIST.md/_SOURCE_MAPPING.md/10.ADR.md는
// 여전히 제외한다 — 이 세 문서는 채택 안 한 외부 후보나 과거 결정의 섹션 번호도 그대로 인용하는
// 근거 문서라, 지금 섹션 구조와 안 맞는 인용이 정상적으로 섞여 있다(알려진 한계, P-10 참고).
// reports/archive/(역사 기록)만 제외하고, reports/ 최상위(현재 Report)는 검사 대상에 포함한다
// (과거엔 reports/ 전체를 건너뛰어 현재 Report의 섹션 인용 오류도 못 잡았다, 외부 검수 M-07).
const sectionRefPattern = /`([0-9]{2}\.[A-Z_]+\.md|(?:gates|checklists|skills)\/[a-zA-Z0-9_/-]+\.md) §([0-9]+(?:-[0-9]+)?)`/g;
const missingSections = [];
for (const file of files) {
  const relFile = path.relative(root, file);
  const baseName = path.basename(file);
  if (EXCLUDED_FILES.has(baseName)) continue;
  if (relFile.startsWith('reports' + path.sep + 'archive' + path.sep)) continue;

  const text = fs.readFileSync(file, 'utf8');
  let m;
  sectionRefPattern.lastIndex = 0;
  while ((m = sectionRefPattern.exec(text)) !== null) {
    const [, targetFile, sectionNum] = m;
    const targetPath = path.join(root, targetFile);
    if (!fs.existsSync(targetPath)) continue; // 파일 자체 존재 여부는 위에서 이미 검사함
    const targetText = fs.readFileSync(targetPath, 'utf8');
    const headingPattern = new RegExp(`^##+\\s*${sectionNum}[.\\s]`, 'm');
    if (!headingPattern.test(targetText)) {
      missingSections.push({ file: relFile, ref: `${targetFile} §${sectionNum}` });
    }
  }
}
if (missingSections.length > 0) {
  console.error(`FAIL ${missingSections.length} section reference(s) point to a section heading that does not exist:`);
  for (const item of missingSections.slice(0, 30)) {
    console.error(`  - ${item.file} -> ${item.ref}`);
  }
  if (missingSections.length > 30) console.error(`  ... and ${missingSections.length - 30} more`);
  failed = true;
}

if (failed) process.exit(1);
console.log(`PASS validate-references: checked ${files.length} markdown files (excluding _PENDING_IMPORT_LIST.md, _SOURCE_MAPPING.md, 10.ADR.md; reports/ included with archive/ fallback), all internal path references AND section references (\`파일.md §N\`) resolve to real files/headings. Known limitation: the 3 excluded files are not checked at all, including their own internal current-section references — see 08.QUALITY_GATE.md §10-1.`);
