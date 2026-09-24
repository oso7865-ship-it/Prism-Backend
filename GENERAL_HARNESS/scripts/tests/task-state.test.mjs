import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { collectState, localFile } from '../task-state.mjs';

function fixture(t) {
  const temp = fs.realpathSync(os.tmpdir());
  const root = fs.mkdtempSync(path.join(temp, 'harness-state-'));
  t.after(() => {
    const resolved = fs.realpathSync(root);
    assert.equal(path.dirname(resolved), temp); assert.ok(path.basename(resolved).startsWith('harness-state-'));
    fs.rmSync(resolved, { recursive: true, force: true });
  });
  const git = args => execFileSync('git', args, { cwd: root, stdio: 'pipe' });
  git(['init', '--quiet']);
  fs.writeFileSync(path.join(root, '.gitignore'), 'receipt/\n');
  fs.writeFileSync(path.join(root, 'doc.md'), '# Doc');
  git(['add', '.']);
  git(['-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'fixture']);
  fs.mkdirSync(path.join(root, 'receipt'));
  return { root, git };
}
test('read-only snapshot includes unstaged/untracked files and explicit unknowns', t => {
  const { root, git } = fixture(t);
  fs.writeFileSync(path.join(root, 'new.md'), 'new');
  const before = git(['status', '--porcelain']).toString();
  const a = collectState(root), b = collectState(root);
  assert.equal(a.complete, true, JSON.stringify(a.issues)); assert.equal(a.fingerprint, b.fingerprint);
  if (process.platform === 'win32') {
    const alternate = collectState(root.toUpperCase());
    assert.equal(alternate.complete, true, JSON.stringify(alternate.issues));
    assert.equal(alternate.fingerprint, a.fingerprint);
  }
  assert.ok(a.files.some(f => f.path === 'new.md'));
  assert.ok(a.unknowns.some(s => s.includes('environment variable')));
  assert.equal(git(['status', '--porcelain']).toString(), before);
});
test('source, dependency lock, deletion and staging invalidate fingerprint', t => {
  const { root, git } = fixture(t); let previous = collectState(root).fingerprint;
  for (const action of [
    () => fs.appendFileSync(path.join(root, 'doc.md'), ' edit'),
    () => fs.writeFileSync(path.join(root, 'package-lock.json'), '{}'),
    () => git(['add', 'doc.md']),
    () => fs.unlinkSync(path.join(root, 'doc.md')),
  ]) { action(); const s = collectState(root); assert.equal(s.complete, true); assert.notEqual(s.fingerprint, previous); previous = s.fingerprint; }
});
test('symlinks and non-repository roots explicitly report incomplete', t => {
  const { root } = fixture(t);
  fs.mkdirSync(path.join(root, 'folder')); fs.symlinkSync(path.join(root, 'folder'), path.join(root, 'alias'), process.platform === 'win32' ? 'junction' : 'dir');
  fs.writeFileSync(path.join(root, 'folder/doc.md'), '# Doc');
  assert.throws(() => localFile(root, 'alias/doc.md'));
  // Git does not always list empty junctions; a tracked symlink entry must not be silently read.
  assert.equal(collectState(path.join(root, 'folder')).complete, false);
  assert.throws(() => localFile(root, '../escape.json'));
  assert.throws(() => localFile(root, 'folder/../doc.md'));
});
