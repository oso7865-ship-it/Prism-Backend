#!/usr/bin/env node
// Read-only work-record inspection. Adapted from the service-side validator;
// scope, deterministic findings and exit status are explicit. No Git facts inferred.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const slash = value => value.split(path.sep).join('/');
const inside = (root, file) => {
  const rel = path.relative(root, file);
  return rel !== '..' && !rel.startsWith(`..${path.sep}`) && !path.isAbsolute(rel);
};
function withoutExamples(text) {
  let fence = null;
  return text.replace(/^\uFEFF/, '').split(/\r?\n/).map(line => {
    const match = line.match(/^\s*(`{3,}|~{3,})/);
    if (match) {
      if (!fence) fence = match[1];
      else if (match[1][0] === fence[0] && match[1].length >= fence.length) fence = null;
      return '';
    }
    return fence ? '' : line;
  });
}
function fields(lines, label) {
  const re = new RegExp(`^\\s*(?:>\\s*|[-*]\\s*|\\|\\s*)?${label}\\s*(?::|：|\\|)\\s*(.*?)\\s*\\|?\\s*$`);
  return lines.flatMap((line, index) => {
    const match = line.match(re);
    return match ? [{ value: match[1].trim(), line: index + 1 }] : [];
  });
}

const stages = ['구현', '로컬 검증', '병합', '배포', '실제 연동'];
const meaningful = value => Boolean(value && !/^(?:[-—.]|\.{3}|…|없음|미확인|미수행|TODO|TBD|N\/A|해당 없음|\{.*\}|<.*>)$/i.test(value));
function checkStageEvidence(lines, file, policy, add) {
  const version = fields(lines, '상태 기록 버전');
  if (!version.length && !stages.some(stage => fields(lines, `${stage} 상태`).length)) return;
  const one = label => {
    const matches = fields(lines, label);
    if (matches.length > 1) add('FAIL', 'STATE_DUPLICATE', file, `Repeated state field: ${label}`);
    return matches[0]?.value.replace(/`/g, '').trim() ?? '';
  };
  if (one('상태 기록 버전') !== '1') add('FAIL', 'STATE_VERSION', file, 'Stage evidence requires 상태 기록 버전: 1.');
  const time = one('상태 확인 시각');
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})$/.test(time) || !Number.isFinite(Date.parse(time))) {
    add('FAIL', 'STATE_TIME', file, 'Record an ISO timestamp with timezone for the observed state.');
  }
  for (const stage of stages) {
    const state = one(`${stage} 상태`);
    const evidence = one(`${stage} 근거`);
    if (!['완료', '진행 중', '미수행', '미확인', '해당 없음', '실패'].includes(state)) add('FAIL', 'STATE_VALUE', file, `Missing or unsupported ${stage} 상태.`);
    if (['완료', '실패', '해당 없음'].includes(state) && !meaningful(evidence)) add('FAIL', 'STATE_EVIDENCE', file, `${stage}: evidence or a not-applicable reason is required.`);
    if (stage === '로컬 검증' && state === '완료' && !meaningful(one('로컬 검증 대상'))) add('FAIL', 'VALIDATION_TARGET', file, 'Completed local validation needs an identified commit or working-tree scope.');
    if (stage === '병합' && state === '완료') {
      const target = one('병합 대상');
      if (!policy) add('FAIL', 'MERGE_POLICY', file, 'Completed merge requires explicit harness.config.json Git policy.');
      else if (target !== `${policy.remote}/${policy.integrationBranch}`) add('FAIL', 'MERGE_TARGET', file, 'Merge target does not match the configured official integration branch.');
    }
  }
}

export function inspectRecords(options = {}) {
  const findings = [];
  const targets = [];
  const files = new Set();
  const add = (severity, code, file, message, line) => findings.push({ severity, code, file, ...(line ? { line } : {}), message });
  let root = path.resolve(options.projectRoot ?? process.cwd());
  const relative = file => slash(path.relative(root, file)) || '.';
  let planFiles = [], reportFiles = [];
  let gitPolicy = null;
  function safe(file) {
    if (!inside(root, file)) throw new Error('path is outside the selected project');
    let current = root;
    for (const part of path.relative(root, file).split(path.sep).filter(Boolean)) {
      current = path.join(current, part);
      if (fs.existsSync(current) && fs.lstatSync(current).isSymbolicLink()) throw new Error('symbolic links are not inspected');
    }
    return file;
  }
  function collect(kind, configured, fallback) {
    const folder = path.resolve(root, configured ?? fallback);
    const target = { kind, path: relative(folder), required: configured !== undefined, state: 'missing', count: 0 };
    targets.push(target);
    const result = [];
    try {
      safe(folder);
      if (!fs.existsSync(folder)) {
        if (target.required) add('FAIL', 'TARGET_MISSING', target.path, 'Explicitly requested directory is missing.');
        return result;
      }
      if (!fs.statSync(folder).isDirectory()) throw new Error('target is not a directory');
      target.state = 'present';
      const walk = dir => {
        for (const entry of fs.readdirSync(dir, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
          if (entry.name === 'archive' || entry.name.startsWith('.')) continue;
          const file = safe(path.join(dir, entry.name));
          if (entry.isDirectory()) walk(file);
          else if (entry.isFile() && /\.md$/i.test(entry.name) && !/^(README|_LATEST)\.md$/i.test(entry.name)) result.push(file);
        }
      };
      walk(folder);
      target.count = result.length;
      if (!result.length) {
        target.state = 'empty';
        if (target.required) add('FAIL', 'TARGET_EMPTY', target.path, 'Explicitly requested directory contains no active records.');
      }
    } catch (error) {
      target.state = 'unreadable';
      add('FAIL', 'TARGET_UNREADABLE', target.path, error.code ?? error.message);
    }
    return result;
  }
  try {
    root = fs.realpathSync(root);
    if (!fs.statSync(root).isDirectory()) throw new Error('project root is not a directory');
    const registry = safe(path.join(root, 'GENERAL_HARNESS', 'skills'));
    const skills = new Set(fs.readdirSync(registry, { withFileTypes: true })
      .filter(entry => entry.isDirectory() && fs.existsSync(path.join(registry, entry.name, 'SKILL.md')))
      .map(entry => entry.name));
    if (!skills.size) throw new Error('skill registry is empty');
    try {
      const configFile = safe(path.join(root, 'harness.config.json'));
      if (fs.existsSync(configFile)) {
        const config = JSON.parse(fs.readFileSync(configFile, 'utf8').replace(/^\uFEFF/, ''));
        const branch = config?.git?.integrationBranch;
        const remote = config?.git?.remote;
        const validBranch = typeof branch === 'string' && /^[A-Za-z0-9][A-Za-z0-9._/-]*$/.test(branch)
          && !branch.includes('..') && !branch.includes('//') && !branch.split('/').some(part => part.startsWith('.') || part.endsWith('.') || part.endsWith('.lock'))
          && !branch.endsWith('/') && branch !== 'HEAD';
        if (config?.schemaVersion !== 1 || typeof remote !== 'string' || !/^[A-Za-z0-9][A-Za-z0-9_-]*$/.test(remote) || !validBranch) throw new Error('Expected schemaVersion 1 and explicit safe remote/integrationBranch names.');
        if (Object.keys(config).some(key => !['schemaVersion', 'git'].includes(key)) || Object.keys(config.git).some(key => !['remote', 'integrationBranch'].includes(key))) throw new Error('Unknown configuration key.');
        gitPolicy = { remote, integrationBranch: branch };
      }
    } catch (error) { add('FAIL', 'CONFIG_INVALID', 'harness.config.json', error.code ?? error.message); }
    planFiles = collect('plans', options.plans, 'docs/work-plans');
    reportFiles = collect('reports', options.reports, 'reports');
    for (const file of new Set([...planFiles, ...reportFiles])) {
      try {
        const lines = withoutExamples(fs.readFileSync(file, 'utf8'));
        files.add(relative(file));
        if (!lines.some(line => line.trim())) add('FAIL', 'RECORD_EMPTY', relative(file), 'Record has no non-example content.');
        checkStageEvidence(lines, relative(file), gitPolicy, add);
        for (const field of fields(lines, '적용\\s*(?:스킬|절차)')) {
          const names = field.value.replace(/`/g, '').replace(/\bHarness\b/g, '').replace(/[.;]\s*$/, '').split(/[,、]/).map(s => s.trim()).filter(Boolean);
          for (const name of names) {
            if (['해당 없음', 'N/A', '없음'].includes(name)) continue;
            if (!/^[A-Za-z][A-Za-z0-9-]*$/.test(name)) add('WARN', 'SKILL_FORMAT', relative(file), 'Use a comma-separated canonical skill list.', field.line);
            else if (!skills.has(name)) add('FAIL', 'SKILL_UNKNOWN', relative(file), `Unregistered skill: ${name}`, field.line);
          }
        }
        const legacy = fields(lines, '형식 상태').some(field => field.value === 'legacy');
        if (reportFiles.includes(file) && !legacy) {
          for (const label of ['작업 브랜치', '커밋/PR', '작업 범위', '적용 스킬', '적용 Gate', '위험도']) {
            const acceptedLabel = label === '적용 스킬' ? '적용\\s*(?:스킬|절차)' : label;
            if (!fields(lines, acceptedLabel).some(field => field.value.replace(/`/g, '').trim())) add('FAIL', 'HEADER_MISSING', relative(file), `Missing non-empty header: ${label}`);
          }
        }
        const risk = fields(lines, '위험도').map(field => field.value).join(' ');
        const gates = fields(lines, '적용 Gate').map(field => field.value).join(' ');
        for (const [trigger, gate, token] of [
          [/\bDB\b|데이터베이스|스키마/i, 'DB', 'db-gate'],
          [/인증|인가|권한|보안|개인정보|외부\s*(?:연동|API|서비스)|제3자\s*API|security|external/i, 'Security', 'security-gate'],
          [/결제|환불|payment|refund/i, 'Payment', 'payment-gate'],
        ]) {
          if (trigger.test(risk) && !new RegExp(`\\b${gate}\\s+Gate\\b|${token}\\.md`, 'i').test(gates)) {
            add('WARN', 'GATE_REVIEW', relative(file), `${gate} Gate may be required; review the declared risk and applicability.`);
          }
        }
      } catch (error) { add('FAIL', 'RECORD_UNREADABLE', relative(file), error.code ?? error.message); }
    }
    const reportDir = path.resolve(root, options.reports ?? 'reports');
    const latest = path.join(reportDir, '_LATEST.md');
    if (targets.find(t => t.kind === 'reports')?.state !== 'unreadable') {
      safe(latest);
      if (fs.existsSync(latest)) {
        const lines = withoutExamples(fs.readFileSync(latest, 'utf8'));
        const table = lines.filter(line => /^\|\s*(?:하네스 유지보수 최신|부착 프로젝트 최신|최신 판단 기준)\s*\|/.test(line));
        const selected = table.length ? table.map(line => line.split('|')[2]).filter(cell => !cell.includes('해당 프로젝트')) : lines;
        const references = selected.flatMap(line => [
          ...[...line.matchAll(/\[[^\]]*\]\(([^)]+\.md(?:#[^)]*)?)\)/g)].map(m => ({ value: m[1], type: 'link' })),
          ...[...line.matchAll(/`([^`]+\.md)`/g)].map(m => ({ value: m[1], type: 'code' })),
        ]);
        if (!references.length) add('FAIL', 'POINTER_FORMAT', relative(latest), 'No supported local Markdown target found.');
        for (const ref of references) {
          try {
            const value = decodeURIComponent(ref.value.split('#')[0]).replaceAll('\\', '/');
            if (/^[a-z]+:|^\//i.test(value)) throw new Error('only project-local pointer targets are supported');
            const prefix = relative(reportDir) + '/';
            const origin = ref.type === 'code' && value.startsWith(prefix) ? root
              : ref.type === 'code' && value.startsWith(path.basename(reportDir) + '/') ? path.dirname(reportDir) : reportDir;
            const target = safe(path.resolve(origin, value));
            if (!fs.existsSync(target) || !fs.statSync(target).isFile()) throw new Error('pointer target is missing or is not a file');
            if (/^(README|_LATEST)\.md$/i.test(path.basename(target)) || path.relative(reportDir, target).split(path.sep).includes('archive')) throw new Error('pointer must identify an active report');
            if (!reportFiles.includes(target)) add('WARN', 'POINTER_OUTSIDE_SCOPE', relative(latest), 'Pointer target exists but is outside the selected report scope.');
            const date = path.basename(target).match(/^(\d{4}-\d{2}-\d{2})[_-]/)?.[1];
            if (date && reportFiles.some(file => path.dirname(file) === path.dirname(target) && (path.basename(file).match(/^(\d{4}-\d{2}-\d{2})[_-]/)?.[1] ?? '') > date)) {
              add('WARN', 'POINTER_NEWER_RECORD', relative(latest), 'A report has a later filename date; review which history it belongs to.');
            }
          } catch (error) { add('FAIL', 'POINTER_INVALID', relative(latest), error.code ?? error.message); }
        }
      } else if (reportFiles.length) add('WARN', 'POINTER_MISSING', relative(latest), 'Active reports exist without a latest pointer.');
    }
  } catch (error) { add('FAIL', 'INPUT_INVALID', '.', error.code ?? error.message); }
  const status = findings.some(f => f.severity === 'FAIL') ? 'FAIL' : !files.size ? 'NOT_CHECKED' : findings.length ? 'WARN' : 'PASS';
  return {
    schemaVersion: 1, status,
    exitCode: status === 'NOT_CHECKED' ? 2 : status === 'FAIL' || (status === 'WARN' && options.strict) ? 1 : 0,
    strict: Boolean(options.strict), gitPolicy, targets, checkedFiles: [...files].sort(), checkedCount: files.size, findings,
    limitations: 'No Git/PR fact verification or complete semantic Gate judgment. README, _LATEST, hidden entries and archive directories are not records; latest pointers are checked separately.',
  };
}

export function runCli(args = process.argv.slice(2)) {
  const options = {};
  const keys = { '--project-root': 'projectRoot', '--plans': 'plans', '--reports': 'reports' };
  try {
    for (let i = 0; i < args.length; i++) {
      const arg = args[i];
      if (arg === '--strict' || arg === '--json') options[arg.slice(2)] = true;
      else if (keys[arg] && args[i + 1] && !args[i + 1].startsWith('--')) {
        if (options[keys[arg]] !== undefined) throw new Error(`Repeated option: ${arg}`);
        options[keys[arg]] = args[++i];
      } else throw new Error(`Unknown option or missing value: ${arg}`);
    }
    if (!options.projectRoot) {
      const cwd = process.cwd();
      options.projectRoot = path.basename(cwd) === 'GENERAL_HARNESS' ? path.dirname(cwd) : cwd;
    }
    const result = inspectRecords(options);
    if (options.json) console.log(JSON.stringify(result, null, 2));
    else {
      console.log(`${result.status} validate-work-records: checked=${result.checkedCount}, exit=${result.exitCode}, strict=${result.strict}`);
      for (const target of result.targets) console.log(`TARGET ${target.kind}: ${target.path} (${target.required ? 'required' : 'optional'}, ${target.state}, records=${target.count})`);
      for (const finding of result.findings) console.log(`${finding.severity} ${finding.code} ${finding.file}${finding.line ? ':' + finding.line : ''}: ${finding.message}`);
      console.log(result.limitations);
    }
    return result.exitCode;
  } catch (error) {
    const result = { schemaVersion: 1, status: 'FAIL', exitCode: 1, checkedCount: 0, checkedFiles: [], targets: [], findings: [{ severity: 'FAIL', code: 'CLI_USAGE', file: '.', message: error.message }] };
    console.log(args.includes('--json') ? JSON.stringify(result) : `FAIL CLI_USAGE: ${error.message}`);
    return 1;
  }
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) process.exitCode = runCli();
