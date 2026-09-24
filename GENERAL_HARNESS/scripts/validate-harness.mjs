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

const requiredFiles = [
  '00.HARNESS_RULES.md',
  '00.QUICK_REF.md',
  '01.SKILL_TEMPLATE.md',
  '02.SKILL_INDEX.md',
  '03.CONTEXT_BUDGET.md',
  '04.GATEGUARD.md',
  '05.WORKING_CONTEXT.md',
  '06.REPORT_TEMPLATE.md',
  '07.SECURITY_BASELINE.md',
  '08.QUALITY_GATE.md',
  '09.AGENT_WORKFLOW.md',
  '10.ADR.md',
  '_SOURCE_MAPPING.md',
  '_PENDING_IMPORT_LIST.md',
  '_WORKING_CONTEXT_HISTORY.md',
  'reports/_LATEST.md',
  'reports/README.md',
  'gates/document-gate.md',
  'gates/skill-gate.md',
  'gates/api-gate.md',
  'gates/db-gate.md',
  'gates/payment-gate.md',
  'gates/security-gate.md',
  'checklists/srs-checklist.md',
  'checklists/erd-checklist.md',
  'checklists/api-checklist.md',
  'checklists/payment-red-blue-checklist.md',
  'checklists/release-checklist.md',
  'scripts/validate-harness.mjs',
  'scripts/validate-docs.mjs',
  'scripts/validate-skills.mjs',
  'scripts/validate-package.mjs',
  'scripts/validate-no-personal-paths.mjs',
  'scripts/validate-references.mjs',
  'scripts/validate-report-consistency.mjs',
  'scripts/validate-no-secrets.mjs',
  'scripts/validate-work-records.mjs',
  'scripts/validate-project-adapter.mjs',
  'PROJECT_ADAPTER.md',
  'AI_RUNTIME_HANDOFF_TEMPLATE.md',
  'checklists/ai-runtime-integration-checklist.md',
  'templates/project-adapter/00.PROJECT_CONTEXT.md',
  'templates/project-adapter/manifest.example.json',
  'scripts/harness-stats.mjs'
];

const requiredDirs = ['skills', 'gates', 'checklists', 'reports', 'scripts'];

let failed = false;
for (const dir of requiredDirs) {
  const p = path.join(root, dir);
  if (!fs.existsSync(p) || !fs.statSync(p).isDirectory()) {
    console.error(`FAIL missing directory: ${dir}`);
    failed = true;
  }
}
for (const file of requiredFiles) {
  const p = path.join(root, file);
  if (!fs.existsSync(p) || !fs.statSync(p).isFile()) {
    console.error(`FAIL missing file: ${file}`);
    failed = true;
  }
}
if (failed) process.exit(1);
console.log('PASS validate-harness: required files and directories exist. This is structure-level only, not semantic quality approval.');
