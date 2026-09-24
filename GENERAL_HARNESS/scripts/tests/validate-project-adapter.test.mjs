import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { inspectAdapter } from '../validate-project-adapter.mjs';

const cli = fileURLToPath(new URL('../validate-project-adapter.mjs', import.meta.url));
function fixture(t) {
  const temp = fs.realpathSync(os.tmpdir());
  const root = fs.mkdtempSync(path.join(temp, 'harness-adapter-'));
  t.after(() => {
    const resolved = fs.realpathSync(root);
    assert.equal(path.dirname(resolved), temp);
    assert.ok(path.basename(resolved).startsWith('harness-adapter-'));
    fs.rmSync(resolved, { recursive: true, force: true });
  });
  const put = (name, text) => {
    fs.mkdirSync(path.dirname(path.join(root, name)), { recursive: true });
    fs.writeFileSync(path.join(root, name), text);
  };
  const manifest = {
    schemaVersion: 1, adapterVersion: '1.0.0',
    harnessSource: { repository: 'https://example.com/harness', commit: 'a'.repeat(40) },
    documents: [{ id: 'requirements', path: 'docs/requirements.md', owner: 'Product' }, { id: 'ui', path: 'docs/ui.md', owner: 'Design' }],
    routes: [{ task: 'ui', documents: ['requirements', 'ui'] }], localChanges: [],
  };
  const save = () => put('PROJECT_HARNESS/manifest.json', JSON.stringify(manifest));
  const valid = () => {
    put('PROJECT_HARNESS/00.PROJECT_CONTEXT.md', '# Context\ndocs/requirements.md\ndocs/ui.md');
    put('docs/requirements.md', '# Requirements'); put('docs/ui.md', '# UI');
    put('GENERAL_HARNESS/00.HARNESS_RULES.md', '# Rules'); save();
  };
  return { root, put, manifest, save, valid, inspect: (options = {}) => inspectAdapter({ projectRoot: root, ...options }) };
}

test('absent optional adapter explicitly does not apply', t => {
  const f = fixture(t); const r = f.inspect({ strict: true });
  assert.equal(r.status, 'NOT_APPLICABLE'); assert.equal(r.exitCode, 0);
  assert.equal(f.inspect({ requireAdapter: true }).status, 'FAIL');
  assert.equal(f.inspect({ task: 'ui' }).status, 'FAIL');
});
test('legacy adapter warns, strict or requested route cannot pass', t => {
  const f = fixture(t); f.put('PROJECT_HARNESS/00.PROJECT_CONTEXT.md', '# Legacy');
  assert.equal(f.inspect().status, 'WARN'); assert.equal(f.inspect().exitCode, 0);
  assert.equal(f.inspect({ strict: true }).exitCode, 1);
  assert.equal(f.inspect({ task: 'ui' }).status, 'FAIL');
  assert.equal(f.inspect({ requireAdapter: true }).status, 'FAIL');
});
test('valid route preserves declared reading order and owner', t => {
  const f = fixture(t); f.valid(); f.manifest.routes[0].documents.reverse(); f.save();
  const r = f.inspect({ task: 'ui', strict: true });
  assert.equal(r.status, 'PASS'); assert.equal(r.exitCode, 0);
  assert.deepEqual(r.selectedDocuments.map(d => d.id), ['ui', 'requirements']);
  assert.equal(r.selectedDocuments[0].owner, 'Design');
  assert.deepEqual(f.inspect().selectedDocuments, []);
  assert.equal(f.inspect({ task: 'unknown' }).status, 'FAIL');
});
const badCases = {
  'unsupported schema': m => { m.schemaVersion = 2; },
  'missing version': m => { delete m.adapterVersion; },
  'short commit': m => { m.harnessSource.commit = 'abcdef'; },
  'credential URL': m => { m.harnessSource.repository = 'https://user:password@example.com/repo'; },
  'unknown key': m => { m.scripts = ['do-not-run']; },
  'missing owner': m => { m.documents[0].owner = ''; },
  'duplicate ID': m => { m.documents[1].id = 'requirements'; },
  'duplicate path ignoring case': m => { m.documents[1].path = 'DOCS/REQUIREMENTS.MD'; },
  'missing file': m => { m.documents[0].path = 'docs/absent.md'; },
  'path traversal': m => { m.documents[0].path = '../escape.md'; },
  'absolute path': m => { m.documents[0].path = 'C:/escape.md'; },
  'backslash path': m => { m.documents[0].path = 'docs\\requirements.md'; },
  'common product document': m => { m.documents[0].path = 'GENERAL_HARNESS/00.HARNESS_RULES.md'; },
  'unknown route document': m => { m.routes[0].documents = ['unknown']; },
  'duplicate route document': m => { m.routes[0].documents = ['ui', 'ui']; },
  'duplicate route': m => { m.routes.push(m.routes[0]); },
  'empty routes': m => { m.routes = []; },
  'local change outside common': m => { m.localChanges = [{ path: 'docs/ui.md', reason: 'wrong scope' }]; },
  'local change missing reason': m => { m.localChanges = [{ path: 'GENERAL_HARNESS/00.HARNESS_RULES.md', reason: '' }]; },
};
for (const [name, mutate] of Object.entries(badCases)) test(name, t => {
  const f = fixture(t); f.valid(); mutate(f.manifest); f.save();
  const r = f.inspect({ task: 'ui' }); assert.equal(r.status, 'FAIL'); assert.equal(r.exitCode, 1); assert.deepEqual(r.selectedDocuments, []);
});
test('local provenance declarations are returned without claiming authenticity', t => {
  const f = fixture(t); f.valid();
  f.manifest.localChanges = [{ path: 'GENERAL_HARNESS/00.HARNESS_RULES.md', reason: 'Local clarification' }]; f.save();
  const r = f.inspect(); assert.equal(r.status, 'PASS'); assert.deepEqual(r.localChanges, f.manifest.localChanges);
  assert.match(r.limitations, /Does not authenticate/);
});
test('malformed JSON and context without paths fail', t => {
  const f = fixture(t); f.valid(); f.put('PROJECT_HARNESS/manifest.json', '{');
  assert.equal(f.inspect().status, 'FAIL'); f.save();
  f.put('PROJECT_HARNESS/00.PROJECT_CONTEXT.md', '# Context'); assert.equal(f.inspect().status, 'FAIL');
});
test('symlinked adapter directory is rejected', t => {
  const f = fixture(t); fs.mkdirSync(path.join(f.root, 'target'));
  fs.symlinkSync(path.join(f.root, 'target'), path.join(f.root, 'PROJECT_HARNESS'), process.platform === 'win32' ? 'junction' : 'dir');
  assert.equal(f.inspect().status, 'FAIL');
});
test('CLI JSON, default root, invalid argument and read-only behavior', t => {
  const f = fixture(t); f.valid();
  const before = fs.readFileSync(path.join(f.root, 'PROJECT_HARNESS/manifest.json'), 'utf8');
  const run = (args, cwd = f.root) => spawnSync(process.execPath, [cli, ...args], { cwd, encoding: 'utf8' });
  const good = run(['--task', 'ui', '--json'], path.join(f.root, 'GENERAL_HARNESS'));
  assert.equal(good.status, 0); assert.equal(JSON.parse(good.stdout).selectedDocuments.length, 2);
  for (const args of [['--wat', '--json'], ['--task', '--json'], ['--task', 'ui', '--task', 'ui', '--json']]) {
    const bad = run(args); assert.equal(bad.status, 1); assert.equal(JSON.parse(bad.stdout).findings[0].code, 'CLI_USAGE');
  }
  assert.equal(fs.readFileSync(path.join(f.root, 'PROJECT_HARNESS/manifest.json'), 'utf8'), before);
});

test('adapter without context cannot pass or silently fall back', t => {
  const f = fixture(t); f.save(); assert.equal(f.inspect().status, 'FAIL');
});

test('CI strict CLI distinguishes absent, legacy and invalid adapter', t => {
  const f = fixture(t);
  const run = () => spawnSync(process.execPath, [cli, '--project-root', f.root, '--strict', '--json'], { encoding: 'utf8' });
  const absent = run(); assert.equal(absent.status, 0); assert.equal(JSON.parse(absent.stdout).status, 'NOT_APPLICABLE');
  f.put('PROJECT_HARNESS/00.PROJECT_CONTEXT.md', '# Legacy');
  const legacy = run(); assert.equal(legacy.status, 1); assert.equal(JSON.parse(legacy.stdout).status, 'WARN');
  f.valid(); f.manifest.routes[0].documents = ['unknown']; f.save();
  const invalid = run(); assert.equal(invalid.status, 1); assert.equal(JSON.parse(invalid.stdout).status, 'FAIL');
});
test('document directory junction cannot bypass local path check', t => {
  const f = fixture(t); f.valid();
  fs.symlinkSync(path.join(f.root, 'docs'), path.join(f.root, 'alias'), process.platform === 'win32' ? 'junction' : 'dir');
  f.manifest.documents[0].path = 'alias/requirements.md'; f.save();
  f.put('PROJECT_HARNESS/00.PROJECT_CONTEXT.md', '# Context\nalias/requirements.md\ndocs/ui.md');
  assert.equal(f.inspect().status, 'FAIL');
});
