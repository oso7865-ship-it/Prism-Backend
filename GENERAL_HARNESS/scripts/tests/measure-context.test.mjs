import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { measureContext } from '../measure-context.mjs';

test('measures UTF-8 and CRLF without altering input, deduplicates paths', t => {
  const temp = fs.realpathSync(os.tmpdir());
  const root = fs.mkdtempSync(path.join(temp, 'harness-measure-'));
  t.after(() => {
    const resolved = fs.realpathSync(root);
    assert.equal(path.dirname(resolved), temp);
    assert.ok(path.basename(resolved).startsWith('harness-measure-'));
    fs.rmSync(resolved, { recursive: true, force: true });
  });
  const original = Buffer.from('한글\r\nabc');
  fs.writeFileSync(path.join(root, 'text.md'), original);
  const result = measureContext(root, ['text.md', 'text.md']);
  assert.equal(result.files.length, 1);
  assert.equal(result.files[0].rawBytes, 11);
  assert.equal(result.totalNormalizedUtf8Bytes, 10);
  assert.deepEqual(fs.readFileSync(path.join(root, 'text.md')), original);
  assert.match(result.metric, /not tokens or money/);
  assert.throws(() => measureContext(root, []));
  assert.throws(() => measureContext(root, ['../outside.md']));
  assert.throws(() => measureContext(root, ['missing.md']));
  fs.writeFileSync(path.join(root, 'invalid.bin'), Buffer.from([0xff]));
  assert.throws(() => measureContext(root, ['invalid.bin']));
});
