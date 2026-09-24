#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { inflateRawSync } from 'node:zlib';

// 이 스크립트는 `unzip` 외부 명령에 의존하지 않는다. 순수 Node(fs/zlib)만으로
// ZIP 중앙 디렉터리(Central Directory)를 직접 파싱한다 — Windows 등 `unzip`이
// 없는 환경에서 "검사 못 함"이 조용히 WARN/PASS로 새는 문제를 근본적으로 없앤다
// (외부 검수 C-01, G-01, G-07).

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

function walkFiles(dir, base, files = []) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === 'node_modules' || entry.name === '.git') continue;
    const full = path.join(dir, entry.name);
    const rel = path.relative(base, full).split(path.sep).join('/');
    if (entry.isDirectory()) {
      walkFiles(full, base, files);
    } else {
      files.push(rel);
    }
  }
  return files;
}

// --- 최소 ZIP 리더: End of Central Directory + Central Directory 레코드만 파싱한다 ---
function readZipEntries(zipPath) {
  const buf = fs.readFileSync(zipPath);
  const EOCD_SIG = 0x06054b50;
  const CDH_SIG = 0x02014b50;

  let eocdOffset = -1;
  const searchStart = Math.max(0, buf.length - 65535 - 22);
  for (let i = buf.length - 22; i >= searchStart; i--) {
    if (buf.readUInt32LE(i) === EOCD_SIG) { eocdOffset = i; break; }
  }
  if (eocdOffset === -1) throw new Error('End of Central Directory record not found (not a valid ZIP or truncated file)');

  const totalEntries = buf.readUInt16LE(eocdOffset + 10);
  const cdSize = buf.readUInt32LE(eocdOffset + 12);
  const cdOffset = buf.readUInt32LE(eocdOffset + 16);
  if (cdOffset + cdSize > buf.length) throw new Error('Central Directory offset/size exceeds file length (corrupt ZIP)');

  const entries = [];
  let ptr = cdOffset;
  for (let i = 0; i < totalEntries; i++) {
    if (buf.readUInt32LE(ptr) !== CDH_SIG) throw new Error(`Central Directory record #${i} has bad signature (corrupt ZIP)`);
    const compressionMethod = buf.readUInt16LE(ptr + 10);
    const compressedSize = buf.readUInt32LE(ptr + 20);
    const uncompressedSize = buf.readUInt32LE(ptr + 24);
    const nameLen = buf.readUInt16LE(ptr + 28);
    const extraLen = buf.readUInt16LE(ptr + 30);
    const commentLen = buf.readUInt16LE(ptr + 32);
    const localHeaderOffset = buf.readUInt32LE(ptr + 42);
    const nameStart = ptr + 46;
    const name = buf.toString('utf8', nameStart, nameStart + nameLen);
    entries.push({ name, compressionMethod, compressedSize, uncompressedSize, localHeaderOffset });
    ptr = nameStart + nameLen + extraLen + commentLen;
  }
  return { buf, entries };
}

function readEntryContent(buf, entry) {
  const LFH_SIG = 0x04034b50;
  const off = entry.localHeaderOffset;
  if (buf.readUInt32LE(off) !== LFH_SIG) throw new Error(`Local File Header for "${entry.name}" has bad signature (corrupt ZIP)`);
  const nameLen = buf.readUInt16LE(off + 26);
  const extraLen = buf.readUInt16LE(off + 28);
  const dataStart = off + 30 + nameLen + extraLen;
  const raw = buf.subarray(dataStart, dataStart + entry.compressedSize);
  if (entry.compressionMethod === 0) return raw;
  if (entry.compressionMethod === 8) return inflateRawSync(raw);
  throw new Error(`Unsupported compression method ${entry.compressionMethod} for "${entry.name}"`);
}

const root = resolveRoot();
const baseName = path.basename(root);
let failed = false;
const warnings = [];

if (baseName !== 'GENERAL_HARNESS') {
  console.error(`FAIL package root folder must be GENERAL_HARNESS, got: ${baseName}`);
  failed = true;
}

const parent = path.dirname(root);
// --zip <경로> 인자로 검사 대상 ZIP을 명시적으로 지정할 수 있다(외부 검수 C-01, G-01).
// 지정하지 않으면 기존처럼 GENERAL_HARNESS.zip을 기본 대상으로 삼는다.
function parseZipArg() {
  const idx = process.argv.indexOf('--zip');
  if (idx === -1) return null;
  const value = process.argv[idx + 1];
  if (!value) {
    console.error('FAIL --zip flag given but no path followed it');
    process.exit(1);
  }
  return path.resolve(value);
}

const zipArg = parseZipArg();
const expectedZip = zipArg || path.join(parent, 'GENERAL_HARNESS.zip');
console.error(`INFO inspecting_zip=${expectedZip}`);
const zipExists = fs.existsSync(expectedZip);
if (zipExists && !fs.statSync(expectedZip).isFile()) {
  console.error('FAIL GENERAL_HARNESS.zip exists but is not a file');
  failed = true;
}

// ZIP이 없거나 파싱할 수 없으면 이제 PASS/WARN이 아니라 FAIL이다(외부 검수 C-01, G-01).
let zipInspected = false;
if (!zipExists) {
  console.error(`FAIL ${expectedZip} not found. Package verification cannot proceed without an actual deployable ZIP at the inspected path (this used to be a WARN; now it blocks publish).`);
  failed = true;
} else {
  let parsed;
  try {
    parsed = readZipEntries(expectedZip);
    zipInspected = true;
  } catch (err) {
    console.error(`FAIL could not parse ZIP internals: ${err.message}`);
    failed = true;
  }

  if (zipInspected) {
    const { buf, entries } = parsed;
    const names = entries.map(e => e.name);

    const roots = new Set(names.map(n => n.split('/')[0]));
    if (roots.size !== 1 || ![...roots][0] || [...roots][0] !== 'GENERAL_HARNESS') {
      console.error(`FAIL ZIP does not have a single "GENERAL_HARNESS" root. Found root(s): ${[...roots].join(', ')}`);
      failed = true;
    }

    const traversal = names.filter(n => n.startsWith('/') || n.includes('..'));
    if (traversal.length > 0) {
      console.error(`FAIL ZIP contains unsafe path entries (absolute path or "..") : ${traversal.slice(0, 5).join(', ')}`);
      failed = true;
    }

    const exactSeen = new Map();
    for (const n of names) exactSeen.set(n, (exactSeen.get(n) || 0) + 1);
    const exactDupes = [...exactSeen].filter(([, c]) => c > 1).map(([n, c]) => `${n} (x${c})`);
    if (exactDupes.length > 0) {
      console.error(`FAIL ZIP has exact duplicate entries (same name appears more than once): ${exactDupes.slice(0, 5).join(', ')}`);
      failed = true;
    }

    const lowerSeen = new Map();
    const caseDupes = [];
    for (const n of names) {
      const lower = n.toLowerCase();
      if (lowerSeen.has(lower) && lowerSeen.get(lower) !== n) caseDupes.push(n);
      lowerSeen.set(lower, n);
    }
    if (caseDupes.length > 0) {
      console.error(`FAIL ZIP has case-insensitive duplicate entries: ${caseDupes.slice(0, 5).join(', ')}`);
      failed = true;
    }

    for (const required of ['00.HARNESS_RULES.md', 'skills/', 'scripts/']) {
      const found = names.some(n => n === `GENERAL_HARNESS/${required}` || n.startsWith(`GENERAL_HARNESS/${required}`));
      if (!found) {
        console.error(`FAIL ZIP is missing required entry: GENERAL_HARNESS/${required}`);
        failed = true;
      }
    }

    const zipFileMap = new Map();
    for (const e of entries) {
      if (!e.name.endsWith('/')) zipFileMap.set(e.name.replace(/^GENERAL_HARNESS\//, ''), e);
    }
    const diskFiles = walkFiles(root, root);
    const diskFileSet = new Set(diskFiles);
    const zipFileSet = new Set(zipFileMap.keys());

    const missingFromZip = diskFiles.filter(f => !zipFileSet.has(f));
    const extraInZip = [...zipFileSet].filter(f => !diskFileSet.has(f));
    if (missingFromZip.length > 0) {
      console.error(`FAIL ${missingFromZip.length} file(s) on disk are missing from ZIP: ${missingFromZip.slice(0, 5).join(', ')}`);
      failed = true;
    }
    if (extraInZip.length > 0) {
      console.error(`FAIL ZIP has ${extraInZip.length} file(s) not present in the extracted folder: ${extraInZip.slice(0, 5).join(', ')}`);
      failed = true;
    }

    if (missingFromZip.length === 0 && extraInZip.length === 0 && exactDupes.length === 0) {
      const mismatched = [];
      for (const relFile of diskFiles) {
        const diskHash = createHash('sha256').update(fs.readFileSync(path.join(root, relFile))).digest('hex');
        let zipContent;
        try {
          zipContent = readEntryContent(buf, zipFileMap.get(relFile));
        } catch (err) {
          mismatched.push({ file: relFile, reason: `could not decode entry (${err.message})` });
          continue;
        }
        const zipHash = createHash('sha256').update(zipContent).digest('hex');
        if (diskHash !== zipHash) mismatched.push({ file: relFile, reason: 'content differs' });
      }
      if (mismatched.length > 0) {
        console.error(`FAIL ${mismatched.length} file(s) have the same name in ZIP and disk but different content (stale ZIP):`);
        for (const item of mismatched.slice(0, 10)) console.error(`  - ${item.file} (${item.reason})`);
        if (mismatched.length > 10) console.error(`  ... and ${mismatched.length - 10} more`);
        failed = true;
      }
    }
  }
}

if (warnings.length > 0) {
  console.error(`WARN ${warnings.length} note(s):`);
  for (const w of warnings) console.error(`  - ${w}`);
}

if (failed) process.exit(1);
const zipWholeHash = zipExists ? createHash('sha256').update(fs.readFileSync(expectedZip)).digest('hex') : 'n/a';
console.log(`PASS validate-package: inspected_zip=${expectedZip} sha256=${zipWholeHash} - root folder name is GENERAL_HARNESS; ZIP internals checked with a pure-Node ZIP reader (no external unzip dependency) - single root, no path traversal, no exact/case-insensitive duplicate entries, required files present, full file name parity AND per-file SHA-256 content match between ZIP and extracted folder.`);
