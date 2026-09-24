#!/usr/bin/env node
// validate-report-consistency: reports/_LATEST.md, 05.WORKING_CONTEXT.md, 02.SKILL_INDEX.md 사이의
// "현재 기준"이 서로 어긋나지 않는지, skills/ 실제 폴더와 02.SKILL_INDEX.md의 스킬 "이름 집합"이
// 일치하는지(개수만이 아니라), reports/archive/HISTORY_DIGEST.md가 archive 폴더 내용을
// 빠짐없이 반영하는지(archive 폴더가 있는데 digest 자체가 없는 경우도 FAIL) 검사한다.
// skills/report-consistency/SKILL.md의 자동 재확인 단계로 사용한다.
import fs from 'node:fs';
import path from 'node:path';

function isHarnessRoot(dir) {
  return fs.existsSync(path.join(dir, '00.HARNESS_RULES.md')) &&
    fs.existsSync(path.join(dir, 'skills')) &&
    fs.existsSync(path.join(dir, 'reports'));
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
let failed = false;
const warnings = [];

// 1. reports/_LATEST.md가 가리키는 Report 경로 추출
const latestPath = path.join(root, 'reports', '_LATEST.md');
if (!fs.existsSync(latestPath)) {
  console.error('FAIL reports/_LATEST.md not found.');
  process.exit(1);
}
const latestText = fs.readFileSync(latestPath, 'utf8');
// 2행 구조(ADR-041): "하네스 유지보수 최신" 행이 이 저장소의 검증 대상 포인터다.
// 구 단일 포인터 형식("최신 판단 기준 | `경로`")도 하위 호환으로 인식한다.
const pointerMatch = latestText.match(/하네스 유지보수 최신\s*\|\s*`([^`]+)`/) ||
  latestText.match(/최신 판단 기준\s*\|\s*`([^`]+)`/);
if (!pointerMatch) {
  console.error('FAIL cannot locate "하네스 유지보수 최신" (or legacy "최신 판단 기준") pointer row in reports/_LATEST.md.');
  process.exit(1);
}
const latestReportRel = pointerMatch[1];
const latestReportAbs = path.join(root, latestReportRel);

// 2. 그 파일이 실제 존재하는지, top-level에 있는지 확인
if (!fs.existsSync(latestReportAbs)) {
  console.error(`FAIL reports/_LATEST.md points to a non-existent file: ${latestReportRel}`);
  failed = true;
} else if (latestReportRel.includes('archive/')) {
  console.error(`FAIL reports/_LATEST.md points into archive/, which should hold superseded Reports only: ${latestReportRel}`);
  failed = true;
}

// 3. 05.WORKING_CONTEXT.md의 "현재 기준은 ~이다" 같은 현재형 고정 지목 문장 검사
const wcPath = path.join(root, '05.WORKING_CONTEXT.md');
const wcText = fs.readFileSync(wcPath, 'utf8');
const stalePointerPattern = /현재\s*기준은\s*`(reports\/[^`]+)`\s*이다/g;
let m;
while ((m = stalePointerPattern.exec(wcText)) !== null) {
  const referenced = m[1];
  if (referenced !== latestReportRel) {
    warnings.push(`05.WORKING_CONTEXT.md still names "${referenced}" as 현재 기준, but reports/_LATEST.md points to "${latestReportRel}".`);
  }
}

// 4. 활성 스킬 수 + 이름 집합 일치 확인 (skills/ 실제 폴더 vs 02.SKILL_INDEX.md Active 행 vs 05.WORKING_CONTEXT.md 표기)
const skillsDir = path.join(root, 'skills');
const actualSkillNames = new Set(
  fs.readdirSync(skillsDir, { withFileTypes: true })
    .filter(e => e.isDirectory() && fs.existsSync(path.join(skillsDir, e.name, 'SKILL.md')))
    .map(e => e.name)
);
const skillIndexPath = path.join(root, '02.SKILL_INDEX.md');
const skillIndexText = fs.readFileSync(skillIndexPath, 'utf8');
// "| N | `skill-name` | 구분 | Active | ..." 형태의 행에서 스킬명과 상태를 함께 추출
const indexRowPattern = /\|\s*`([a-z0-9-]+)`\s*\|[^|]*\|\s*Active\s*\|/g;
const indexedActiveNames = new Set();
let rowMatch;
while ((rowMatch = indexRowPattern.exec(skillIndexText)) !== null) {
  indexedActiveNames.add(rowMatch[1]);
}
const activeCount = indexedActiveNames.size;

const missingFromIndex = [...actualSkillNames].filter(n => !indexedActiveNames.has(n));
const missingFromDisk = [...indexedActiveNames].filter(n => !actualSkillNames.has(n));
if (missingFromIndex.length > 0 || missingFromDisk.length > 0) {
  console.error('FAIL skill name set mismatch between skills/ directory and 02.SKILL_INDEX.md Active rows:');
  if (missingFromIndex.length > 0) console.error(`  - on disk but not indexed as Active: ${missingFromIndex.join(', ')}`);
  if (missingFromDisk.length > 0) console.error(`  - indexed as Active but no skills/ folder: ${missingFromDisk.join(', ')}`);
  failed = true;
}

const wcSkillMatch = wcText.match(/활성 스킬\s*\|\s*(\d+)개/);
if (wcSkillMatch) {
  const wcCount = parseInt(wcSkillMatch[1], 10);
  if (wcCount !== activeCount) {
    console.error(`FAIL active skill count mismatch: 02.SKILL_INDEX.md has ${activeCount} Active rows, 05.WORKING_CONTEXT.md states ${wcCount}.`);
    failed = true;
  }
} else {
  warnings.push('Could not find "활성 스킬 | N개" row in 05.WORKING_CONTEXT.md to compare.');
}

// 5. top-level reports/에 superseded 표시 없는 과거 Report가 있는지 확인(최신 Report 제외)
const reportsDir = path.join(root, 'reports');
const topLevelReports = fs.readdirSync(reportsDir, { withFileTypes: true })
  .filter(e => e.isFile() && e.name.endsWith('.md') && e.name !== 'README.md' && e.name !== '_LATEST.md')
  .map(e => e.name);
for (const name of topLevelReports) {
  const rel = `reports/${name}`;
  if (rel === latestReportRel) continue;
  const text = fs.readFileSync(path.join(reportsDir, name), 'utf8');
  if (!text.includes('Superseded note')) {
    warnings.push(`reports/${name} is not the latest Report but has no "Superseded note" — consider adding one and moving it to reports/archive/.`);
  }
}

// 6. reports/archive/의 실제 Report 수와 HISTORY_DIGEST.md 색인 수 일치 확인 (event 기반 재작성 — 외부 검수 M-06/X-06/G-06)
//
// 이전 버전들의 결함(전부 실제 재현 테스트로 확인됨):
//   - 연도가 "2026-"으로 하드코딩되어 2027년 이후 고아 행을 전혀 못 잡음(1차 결함)
//   - 명시적 목록(PURGED_FILES) 방식도 "digest 행 + 목록 + 누계 count"를 한꺼번에 일관되게
//     조작하면(실제로 파일을 지우고 목록에 추가하고 count를 30→31로 바꾸는 식) 새로운 승인
//     증거 없이 조용히 PASS함(2차 결함, 자기승인 우회를 실제로 재현해 확인)
//   - 그 방식은 반대로 "정상적인 두 번째 삭제"도 지원하지 못함 — 전체 count 하나만 있어서
//     새 이벤트를 추가하면 옛 count와 안 맞아 FAIL함(2차 결함의 반대쪽)
// 지금은 삭제를 "이벤트"로 나눈다. 각 이벤트는 독립된 블록(<!-- PURGE_EVENT ... --> ~
// <!-- PURGE_EVENT_END ... -->)이며 event_id/date/approval/count를 자기 헤더에 갖는다.
// 이벤트는 추가만 하고 기존 이벤트는 절대 고치지 않는다(불변). 각 이벤트를 독립적으로 검증하고,
// 전체 이벤트의 파일을 합친 것으로 최종 고아 검사를 한다.
const archiveDir = path.join(reportsDir, 'archive');
const digestPath = path.join(archiveDir, 'HISTORY_DIGEST.md');
const adrPath = path.join(root, '10.ADR.md');
if (fs.existsSync(archiveDir)) {
  const archiveFiles = fs.readdirSync(archiveDir, { withFileTypes: true })
    .filter(e => e.isFile() && e.name.endsWith('.md') && e.name !== 'HISTORY_DIGEST.md')
    .map(e => e.name);
  const archiveFileSet = new Set(archiveFiles);

  if (archiveFiles.length > 0 && !fs.existsSync(digestPath)) {
    console.error(`FAIL reports/archive/ has ${archiveFiles.length} report(s) but HISTORY_DIGEST.md does not exist.`);
    failed = true;
  } else if (fs.existsSync(digestPath)) {
    const digestText = fs.readFileSync(digestPath, 'utf8');

    // digestRows: 표 행("| 날짜 | `파일명` | 설명 |")에서만 파일명을 뽑는다. 연도는 4자리 전체 일반화.
    const digestRows = new Set(
      [...digestText.matchAll(/^\|\s*\d{4}-\d{2}-\d{2}\s*\|\s*`([^`]+\.md)`/gm)].map(m => m[1])
    );

    // 실제 존재하는 ADR 번호 집합(approval 근거 검증용)
    const adrNumbers = fs.existsSync(adrPath)
      ? new Set([...fs.readFileSync(adrPath, 'utf8').matchAll(/^## ADR-(\d+)\./gm)].map(m => `ADR-${m[1]}`))
      : new Set();

    // PURGE_EVENT 블록 전부를 파싱한다(0개 이상 있을 수 있다). 각 START는 반드시 매칭되는
    // 같은 event_id의 END를 가져야 하고, event_id는 전체에서 고유해야 한다.
    const startPattern = /^<!-- PURGE_EVENT event_id=(\S+) date=(\d{4}-\d{2}-\d{2}) approval=(\S+) count=(\d+) -->$/gm;
    const starts = [...digestText.matchAll(startPattern)];
    const endPattern = /^<!-- PURGE_EVENT_END event_id=(\S+) -->$/gm;
    const ends = [...digestText.matchAll(endPattern)].map(m => m[1]);

    const eventIdCounts = new Map();
    for (const m of starts) eventIdCounts.set(m[1], (eventIdCounts.get(m[1]) || 0) + 1);
    const duplicateEventIds = [...eventIdCounts].filter(([, c]) => c > 1).map(([id]) => id);
    if (duplicateEventIds.length > 0) {
      console.error(`FAIL Duplicate PURGE_EVENT event_id(s): ${duplicateEventIds.join(', ')}`);
      failed = true;
    }

    const allPurgedFiles = new Set();
    const filenamePattern = /^\d{4}-\d{2}-\d{2}[a-zA-Z0-9_.-]*\.md$/;

    for (const startMatch of starts) {
      const [fullMatch, eventId, eventDate, approval, countStr] = startMatch;
      if (!ends.includes(eventId)) {
        console.error(`FAIL PURGE_EVENT ${eventId} has a START marker but no matching END marker.`);
        failed = true;
        continue;
      }
      const blockPattern = new RegExp(
        `<!-- PURGE_EVENT event_id=${eventId} date=\\S+ approval=\\S+ count=\\d+ -->\\s*` +
        '```text\\s*([\\s\\S]*?)```\\s*' +
        `<!-- PURGE_EVENT_END event_id=${eventId} -->`
      );
      const blockMatch = digestText.match(blockPattern);
      if (!blockMatch) {
        console.error(`FAIL PURGE_EVENT ${eventId} block could not be parsed (check marker/code-block format).`);
        failed = true;
        continue;
      }
      const fileList = blockMatch[1].split('\n').map(s => s.trim()).filter(Boolean);
      const statedCount = parseInt(countStr, 10);

      if (fileList.length !== statedCount) {
        console.error(`FAIL PURGE_EVENT ${eventId} declares count=${statedCount} but lists ${fileList.length} file(s).`);
        failed = true;
      }
      const malformed = fileList.filter(name => !filenamePattern.test(name));
      if (malformed.length > 0) {
        console.error(`FAIL PURGE_EVENT ${eventId} contains malformed filename(s): ${malformed.join(', ')}`);
        failed = true;
      }
      if (adrNumbers.size > 0 && !adrNumbers.has(approval)) {
        console.error(`FAIL PURGE_EVENT ${eventId} cites approval=${approval} but no such ADR exists in 10.ADR.md.`);
        failed = true;
      }
      const notInDigest = fileList.filter(name => !digestRows.has(name));
      if (notInDigest.length > 0) {
        console.error(`FAIL PURGE_EVENT ${eventId} lists ${notInDigest.length} file(s) with no matching HISTORY_DIGEST.md table row: ${notInDigest.join(', ')}`);
        failed = true;
      }
      const stillPresent = fileList.filter(name => archiveFileSet.has(name));
      if (stillPresent.length > 0) {
        console.error(`FAIL PURGE_EVENT ${eventId} lists ${stillPresent.length} file(s) that still physically exist in reports/archive/: ${stillPresent.join(', ')}`);
        failed = true;
      }
      for (const name of fileList) allPurgedFiles.add(name);
    }
    // END만 있고 START가 없는 경우도 검사
    for (const endId of ends) {
      if (!starts.some(m => m[1] === endId)) {
        console.error(`FAIL PURGE_EVENT_END ${endId} has no matching START marker.`);
        failed = true;
      }
    }

    // digestRows − allPurgedFiles − archive = ∅: 표에는 있는데 archive에도 없고 어떤 삭제
    // 이벤트에도 속하지 않는 파일 — 이게 진짜 고아 행이다. FAIL이다(D-021 fail-open 금지 원칙과 통일).
    const archiveFilesMissingFromDigest = archiveFiles.filter(name => !digestRows.has(name));
    if (archiveFilesMissingFromDigest.length > 0) {
      console.error(`FAIL reports/archive/HISTORY_DIGEST.md is missing ${archiveFilesMissingFromDigest.length} archived report(s):`);
      for (const name of archiveFilesMissingFromDigest) console.error(`  - ${name}`);
      failed = true;
    }
    const unexplainedOrphans = [...digestRows].filter(name => !archiveFileSet.has(name) && !allPurgedFiles.has(name));
    if (unexplainedOrphans.length > 0) {
      console.error(`FAIL HISTORY_DIGEST.md references ${unexplainedOrphans.length} file(s) not present in reports/archive/ and not covered by any PURGE_EVENT: ${unexplainedOrphans.join(', ')}`);
      failed = true;
    }
  }
}

if (warnings.length > 0) {
  console.error(`WARN ${warnings.length} consistency issue(s) found:`);
  for (const w of warnings) console.error(`  - ${w}`);
}

if (failed) process.exit(1);
if (warnings.length > 0) {
  console.log('WARN validate-report-consistency: no FAIL-level mismatch, but see warnings above.');
  process.exit(0);
}
console.log('PASS validate-report-consistency: _LATEST.md target exists, skill name sets and counts match between skills/, 02.SKILL_INDEX.md, 05.WORKING_CONTEXT.md, and reports/archive/HISTORY_DIGEST.md covers all archived reports with no UNEXPLAINED orphan rows (rows covered by a valid PURGE_EVENT are expected to have no physical file and are not orphans). Note: this script alone does not require reports/archive/ to exist — if that directory is absent entirely, this section is skipped (other scripts like validate-harness still check required top-level structure). This does not verify prose accuracy inside Working Context sections, digest entry date ordering, duplicate digest rows, or whether each digest summary sentence accurately describes its report (외부 검수 m-05/m-11, known limitation).');
