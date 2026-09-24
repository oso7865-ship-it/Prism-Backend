#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";

const extensions = new Set([".vue", ".css", ".scss", ".sass", ".less", ".html", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx"]);
const ignoredDirectories = new Set([".git", "node_modules", "dist", "build", "coverage", ".nuxt", ".output"]);

const rules = [
  { id: "A11Y-01", level: "high", pattern: /outline\s*:\s*(?:0|none)\b/i, message: "포커스 윤곽 제거를 확인하세요. 대체 focus-visible이 없다면 접근성 실패입니다." },
  { id: "A11Y-02", level: "high", pattern: /<div\b[^>]*(?:@click|v-on:click)=/i, message: "클릭 가능한 div입니다. button/link 의미 요소와 키보드 동작을 확인하세요." },
  { id: "MOTION-01", level: "medium", pattern: /transition(?:-property)?\s*:\s*all\b|\btransition-all\b/i, message: "transition-all 대신 실제 변경 속성을 지정하세요." },
  { id: "MOTION-02", level: "medium", pattern: /transition(?:-property)?\s*:[^;]*(?:width|height|margin|padding|top|left)\b|@keyframes[^}]*\b(?:width|height|margin|padding|top|left)\s*:/i, message: "레이아웃 속성 애니메이션의 성능과 대안을 확인하세요." },
  { id: "RESP-01", level: "high", pattern: /\bwidth\s*:\s*100vw\b/i, message: "100vw가 데스크톱 스크롤바를 포함해 가로 넘침을 만들지 확인하세요." },
  { id: "VUE-01", level: "medium", pattern: /:key\s*=\s*["'](?:index|i)["']/i, message: "배열 index key는 삽입·정렬 시 상태와 전환을 깨뜨릴 수 있습니다." },
  { id: "VISUAL-01", level: "low", pattern: /background-clip\s*:\s*text|-webkit-background-clip\s*:\s*text/i, message: "gradient text가 제품·브랜드 의미 없이 사용됐는지 확인하세요." },
  { id: "VISUAL-02", level: "low", pattern: /grid-template-columns\s*:\s*repeat\(\s*3\s*,\s*(?:minmax\([^)]*\)|1fr)\s*\)/i, message: "동일 3열 구조가 실제 비교 목적에 맞는지 확인하세요." },
  { id: "VISUAL-03", level: "low", pattern: /min-height\s*:\s*100(?:d|s|l)?vh\b/i, message: "전체 높이 화면이 콘텐츠 목적 때문인지, 중앙 영웅 기본값인지 확인하세요." },
  { id: "VISUAL-04", level: "low", pattern: /(?:background|color)\s*:\s*#(?:000000|000|ffffff|fff)\b/i, message: "순수 흑백이 기존 디자인 시스템과 대비 목적에 맞는지 확인하세요." },
  { id: "COPY-01", level: "medium", pattern: /\b(?:John Doe|Jane Doe|Acme|Lorem ipsum)\b/i, message: "개발용 범용 문구가 운영 UI에 남아 있는지 확인하세요." },
  { id: "COPY-02", level: "medium", pattern: /(?:trusted by\s+[\d,]+|\+?\d+(?:\.\d+)?[x×]\s+(?:faster|better)|\d+만\s*명(?:이|의)?\s*선택)/i, message: "근거가 제공되지 않은 성과·신뢰 수치인지 확인하세요." }
];

function collect(target, files) {
  if (!fs.existsSync(target)) {
    console.error(`missing: ${target}`);
    return;
  }
  const stat = fs.statSync(target);
  if (stat.isFile()) {
    if (extensions.has(path.extname(target).toLowerCase())) files.push(target);
    return;
  }
  for (const entry of fs.readdirSync(target, { withFileTypes: true })) {
    if (entry.isDirectory() && ignoredDirectories.has(entry.name)) continue;
    collect(path.join(target, entry.name), files);
  }
}

const targets = process.argv.slice(2);
if (targets.length === 0) {
  console.error("usage: node ui-pattern-audit.mjs <file-or-directory...>");
  process.exit(2);
}

const files = [];
for (const target of targets) collect(path.resolve(target), files);

const findings = [];
for (const file of [...new Set(files)].sort()) {
  const lines = fs.readFileSync(file, "utf8").split(/\r?\n/);
  lines.forEach((line, index) => {
    for (const rule of rules) {
      rule.pattern.lastIndex = 0;
      if (rule.pattern.test(line)) {
        findings.push({ file, line: index + 1, ...rule });
      }
    }
  });
}

for (const finding of findings) {
  console.log(`${finding.level.toUpperCase()} ${finding.id} ${finding.file}:${finding.line}`);
  console.log(`  ${finding.message}`);
}

const counts = findings.reduce((acc, item) => {
  acc[item.level] = (acc[item.level] ?? 0) + 1;
  return acc;
}, {});

console.log(`scanned ${files.length} file(s) · ${findings.length} finding(s) · high ${counts.high ?? 0} · medium ${counts.medium ?? 0} · low ${counts.low ?? 0}`);
