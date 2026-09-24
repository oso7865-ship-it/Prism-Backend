#!/usr/bin/env node
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

  const entries = fs.readdirSync(cwd, { withFileTypes: true });
  const candidates = entries
    .filter((entry) => entry.isDirectory())
    .map((entry) => path.join(cwd, entry.name))
    .filter(isHarnessRoot);

  if (candidates.length === 1) return candidates[0];
  if (candidates.length > 1) {
    console.error('FAIL multiple harness roots found. Use the stable GENERAL_HARNESS folder or run from the intended harness root.');
    process.exit(1);
  }

  console.error('FAIL cannot locate GENERAL_HARNESS root. Run from the harness root or its parent directory.');
  process.exit(1);
}

const root = resolveRoot();
const skillsRoot = path.join(root, 'skills');
const requiredSections = [
  'Harness Control Rule',
  'Trigger',
  'Do Not Trigger',
  'Required Inputs',
  'Procedure',
  'Quality Gate',
  'Handoff'
];

let failed = false;
const skillDirs = fs.readdirSync(skillsRoot, { withFileTypes: true }).filter(d => d.isDirectory()).map(d => d.name);

for (const dir of skillDirs) {
  const file = path.join(skillsRoot, dir, 'SKILL.md');
  if (!fs.existsSync(file)) {
    console.error(`FAIL ${dir}: SKILL.md missing`);
    failed = true;
    continue;
  }

  const text = fs.readFileSync(file, 'utf8');
  const sections = extractLevel2Sections(text);

  for (const section of requiredSections) {
    if (!sections.has(section)) {
      console.error(`FAIL ${dir}: missing section ${section}`);
      failed = true;
    }
  }

  const hcrText = sections.get('Harness Control Rule') ?? '';
  if (hcrText) {
    const hasRootRule = /00\.HARNESS_RULES\.md/.test(hcrText);
    const hasSubmodule = /하위 모듈/.test(hcrText);
    const hasConflictStop = /(충돌.*(상위 규칙|중단|따른다)|(상위 규칙).*(충돌|따른다))/.test(hcrText);
    const hasRiskWarnLimit = /(위험 작업|DB|결제|보안|WARN).*(단독으로 진행하지 않는다|중단|사용자 확인)/.test(hcrText);
    if (!(hasRootRule && hasSubmodule && hasConflictStop && hasRiskWarnLimit)) {
      console.error(`FAIL ${dir}: Harness Control Rule must reference 00.HARNESS_RULES.md, define the skill as a 하위 모듈, stop/defer on conflicts, and restrict risky WARN work`);
      failed = true;
    }
  }

  const gateText = sections.get('Quality Gate') ?? '';
  if (gateText && !(/\bPASS\b/.test(gateText) && /\bWARN\b/.test(gateText) && /\bFAIL\b/.test(gateText))) {
    console.error(`FAIL ${dir}: Quality Gate must include PASS/WARN/FAIL`);
    failed = true;
  }

  const handoffText = sections.get('Handoff') ?? '';
  for (const target of extractCodeSpanTargets(handoffText)) {
    if (isPlaceholderTarget(target)) continue;
    if (!targetExists(root, target)) {
      console.error(`FAIL ${dir}: Handoff target does not exist: ${target}`);
      failed = true;
    }
  }
}

function extractLevel2Sections(text) {
  const result = new Map();
  const lines = text.split(/\r?\n/);
  let current = null;
  let buffer = [];

  for (const line of lines) {
    const match = line.match(/^##\s+(?:\d+\.?\s*)?(.+?)\s*$/);
    if (match) {
      if (current) result.set(current, buffer.join('\n'));
      current = match[1].trim();
      buffer = [line];
    } else if (current) {
      buffer.push(line);
    }
  }
  if (current) result.set(current, buffer.join('\n'));
  return result;
}

function extractCodeSpanTargets(text) {
  return [...text.matchAll(/`([^`]+)`/g)].map(m => m[1].trim()).filter(Boolean);
}

function isPlaceholderTarget(target) {
  return /[{}]/.test(target) || target.includes('target-');
}

function targetExists(root, target) {
  if (target.startsWith('skills/')) {
    if (!target.endsWith('/SKILL.md')) return false;
    const skillFile = path.join(root, target);
    return fs.existsSync(skillFile) && fs.statSync(skillFile).isFile();
  }
  if (target.endsWith('.md')) {
    const mdFile = path.join(root, target);
    return fs.existsSync(mdFile) && fs.statSync(mdFile).isFile();
  }
  return false;
}

if (failed) process.exit(1);
console.log(`PASS validate-skills: ${skillDirs.length} skills checked. This is structure-level plus low-cost harness-control and Handoff-target validation, not full skill quality approval.`);
