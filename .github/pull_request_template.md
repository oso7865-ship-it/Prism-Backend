# PR 요약

<!-- 무엇을, 왜 바꾸는지 1~3문장 -->

## 작업 정보

- 작업 범위: S / M / L / XL
- 위험도: 일반 / 구조 / DB / 보안 / 결제 / 파일 손상 가능 / 외부 실행 / 환경 변경(비파괴적)
- 적용 Skill:
- 적용 Gate/Checklist:

## 검증

- [ ] CI(harness-ci)가 PASS했다 — 검증 스크립트 7종
- [ ] 위험도가 "일반"이 아니면 `GENERAL_HARNESS/04.GATEGUARD.md` §6-1 기준 확인을 거쳤다
- [ ] 코드 변경이면 빌드·테스트·실측(browser-qa) 결과를 아래에 기록했다

<!-- 검증 결과: 실행한 명령과 결과를 재현 가능하게 -->

## Report

- Report 경로: <!-- GENERAL_HARNESS/reports/... 또는 "해당 없음(단일 문서 S 작업 등 사유)" -->
- [ ] 여러 파일 수정·Gate 적용·WARN/FAIL이 있었다면 Report를 작성하고 `reports/_LATEST.md`를 갱신했다

## 미해결 항목

<!-- 없으면 "없음" -->
