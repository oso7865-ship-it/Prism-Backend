import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

export function safePath(root, relative) {
  if (typeof relative !== 'string' || !relative || relative.includes('\\') ||
      relative.includes(':') || relative.split('/').some(p => !p || p === '.' || p === '..' || p === '.git')) {
    throw new Error('Unsafe documentation path');
  }
  const absoluteRoot = fs.realpathSync(root);
  const target = path.resolve(absoluteRoot, relative);
  if (!target.startsWith(absoluteRoot + path.sep)) throw new Error('Path escapes repository');
  let cursor = absoluteRoot;
  for (const part of relative.split('/')) {
    cursor = path.join(cursor, part);
    try {
      if (fs.lstatSync(cursor).isSymbolicLink()) throw new Error('Symlink in documentation path');
    } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
  return target;
}

export function planRestore(sourceRoot, destinationRoot, entries, repository) {
  const planned = [];
  const seen = new Set();
  for (const entry of entries.filter(e => e.repository === repository)) {
    if (seen.has(entry.path)) throw new Error('Duplicate documentation path');
    seen.add(entry.path);
    const source = safePath(sourceRoot, `records/${repository}/${entry.path}`);
    const destination = safePath(destinationRoot, entry.path);
    const bytes = fs.readFileSync(source);
    if (crypto.createHash('sha256').update(bytes).digest('hex') !== entry.sha256) {
      throw new Error(`Documentation checksum mismatch: ${entry.path}`);
    }
    if (fs.existsSync(destination)) {
      if (!fs.readFileSync(destination).equals(bytes)) throw new Error(`Preserve local edits: ${entry.path}`);
    } else planned.push({ destination, bytes });
  }
  if (!seen.size) throw new Error('No documents for this repository');
  return planned;
}

function main() {
  const destination = process.cwd();
  const config = JSON.parse(fs.readFileSync(path.join(destination, 'architecture.json'), 'utf8'));
  const source = process.argv[2];
  if (!source) throw new Error('Usage: node scripts/restore-docs.mjs <Prism-Architecture clone path>');
  if (!/^[a-f0-9]{40}$/.test(config.revision)) throw new Error('Pinned architecture revision required');
  const repository = config.logical_path_prefix?.replace(/\/$/, '');
  if (!['backend', 'frontend'].includes(repository)) throw new Error('Unknown repository');
  const sourceRoot = fs.realpathSync(source);
  // Read the manifest from the pinned Git object, then verify every source byte before writing.
  const manifest = JSON.parse(execFileSync('git', [
    '-c', `safe.directory=${sourceRoot.replaceAll('\\', '/')}`, '-C', sourceRoot,
    'show', `${config.revision}:records/manifest.json`,
  ], { encoding: 'utf8', windowsHide: true }));
  if (manifest.schemaVersion !== 1) throw new Error('Unsupported documentation manifest');
  const planned = planRestore(sourceRoot, destination, manifest.files, repository);
  if (!process.argv.includes('--check')) {
    for (const item of planned) {
      fs.mkdirSync(path.dirname(item.destination), { recursive: true });
      fs.writeFileSync(item.destination, item.bytes, { flag: 'wx' });
    }
  }
  console.log(`PASS: ${planned.length} missing documentation files ${process.argv.includes('--check') ? 'verified' : 'restored'}; existing files preserved`);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(); } catch (error) { console.error(error.message); process.exitCode = 1; }
}
