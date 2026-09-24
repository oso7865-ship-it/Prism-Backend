import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { inspectRecords } from '../validate-work-records.mjs';

const cli = fileURLToPath(new URL('../validate-work-records.mjs', import.meta.url));
const report = '# Work report\n> 작업 브랜치: feature/example\n> 커밋/PR: 미커밋\n> 작업 범위: M\n> 적용 스킬: `planning`\n> 적용 Gate: Document Gate\n> 위험도: 일반\n';
function fixture(t) {
  const temp = fs.realpathSync(os.tmpdir());
  const root = fs.mkdtempSync(path.join(temp, 'harness-records-'));
  t.after(() => {
    // Only remove this test's freshly created directory inside the resolved temp root.
    const resolved = fs.realpathSync(root);
    assert.equal(path.dirname(resolved), temp);
    assert.ok(path.basename(resolved).startsWith('harness-records-'));
    fs.rmSync(resolved, { recursive: true, force: true });
  });
  const put = (name, text = '') => {
    const file = path.join(root, name);
    fs.mkdirSync(path.dirname(file), { recursive: true });
    fs.writeFileSync(file, text);
  };
  put('GENERAL_HARNESS/skills/planning/SKILL.md', '# Planning');
  const inspect = (options = {}) => inspectRecords({ projectRoot: root, ...options });
  const valid = () => {
    put('reports/2026-09-19_result.md', report);
    put('reports/_LATEST.md', '`reports/2026-09-19_result.md`');
  };
  return { root, put, inspect, valid };
}
const has = (result, code) => result.findings.some(f => f.code === code);
const stateRecord = '# Current work\n> 상태 기록 버전: 1\n> 상태 확인 시각: 2026-09-19T16:00:00+09:00\n'
  + ['구현', '로컬 검증', '병합', '배포', '실제 연동'].map(stage => `> ${stage} 상태: 미수행\n`).join('');
const policy = branch => JSON.stringify({ schemaVersion: 1, git: { remote: 'origin', integrationBranch: branch } });

test('valid report and root-relative code pointer pass', t => {
  const f = fixture(t); f.valid();
  const r = f.inspect();
  assert.equal(r.status, 'PASS'); assert.equal(r.exitCode, 0); assert.equal(r.checkedCount, 1);
  assert.deepEqual(r.checkedFiles, ['reports/2026-09-19_result.md']);
  assert.equal(r.targets[0].state, 'missing'); // optional plans are explicitly visible
});
test('missing default targets are NOT_CHECKED, never PASS', t => {
  const r = fixture(t).inspect();
  assert.equal(r.status, 'NOT_CHECKED'); assert.equal(r.exitCode, 2);
});
test('README, pointer and archived examples do not count as records', t => {
  const f = fixture(t);
  f.put('reports/README.md', '# Index'); f.put('reports/archive/old.md', report);
  const r = f.inspect(); assert.equal(r.status, 'NOT_CHECKED'); assert.equal(r.checkedCount, 0);
});
test('explicit missing directory fails even when other records exist', t => {
  const f = fixture(t); f.valid(); const r = f.inspect({ plans: 'absent' });
  assert.equal(r.status, 'FAIL'); assert.ok(has(r, 'TARGET_MISSING'));
});
test('explicit empty directory fails', t => {
  const f = fixture(t); f.put('plans/README.md', '# Index');
  assert.ok(has(f.inspect({ plans: 'plans' }), 'TARGET_EMPTY'));
});
test('a file used as a directory fails', t => {
  const f = fixture(t); f.put('plans', 'file');
  assert.ok(has(f.inspect({ plans: 'plans' }), 'TARGET_UNREADABLE'));
});
test('empty record is a confirmed error', t => {
  const f = fixture(t); f.put('docs/work-plans/empty.md');
  assert.ok(has(f.inspect(), 'RECORD_EMPTY'));
});
test('unknown skill is FAIL in both plain and code-span notation', t => {
  const f = fixture(t);
  for (const name of ['missing-skill', '`missing-skill`', 'Browser']) {
    f.put('docs/work-plans/task.md', `# Plan\n- 적용 스킬: ${name}`);
    const r = f.inspect(); assert.equal(r.status, 'FAIL'); assert.ok(has(r, 'SKILL_UNKNOWN'));
  }
});
test('canonical plain lists and table metadata are parsed', t => {
  const f = fixture(t); f.put('docs/work-plans/task.md', '# Plan\n| 적용 스킬 | planning |\n| 위험도 | DB |\n| 적용 Gate | DB Gate |');
  assert.equal(f.inspect().status, 'PASS');
});
test('existing applied-procedure alias and trailing punctuation remain compatible', t => {
  const f = fixture(t); f.valid();
  f.put('reports/2026-09-19_result.md', report.replace('적용 스킬: `planning`', '적용 절차: Harness `planning`.'));
  assert.equal(f.inspect().status, 'PASS');
});
test('examples inside backtick and tilde fences do not create findings', t => {
  const f = fixture(t); f.valid();
  f.put('reports/2026-09-19_result.md', report + '\n```md\n> 적용 스킬: invented\n```\n~~~\n> 위험도: DB\n~~~');
  assert.equal(f.inspect().status, 'PASS');
});
test('missing and empty required report headers fail', t => {
  const f = fixture(t); f.valid();
  f.put('reports/2026-09-19_result.md', report.replace('> 커밋/PR: 미커밋', '> 커밋/PR:'));
  assert.ok(has(f.inspect(), 'HEADER_MISSING'));
});
test('legacy skips header enforcement but never skips unknown skills', t => {
  const f = fixture(t); f.valid();
  f.put('reports/2026-09-19_result.md', '# Old\n> 형식 상태: legacy\n> 적용 스킬: invented');
  const r = f.inspect(); assert.ok(!has(r, 'HEADER_MISSING')); assert.ok(has(r, 'SKILL_UNKNOWN'));
});
test('DB and generic external integration produce review warnings', t => {
  const f = fixture(t);
  f.put('docs/work-plans/task.md', '# Plan\n> 위험도: DB 및 외부 서비스 연동\n> 적용 Gate: Document Gate');
  const r = f.inspect(); assert.equal(r.status, 'WARN'); assert.equal(r.exitCode, 0);
  assert.equal(r.findings.filter(x => x.code === 'GATE_REVIEW').length, 2);
  const strict = f.inspect({ strict: true }); assert.equal(strict.status, 'WARN'); assert.equal(strict.exitCode, 1);
});
test('Gate mentioned only in body does not satisfy declared Gate field', t => {
  const f = fixture(t); f.put('docs/work-plans/task.md', '# Plan\n> 위험도: 결제\nPayment Gate가 필요할 수 있다.');
  assert.ok(has(f.inspect(), 'GATE_REVIEW'));
});
test('canonical Gate paths satisfy the corresponding risk check', t => {
  const f = fixture(t); f.put('docs/work-plans/task.md', '# Plan\n> 위험도: DB 인증 환불\n> 적용 Gate: `gates/db-gate.md`, `gates/security-gate.md`, `gates/payment-gate.md`');
  assert.equal(f.inspect().status, 'PASS');
});
test('missing latest pointer is WARN, broken pointer is FAIL', t => {
  const f = fixture(t); f.put('reports/2026-09-19_result.md', report);
  assert.ok(has(f.inspect(), 'POINTER_MISSING'));
  f.put('reports/_LATEST.md', '[latest](gone.md)');
  const r = f.inspect(); assert.equal(r.status, 'FAIL'); assert.ok(has(r, 'POINTER_INVALID'));
});
test('encoded relative Markdown pointer with fragment is supported', t => {
  const f = fixture(t); f.put('reports/결과 보고.md', report);
  f.put('reports/_LATEST.md', '[latest](%EA%B2%B0%EA%B3%BC%20%EB%B3%B4%EA%B3%A0.md#result)');
  assert.equal(f.inspect().status, 'PASS');
});
test('two-history table ignores delegated project history', t => {
  const f = fixture(t); f.valid();
  f.put('reports/_LATEST.md', '| 하네스 유지보수 최신 | `reports/2026-09-19_result.md` | current |\n| 부착 프로젝트 최신 | 해당 프로젝트 폴더의 `reports/_LATEST.md`를 따른다 | delegated |');
  assert.equal(f.inspect().status, 'PASS');
});
test('nested harness report directory supports legacy reports/ code paths', t => {
  const f = fixture(t);
  f.put('GENERAL_HARNESS/reports/2026-09-19_result.md', report);
  f.put('GENERAL_HARNESS/reports/_LATEST.md', '| 하네스 유지보수 최신 | `reports/2026-09-19_result.md` | current |');
  assert.equal(f.inspect({ reports: 'GENERAL_HARNESS/reports' }).status, 'PASS');
});
test('later filename date warns; equal dates do not imply newer work', t => {
  const f = fixture(t); f.valid(); f.put('reports/2026-09-19_other.md', report);
  assert.equal(f.inspect().status, 'PASS');
  f.put('reports/2026-09-20_next.md', report); assert.ok(has(f.inspect(), 'POINTER_NEWER_RECORD'));
});
test('unrecognizable latest pointer cannot silently pass', t => {
  const f = fixture(t); f.valid(); f.put('reports/_LATEST.md', '# Latest\nNo target');
  assert.ok(has(f.inspect(), 'POINTER_FORMAT'));
});
test('pointer to itself or archive fails', t => {
  const f = fixture(t); f.valid();
  for (const target of ['_LATEST.md', 'archive/old.md']) {
    f.put('reports/archive/old.md', report); f.put('reports/_LATEST.md', `[latest](${target})`);
    assert.ok(has(f.inspect(), 'POINTER_INVALID'));
  }
});
test('target and pointer traversal outside project fail', t => {
  const f = fixture(t); f.valid();
  assert.ok(has(f.inspect({ plans: '../outside' }), 'TARGET_UNREADABLE'));
  f.put('reports/_LATEST.md', '[latest](../../outside.md)');
  assert.ok(has(f.inspect(), 'POINTER_INVALID'));
});
test('overlapping scopes count unique inspected files', t => {
  const f = fixture(t); f.valid(); const r = f.inspect({ plans: 'reports' });
  assert.equal(r.checkedCount, 1); assert.equal(r.status, 'PASS');
});
test('missing registry is FAIL, not NOT_CHECKED', t => {
  const f = fixture(t); f.put('other/README.md', '# Other project');
  const r = inspectRecords({ projectRoot: path.join(f.root, 'other') });
  assert.equal(r.status, 'FAIL'); assert.ok(has(r, 'INPUT_INVALID'));
});
test('empty registry is FAIL', t => {
  const f = fixture(t); fs.mkdirSync(path.join(f.root, 'other/GENERAL_HARNESS/skills'), { recursive: true });
  assert.equal(inspectRecords({ projectRoot: path.join(f.root, 'other') }).status, 'FAIL');
});
test('BOM and CRLF do not change metadata interpretation', t => {
  const f = fixture(t); f.valid(); f.put('reports/2026-09-19_result.md', '\uFEFF' + report.replaceAll('\n', '\r\n'));
  assert.equal(f.inspect().status, 'PASS');
});
test('existing report outside selected scope is WARN', t => {
  const f = fixture(t); f.valid(); f.put('other/report.md', report);
  f.put('reports/_LATEST.md', '[latest](../other/report.md)');
  assert.ok(has(f.inspect(), 'POINTER_OUTSIDE_SCOPE'));
});
test('directory symlink cannot hide uninspected records', t => {
  const f = fixture(t); f.valid(); f.put('other/task.md', '# Plan');
  fs.symlinkSync(path.join(f.root, 'other'), path.join(f.root, 'reports/linked'), process.platform === 'win32' ? 'junction' : 'dir');
  assert.ok(has(f.inspect(), 'TARGET_UNREADABLE'));
});
test('CLI emits parseable JSON, exit 2 for no records, and does not write input files', t => {
  const f = fixture(t);
  const before = fs.readdirSync(f.root, { recursive: true }).sort();
  const child = spawnSync(process.execPath, [cli, '--project-root', f.root, '--json'], { encoding: 'utf8' });
  assert.equal(child.status, 2); assert.equal(JSON.parse(child.stdout).status, 'NOT_CHECKED');
  assert.deepEqual(fs.readdirSync(f.root, { recursive: true }).sort(), before);
});
test('CLI invalid option and absent value fail as structured errors', t => {
  for (const args of [['--unknown'], ['--reports']]) {
    const child = spawnSync(process.execPath, [cli, ...args, '--json'], { encoding: 'utf8' });
    assert.equal(child.status, 1); assert.equal(JSON.parse(child.stdout).findings[0].code, 'CLI_USAGE');
  }
});
test('CLI supports running from GENERAL_HARNESS and strict WARN exit', t => {
  const f = fixture(t); f.put('docs/work-plans/task.md', '# Plan\n> 위험도: DB');
  const child = spawnSync(process.execPath, [cli, '--strict', '--json'], { cwd: path.join(f.root, 'GENERAL_HARNESS'), encoding: 'utf8' });
  assert.equal(child.status, 1); assert.equal(JSON.parse(child.stdout).status, 'WARN');
});

test('CI explicit scopes fail even when another scope has valid records', t => {
  const f = fixture(t); f.valid();
  const args = [cli, '--project-root', f.root, '--plans', 'docs/hardening', '--reports', 'reports', '--strict', '--json'];
  const missing = spawnSync(process.execPath, args, { encoding: 'utf8' });
  assert.equal(missing.status, 1); assert.equal(JSON.parse(missing.stdout).status, 'FAIL');
  fs.mkdirSync(path.join(f.root, 'docs/hardening'), { recursive: true });
  const empty = spawnSync(process.execPath, args, { encoding: 'utf8' });
  assert.equal(empty.status, 1); assert.equal(JSON.parse(empty.stdout).status, 'FAIL');
  f.put('docs/hardening/task.md', '# Plan');
  const valid = spawnSync(process.execPath, args, { encoding: 'utf8' });
  assert.equal(valid.status, 0); assert.equal(JSON.parse(valid.stdout).checkedCount, 2);
});

test('stage record permits honest unperformed work without inventing evidence', t => {
  const f = fixture(t); f.put('docs/work-plans/task.md', stateRecord);
  assert.equal(f.inspect().status, 'PASS'); assert.equal(f.inspect().gitPolicy, null);
});
test('completed stage requires meaningful evidence', t => {
  const f = fixture(t);
  for (const evidence of ['', 'TODO', '`미확인`', '{증거}']) {
    f.put('docs/work-plans/task.md', stateRecord.replace('구현 상태: 미수행', `구현 상태: 완료\n> 구현 근거: ${evidence}`));
    assert.ok(has(f.inspect(), 'STATE_EVIDENCE'));
  }
});
test('completed local validation requires target in addition to command evidence', t => {
  const f = fixture(t);
  const record = stateRecord.replace('로컬 검증 상태: 미수행', '로컬 검증 상태: 완료\n> 로컬 검증 근거: node --test, 33 tests PASS');
  f.put('docs/work-plans/task.md', record); assert.ok(has(f.inspect(), 'VALIDATION_TARGET'));
  f.put('docs/work-plans/task.md', record + '> 로컬 검증 대상: working-tree scripts changes at recorded time\n');
  assert.equal(f.inspect().status, 'PASS');
});
test('main and dev merge policies are explicit and never interchangeable', t => {
  const f = fixture(t);
  for (const branch of ['main', 'dev', 'release/next']) {
    f.put('harness.config.json', policy(branch));
    const record = stateRecord.replace('병합 상태: 미수행', `병합 상태: 완료\n> 병합 근거: PR 10 merged, base ${branch}, merge commit abc123, observed at recorded time\n> 병합 대상: origin/${branch}`);
    f.put('docs/work-plans/task.md', record); assert.equal(f.inspect().status, 'PASS');
    f.put('docs/work-plans/task.md', record.replace(`병합 대상: origin/${branch}`, '병합 대상: upstream/wrong'));
    assert.ok(has(f.inspect(), 'MERGE_TARGET'));
  }
});
test('missing Git policy cannot silently default merged work to main', t => {
  const f = fixture(t); f.put('docs/work-plans/task.md', stateRecord.replace('병합 상태: 미수행', '병합 상태: 완료\n> 병합 근거: PR 10 merged\n> 병합 대상: origin/main'));
  assert.ok(has(f.inspect(), 'MERGE_POLICY'));
});
test('merge completion does not require or promote deployment and live integration', t => {
  const f = fixture(t); f.put('harness.config.json', policy('dev'));
  f.put('docs/work-plans/task.md', stateRecord.replace('병합 상태: 미수행', '병합 상태: 완료\n> 병합 근거: PR 11 merged into dev, commit abc123\n> 병합 대상: origin/dev'));
  assert.equal(f.inspect().status, 'PASS');
});
test('failure and not-applicable both require explanations', t => {
  const f = fixture(t);
  for (const state of ['실패', '해당 없음']) {
    f.put('docs/work-plans/task.md', stateRecord.replace('배포 상태: 미수행', `배포 상태: ${state}`));
    assert.ok(has(f.inspect(), 'STATE_EVIDENCE'));
  }
});
test('state marker, observed timezone, and all five stages are required', t => {
  const f = fixture(t);
  for (const [record, code] of [
    [stateRecord.replace('상태 기록 버전: 1', '상태 기록 버전: 2'), 'STATE_VERSION'],
    [stateRecord.replace('> 상태 기록 버전: 1\n', ''), 'STATE_VERSION'],
    [stateRecord.replace('+09:00', ''), 'STATE_TIME'],
    [stateRecord.replace('> 배포 상태: 미수행\n', ''), 'STATE_VALUE'],
    [stateRecord.replace('구현 상태: 미수행', '구현 상태: 대충 완료'), 'STATE_VALUE'],
  ]) {
    f.put('docs/work-plans/task.md', record); assert.ok(has(f.inspect(), code));
  }
});
test('conflicting repeated stage fields fail', t => {
  const f = fixture(t); f.put('docs/work-plans/task.md', stateRecord + '> 구현 상태: 완료\n> 구현 근거: observed diff\n');
  assert.ok(has(f.inspect(), 'STATE_DUPLICATE'));
});
test('legacy never bypasses explicitly declared new status evidence', t => {
  const f = fixture(t); f.put('docs/work-plans/task.md', stateRecord.replace('구현 상태: 미수행', '구현 상태: 완료') + '> 형식 상태: legacy\n');
  assert.ok(has(f.inspect(), 'STATE_EVIDENCE'));
});
test('malformed and unsupported policy never defaults silently', t => {
  const f = fixture(t); f.put('docs/work-plans/task.md', stateRecord);
  for (const config of ['{', '{}', policy(''), policy('../dev'), policy('HEAD'), policy('dev.lock'), policy('dev').replace('schemaVersion":1', 'schemaVersion":2'), policy('dev').replace('integrationBranch', 'integrationBrnach')]) {
    f.put('harness.config.json', config); assert.ok(has(f.inspect(), 'CONFIG_INVALID'));
  }
});
