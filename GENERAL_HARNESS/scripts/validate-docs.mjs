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
const skipDirs = new Set(['node_modules', '.git']);
let failed = false;
let checked = 0;

function walk(dir) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (skipDirs.has(entry.name)) continue;
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) walk(p);
    else if (entry.isFile() && entry.name.endsWith('.md')) checkFile(p);
  }
}

function checkFile(file) {
  checked += 1;
  const rel = path.relative(root, file);
  const text = fs.readFileSync(file, 'utf8');
  if (text.trim().length === 0) {
    console.error(`FAIL empty md: ${rel}`);
    failed = true;
  }
  // Codex skills may carry YAML metadata before the Markdown title.
  // This is a title-location check; skill metadata is validated separately.
  const body = text.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n\s*/, '');
  if (!/^#\s+/.test(body)) {
    console.error(`FAIL missing top-level title: ${rel}`);
    failed = true;
  }
  const malformedLinks = [...text.matchAll(/\[[^\]]+\]\(([^)]+)\)/g)].filter(m => m[1].trim() === '');
  if (malformedLinks.length > 0) {
    console.error(`FAIL malformed empty link: ${rel}`);
    failed = true;
  }

  const duplicateH2Numbers = findDuplicateH2NumbersOutsideCode(text);
  if (duplicateH2Numbers.length > 0) {
    console.error(`FAIL duplicate H2 section numbers in ${rel}: ${duplicateH2Numbers.join(', ')}`);
    failed = true;
  }
}


function extractSectionTable(text, heading) {
  const idx = text.indexOf(heading);
  if (idx === -1) return null;
  const rest = text.slice(idx + heading.length);
  const lines = rest.split(/\r?\n/);
  const table = [];
  let started = false;
  for (const line of lines) {
    if (/^##\s/.test(line.trim())) break; // 다음 섹션 헤딩을 만나면 이 섹션 범위를 벗어난 것으로 본다
    if (line.trim().startsWith('|')) {
      started = true;
      table.push(line.trim());
      continue;
    }
    if (started) break;
  }
  return table.join('\n');
}

function checkPriorityTableSync(root) {
  const rulesPath = path.join(root, '00.HARNESS_RULES.md');
  const quickPath = path.join(root, '00.QUICK_REF.md');
  const rules = fs.readFileSync(rulesPath, 'utf8');
  const quick = fs.readFileSync(quickPath, 'utf8');
  const rulesTable = extractSectionTable(rules, '## 3. 충돌 해결 우선순위');
  if (!rulesTable) {
    console.error('FAIL cannot locate priority table in 00.HARNESS_RULES.md §3.');
    failed = true;
    return;
  }
  const quickTable = extractSectionTable(quick, '## 1. 충돌 우선순위');
  if (quickTable) {
    console.error('FAIL 00.QUICK_REF.md §1 duplicates the priority table again; it should only reference 00.HARNESS_RULES.md §3.');
    failed = true;
    return;
  }
  if (!quick.includes('00.HARNESS_RULES.md §3')) {
    console.error('FAIL 00.QUICK_REF.md §1 no longer references 00.HARNESS_RULES.md §3 as the owning source.');
    failed = true;
  }
}

function findDuplicateH2NumbersOutsideCode(text) {
  const seen = new Set();
  const duplicates = new Set();
  let inFence = false;

  for (const line of text.split(/\r?\n/)) {
    if (/^```/.test(line.trim())) {
      inFence = !inFence;
      continue;
    }
    if (inFence) continue;

    const match = line.match(/^##\s+(\d+)\.\s+/);
    if (!match) continue;
    const number = match[1];
    if (seen.has(number)) duplicates.add(number);
    else seen.add(number);
  }
  return [...duplicates];
}

walk(root);
checkPriorityTableSync(root);
if (failed) process.exit(1);
console.log(`PASS validate-docs: ${checked} markdown files checked. This is structure-level only, not semantic quality approval.`);
