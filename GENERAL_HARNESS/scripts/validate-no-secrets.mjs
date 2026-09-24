#!/usr/bin/env node
// validate-no-secrets: 저장소에 커밋되면 안 되는 비밀값(토큰·키·개인키 블록)과
// 추적되면 안 되는 민감 파일(zip, .env, 개인키 파일, 로컬 에이전트 설정)이
// Git 추적 대상에 들어 있지 않은지 검사한다.
//
// 도입 근거(실제 사고 2건, 2026-08-02~03):
//   - 민감 검수 문서와 외부 원본 zip이 PUBLIC 저장소에 push되어 이력 재작성으로 제거함
//   - 로컬 에이전트 설정(.claude/settings.json)이 `git add -A`에 딸려 커밋됨
// 이 스크립트는 위 사고의 재발 경로를 커밋/CI 시점에 기계적으로 차단한다.
//
// 한계: 패턴 목록에 없는 형식의 비밀값, 마스킹을 우회한 난독화 값, 이미 과거
// 커밋 이력에 들어간 비밀값은 잡지 못한다(이력 정리는 별도 절차).
import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';

function findRepoRoot() {
  // GENERAL_HARNESS 안에서 실행돼도 저장소 전체(.git 있는 곳)를 검사한다.
  let dir = process.cwd();
  for (let i = 0; i < 5; i++) {
    if (fs.existsSync(path.join(dir, '.git'))) return dir;
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return null;
}

const repoRoot = findRepoRoot();
if (!repoRoot) {
  console.error('FAIL cannot locate repository root (.git). Run inside the git repository.');
  process.exit(1);
}

let trackedFiles;
try {
  trackedFiles = execSync('git ls-files', { cwd: repoRoot, encoding: 'utf8' })
    .split('\n').map(s => s.trim()).filter(Boolean);
} catch {
  console.error('FAIL git ls-files failed. This check requires a working git environment.');
  process.exit(1);
}

let failed = false;

// 1. 추적되면 안 되는 파일 패턴 (내용과 무관하게 존재 자체가 FAIL)
const forbiddenFilePatterns = [
  { re: /(^|\/)\.claude\//, why: '로컬 에이전트 설정은 공유하지 않는다(.gitignore 정책)' },
  { re: /\.zip$/i, why: '외부 반입 원본 zip은 저장소에 올리지 않는다(.gitignore 정책)' },
  { re: /(^|\/)\.env(\.|$)/, why: '환경변수 파일은 비밀값을 담을 수 있다' },
  { re: /\.(pem|p12|pfx|jks|keystore)$/i, why: '키/인증서 파일' },
  { re: /(^|\/)id_(rsa|ed25519|ecdsa)(\.|$)/, why: 'SSH 개인키' },
];
for (const f of trackedFiles) {
  for (const { re, why } of forbiddenFilePatterns) {
    if (re.test(f)) {
      console.error(`FAIL tracked file should not be in the repository: ${f} (${why})`);
      failed = true;
    }
  }
}

// 2. 파일 내용의 비밀값 패턴 (텍스트 파일만, 1MB 초과·바이너리 확장자는 건너뜀)
const secretPatterns = [
  { name: 'AWS Access Key', re: /\bAKIA[0-9A-Z]{16}\b/ },
  { name: 'GitHub token', re: /\bgh[pousr]_[A-Za-z0-9]{20,}\b/ },
  { name: 'GitHub fine-grained PAT', re: /\bgithub_pat_[A-Za-z0-9_]{22,}\b/ },
  { name: 'Slack token', re: /\bxox[baprs]-[A-Za-z0-9-]{10,}\b/ },
  { name: 'Generic sk- API key', re: /\bsk-[A-Za-z0-9_-]{20,}\b/ },
  { name: 'Google API key', re: /\bAIza[0-9A-Za-z_-]{35}\b/ },
  { name: 'Private key block', re: /-----BEGIN [A-Z ]*PRIVATE KEY-----/ },
  { name: 'JWT', re: /\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b/ },
];
const binaryExt = /\.(png|jpg|jpeg|gif|svg|ico|woff2?|ttf|eot|pdf|zip|gz|tar|exe|dll|bin)$/i;
// 문서에서 마스킹된 예시(gho_****)나 placeholder({TOKEN})는 잡지 않는다 — 패턴 자체가
// 실제 문자셋만 매칭하므로 별도 허용 목록은 두지 않는다. 추가 예외가 필요해지면
// 아래 allowlist에 "파일경로:패턴이름"을 등록하고 사유를 주석으로 남긴다.
const allowlist = new Set([]);

for (const f of trackedFiles) {
  if (binaryExt.test(f)) continue;
  const full = path.join(repoRoot, f);
  if (!fs.existsSync(full)) continue;
  const stat = fs.statSync(full);
  if (stat.size > 1024 * 1024) continue;
  const text = fs.readFileSync(full, 'utf8');
  for (const { name, re } of secretPatterns) {
    if (re.test(text)) {
      if (allowlist.has(`${f}:${name}`)) continue;
      const line = text.split(/\r?\n/).findIndex(l => re.test(l)) + 1;
      console.error(`FAIL possible secret (${name}) in ${f}:${line}`);
      failed = true;
    }
  }
}

if (failed) process.exit(1);
console.log(`PASS validate-no-secrets: ${trackedFiles.length} tracked files checked — no forbidden file patterns (.claude/, *.zip, .env, key files) and no known secret token patterns (AWS/GitHub/Slack/sk-/Google/private key/JWT). This does not cover unknown token formats, obfuscated values, or secrets already buried in past commit history.`);
