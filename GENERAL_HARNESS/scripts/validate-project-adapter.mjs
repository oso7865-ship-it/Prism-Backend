#!/usr/bin/env node
// Optional project adapter, contract version 1. Read-only; never runs project code.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

export function inspectAdapter(options = {}) {
  const findings = [], documents = [], routes = [], localChanges = [];
  let provenance = null, adapterVersion = null, status = 'PASS';
  const add = (severity, code, message) => findings.push({ severity, code, message });
  try {
    const root = fs.realpathSync(path.resolve(options.projectRoot ?? process.cwd()));
    if (!fs.statSync(root).isDirectory()) throw new Error('project root must be a directory');
    function exists(file) {
      try { fs.lstatSync(file); return true; } catch (error) { if (error.code === 'ENOENT') return false; throw error; }
    }
    function local(relative, directory = false) {
      if (typeof relative !== 'string' || !relative || relative.includes('\\') || path.isAbsolute(relative)
        || /^[a-z]+:/i.test(relative) || relative.split('/').some(part => !part || part === '..' || part === '.')) throw new Error('use a project-relative path without traversal');
      let current = root;
      for (const part of relative.split('/')) {
        current = path.join(current, part);
        if (fs.lstatSync(current).isSymbolicLink()) throw new Error('symbolic links are not supported');
      }
      const stat = fs.statSync(current);
      if (!(directory ? stat.isDirectory() : stat.isFile())) throw new Error('path has the wrong file type');
      return current;
    }
    const folder = path.join(root, 'PROJECT_HARNESS');
    if (!exists(folder)) {
      if (options.requireAdapter || options.task) add('FAIL', 'ADAPTER_REQUIRED', 'Requested project adapter is absent.');
      else status = 'NOT_APPLICABLE';
    } else {
      local('PROJECT_HARNESS', true);
      const contextPath = local('PROJECT_HARNESS/00.PROJECT_CONTEXT.md');
      const context = fs.readFileSync(contextPath, 'utf8').replace(/^\uFEFF/, '');
      if (!/^#\s+\S/m.test(context)) throw new Error('project context needs a title');
      if (!exists(path.join(folder, 'manifest.json'))) {
        add(options.requireAdapter || options.task ? 'FAIL' : 'WARN', 'LEGACY_ADAPTER', 'Existing context has no versioned manifest; inspect manually before migration.');
      } else {
        const manifest = JSON.parse(fs.readFileSync(local('PROJECT_HARNESS/manifest.json'), 'utf8').replace(/^\uFEFF/, ''));
        function keys(value, allowed) {
          if (!value || typeof value !== 'object' || Array.isArray(value) || Object.keys(value).some(k => !allowed.includes(k))) throw new Error('invalid object or unknown manifest key');
        }
        const text = value => typeof value === 'string' && value.trim().length > 0;
        keys(manifest, ['schemaVersion', 'adapterVersion', 'harnessSource', 'documents', 'routes', 'localChanges']);
        if (manifest.schemaVersion !== 1 || !/^\d+\.\d+\.\d+$/.test(manifest.adapterVersion ?? '')) throw new Error('unsupported schema or adapter version');
        adapterVersion = manifest.adapterVersion;
        keys(manifest.harnessSource, ['repository', 'commit']);
        const source = new URL(manifest.harnessSource.repository);
        if (source.protocol !== 'https:' || source.username || source.password || source.search || source.hash
          || !/^(?:[a-f0-9]{40}|[a-f0-9]{64})$/i.test(manifest.harnessSource.commit ?? '')) throw new Error('source requires an HTTPS repository and full commit ID');
        provenance = manifest.harnessSource;
        if (!Array.isArray(manifest.documents) || !manifest.documents.length || !Array.isArray(manifest.routes) || !manifest.routes.length || !Array.isArray(manifest.localChanges)) throw new Error('documents/routes must be non-empty arrays; localChanges must be an array');
        const ids = new Set(), paths = new Set(), tasks = new Set(), changes = new Set();
        for (const doc of manifest.documents) {
          keys(doc, ['id', 'path', 'owner']);
          if (!/^[a-z][a-z0-9-]*$/.test(doc.id ?? '') || !text(doc.owner) || typeof doc.path !== 'string') throw new Error('invalid document ID, owner or path');
          const key = doc.path.toLowerCase();
          if (ids.has(doc.id) || paths.has(key)) throw new Error('duplicate document ID/path');
          if (/^GENERAL_HARNESS\//i.test(doc.path) || !/\.md$/i.test(doc.path)) throw new Error('product documents must be Markdown outside GENERAL_HARNESS');
          local(doc.path);
          if (!context.includes(doc.path)) throw new Error(`context does not reference document ${doc.id}`);
          ids.add(doc.id); paths.add(key); documents.push(doc);
        }
        for (const route of manifest.routes) {
          keys(route, ['task', 'documents']);
          if (!text(route.task) || tasks.has(route.task) || !Array.isArray(route.documents) || !route.documents.length
            || new Set(route.documents).size !== route.documents.length || route.documents.some(id => !ids.has(id))) throw new Error('invalid task route or unknown/duplicate document ID');
          tasks.add(route.task); routes.push(route);
        }
        for (const change of manifest.localChanges) {
          keys(change, ['path', 'reason']);
          if (!text(change.reason) || typeof change.path !== 'string' || !change.path.startsWith('GENERAL_HARNESS/') || changes.has(change.path.toLowerCase())) throw new Error('local changes need a unique common-harness path and reason');
          local(change.path); changes.add(change.path.toLowerCase()); localChanges.push(change);
        }
        if (options.task && !tasks.has(options.task)) add('FAIL', 'TASK_UNKNOWN', 'Requested task is not declared; do not guess a route.');
      }
    }
  } catch (error) { add('FAIL', 'ADAPTER_INVALID', error.code ?? error.message); }
  if (findings.some(f => f.severity === 'FAIL')) status = 'FAIL';
  else if (findings.length) status = 'WARN';
  const chosen = routes.find(route => route.task === options.task);
  return {
    schemaVersion: 1, status, exitCode: status === 'FAIL' || (status === 'WARN' && options.strict) ? 1 : 0,
    adapterVersion, provenance, localChanges, documentCount: documents.length, routes,
    selectedDocuments: status === 'PASS' && chosen ? chosen.documents.map(id => documents.find(doc => doc.id === id)) : [], findings,
    limitations: 'Validates declared structure, local paths and routes only. Does not authenticate upstream commits, detect unlisted local changes, judge document meaning, or execute project scripts. No adapter means explicit NOT_APPLICABLE, not an adapter PASS.',
  };
}

export function runAdapterCli(args = process.argv.slice(2)) {
  const options = {};
  try {
    for (let i = 0; i < args.length; i++) {
      const arg = args[i];
      if (['--json', '--strict', '--require-adapter'].includes(arg)) options[arg === '--require-adapter' ? 'requireAdapter' : arg.slice(2)] = true;
      else if (['--project-root', '--task'].includes(arg) && args[i + 1] && !args[i + 1].startsWith('--')) {
        const key = arg === '--task' ? 'task' : 'projectRoot';
        if (options[key] !== undefined) throw new Error('duplicate option');
        options[key] = args[++i];
      } else throw new Error('unknown option or missing value');
    }
    if (!options.projectRoot) options.projectRoot = path.basename(process.cwd()) === 'GENERAL_HARNESS' ? path.dirname(process.cwd()) : process.cwd();
    const result = inspectAdapter(options);
    if (options.json) console.log(JSON.stringify(result, null, 2));
    else {
      console.log(`${result.status} validate-project-adapter: documents=${result.documentCount}, exit=${result.exitCode}`);
      for (const finding of result.findings) console.log(`${finding.severity} ${finding.code}: ${finding.message}`);
      for (const doc of result.selectedDocuments) console.log(`READ ${doc.path} (owner: ${doc.owner})`);
      console.log(result.limitations);
    }
    return result.exitCode;
  } catch (error) {
    const result = { status: 'FAIL', exitCode: 1, findings: [{ severity: 'FAIL', code: 'CLI_USAGE', message: error.message }] };
    console.log(args.includes('--json') ? JSON.stringify(result) : `FAIL CLI_USAGE: ${error.message}`);
    return 1;
  }
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) process.exitCode = runAdapterCli();
