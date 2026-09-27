import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { planRestore, safePath } from './restore-docs.mjs';

test('restore rejects traversal, absolute and Git metadata destinations', () => {
  for (const name of ['../outside', '/outside', 'C:/outside', '.git/config', 'docs/../../key', 'docs\\file']) {
    assert.throws(() => safePath(process.cwd(), name));
  }
});

test('restore verifies every source before writing and preserves local edits', () => {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'prism-doc-test-'));
  const source = path.join(root, 'source');
  const destination = path.join(root, 'destination');
  fs.mkdirSync(path.join(source, 'records', 'backend', 'docs'), { recursive: true });
  fs.mkdirSync(destination);
  const bytes = Buffer.from('saved record');
  fs.writeFileSync(path.join(source, 'records', 'backend', 'docs', 'guide.md'), bytes);
  const entry = { repository: 'backend', path: 'docs/guide.md', sha256: crypto.createHash('sha256').update(bytes).digest('hex') };
  assert.equal(planRestore(source, destination, [entry], 'backend').length, 1);
  assert.equal(fs.existsSync(path.join(destination, 'docs')), false);
  assert.throws(() => planRestore(source, destination, [{ ...entry, sha256: 'wrong' }], 'backend'));
  fs.mkdirSync(path.join(destination, 'docs'));
  fs.writeFileSync(path.join(destination, 'docs', 'guide.md'), 'local edit');
  assert.throws(() => planRestore(source, destination, [entry], 'backend'), /Preserve local edits/);
  fs.writeFileSync(path.join(destination, 'docs', 'guide.md'), bytes);
  assert.equal(planRestore(source, destination, [entry], 'backend').length, 0);
  // Small OS temporary test artifacts are retained; no recursive filesystem deletion.
});
