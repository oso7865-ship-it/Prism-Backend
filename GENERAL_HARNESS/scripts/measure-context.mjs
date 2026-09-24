#!/usr/bin/env node
// Observes explicitly supplied local files. Does not select reading routes.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { localFile } from './task-state.mjs';

export function measureContext(root, names) {
  if (!names.length) throw new Error('provide repository-relative file paths');
  const files = [...new Set(names)].map(name => {
    const data = fs.readFileSync(localFile(root, name));
    const text = new TextDecoder('utf-8', { fatal: true }).decode(data).replaceAll('\r\n', '\n');
    return { path: name, rawBytes: data.length, normalizedUtf8Bytes: Buffer.byteLength(text) };
  });
  return { schemaVersion: 1, metric: 'UTF-8 bytes, not tokens or money', files,
    totalNormalizedUtf8Bytes: files.reduce((sum, f) => sum + f.normalizedUtf8Bytes, 0),
    limitations: ['File size only; does not measure actual reads, repeated calls, cached tokens, output tokens, retries or billed cost.',
      'Selected paths are supplied by the caller and do not replace required reading rules.'] };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { console.log(JSON.stringify(measureContext(process.cwd(), process.argv.slice(2)), null, 2)); }
  catch (error) { console.error(`FAIL measure-context: ${error.message}`); process.exitCode = 1; }
}
