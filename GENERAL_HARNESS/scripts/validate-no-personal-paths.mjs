#!/usr/bin/env node
// validate-no-personal-paths: 07.SECURITY_BASELINE.md의 "개인 경로 노출 금지" 규칙을 자동 검사한다.
// ECC 원본 아이디어(scripts/ci/validate-no-personal-paths.js)를 참고해 이 하네스 스크립트 스타일로 재작성함.
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

// macOS: /Users/<name>/... , Windows: C:\Users\<name>\... 또는 C:/Users/<name>/... , 기타 드라이브 문자, UNC 경로
// 플레이스홀더로 흔히 쓰는 "설명용" 이름만 예외로 둔다. 실제 사람 이름은 예외에 넣지 않는다
// (과거에 실제 사용자 이름이 예외 목록에 들어가 있던 적이 있었는데, 그건 이 검사의 목적과
// 정반대라 제거함 — 외부 검수 M-08).
const PLACEHOLDER_NAMES = new Set(['username', 'user', 'yourname', 'name', '사용자', 'youruser', 'currentuser']);

const PATTERNS = [
  /\/Users\/([\p{L}\p{N}._-]+)/gu,
  /[A-Za-z]:\\Users\\([\p{L}\p{N}._-]+)/gu,
  /[A-Za-z]:\/Users\/([\p{L}\p{N}._-]+)/gu,
  /\\\\[\p{L}\p{N}._-]+\\Users\\([\p{L}\p{N}._-]+)/gu, // UNC 경로: \\server\Users\name
  /\/home\/([\p{L}\p{N}._-]+)/gu,
  /\/root\/([\p{L}\p{N}._-]+)/gu,
];

function walk(dir, files = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === 'node_modules' || entry.name === '.git') continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(full, files);
    } else if (entry.name.endsWith('.md') || entry.name.endsWith('.mjs')) {
      files.push(full);
    }
  }
  return files;
}

let failed = false;
const hits = [];

for (const file of walk(root)) {
  const text = fs.readFileSync(file, 'utf8');
  for (const pattern of PATTERNS) {
    let m;
    pattern.lastIndex = 0;
    while ((m = pattern.exec(text)) !== null) {
      const name = m[1];
      if (PLACEHOLDER_NAMES.has(name.toLowerCase())) continue;
      if (/^\.+$/.test(name)) continue; // "...", ".." 같은 설명용 placeholder는 실제 경로가 아님
      hits.push({ file: path.relative(root, file), match: m[0] });
    }
  }
}

if (hits.length > 0) {
  console.error(`FAIL personal absolute paths found in ${hits.length} location(s):`);
  for (const hit of hits.slice(0, 20)) {
    console.error(`  - ${hit.file}: ${hit.match}`);
  }
  if (hits.length > 20) console.error(`  ... and ${hits.length - 20} more`);
  failed = true;
}

if (failed) process.exit(1);
console.log('PASS validate-no-personal-paths: no personal paths found matching supported patterns (macOS /Users/, Windows drive:\\Users\\ or UNC \\\\server\\Users\\, /home/, /root/, Unicode names included). This does not cover every possible OS path convention(e.g. non-Users-style corporate mount points), and explicit placeholder names listed in the script are exempt.');
