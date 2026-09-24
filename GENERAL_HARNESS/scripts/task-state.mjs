#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { createHash } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

export const hash = value => createHash('sha256').update(value).digest('hex');
export function localFile(root, relative) {
  if (!relative || path.isAbsolute(relative) || /[:\\]/.test(relative)
    || relative.split('/').some(p => !p || p === '.' || p === '..')) throw new Error('invalid local path');
  let current = root;
  for (const part of relative.split('/')) {
    current = path.join(current, part);
    if (fs.lstatSync(current).isSymbolicLink()) throw new Error('symlink unsupported');
  }
  if (!fs.statSync(current).isFile()) throw new Error('not a file');
  return current;
}

export function collectState(root) {
  root = fs.realpathSync.native(root);
  const issues = [], files = [];
  const environment = { node: process.version, platform: process.platform, arch: process.arch };
  const unknowns = ['Remote branch freshness and remote CI', 'Ignored files, environment variable values, installed dependency contents and external services', 'Concurrent edits during collection; snapshot is not atomic'];
  let head = null, branch = null, status = null, indexHash = null;
  const git = args => execFileSync('git', args, { cwd: root, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'], maxBuffer: 32 * 1024 * 1024 });
  try {
    // Windows Git and Node may preserve different casing of the same path.
    // Native realpath also expands Windows 8.3 aliases used by runner temp paths.
    if (path.relative(root, fs.realpathSync.native(git(['rev-parse', '--show-toplevel']).trim())) !== '') {
      const error = new Error('run at repository root');
      error.code = 'NOT_REPOSITORY_ROOT';
      throw error;
    }
    head = git(['rev-parse', 'HEAD']).trim();
    branch = git(['rev-parse', '--abbrev-ref', 'HEAD']).trim();
    status = git(['status', '--porcelain=v1', '-z', '--untracked-files=all']);
    indexHash = hash(git(['ls-files', '--stage', '-z']));
    const names = [...new Set(git(['ls-files', '--cached', '--others', '--exclude-standard', '-z']).split('\0').filter(Boolean))].sort();
    for (const name of names) {
      try { files.push({ path: name, sha256: hash(fs.readFileSync(localFile(root, name))) }); }
      catch (error) {
        // Missing tracked files are observable deletions, not a successful file read.
        if (error.code === 'ENOENT') files.push({ path: name, state: 'missing' });
        else issues.push({ path: name, code: error.code ?? error.message });
      }
    }
  } catch (error) { issues.push({ code: 'GIT_STATE_UNAVAILABLE', message: error.code ?? 'Repository root or Git query failed' }); }
  const payload = { head, branch, status, indexHash, environment, files };
  return { schemaVersion: 1, observedAt: new Date().toISOString(), complete: issues.length === 0,
    fingerprint: issues.length ? null : hash(JSON.stringify(payload)), ...payload, issues, unknowns };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const args = process.argv.slice(2);
    if (args.length > 1 || (args.length === 1 && args[0] !== '--json')) throw new Error('use --json or no arguments');
    const state = collectState(process.cwd());
    if (args[0] === '--json') console.log(JSON.stringify(state, null, 2));
    else {
      console.log(`STATE ${state.complete ? 'COLLECTED' : 'INCOMPLETE'} branch=${state.branch} head=${state.head} files=${state.files.length} sha256=${state.fingerprint}`);
      for (const issue of state.issues) console.log(`ISSUE ${JSON.stringify(issue)}`);
      for (const unknown of state.unknowns) console.log(`UNKNOWN ${unknown}`);
    }
    process.exitCode = state.complete ? 0 : 1;
  } catch (error) { console.error(`FAIL task-state: ${error.message}`); process.exitCode = 1; }
}
