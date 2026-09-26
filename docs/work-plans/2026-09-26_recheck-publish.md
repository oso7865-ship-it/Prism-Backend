# 재평가·Windows 진단·게시 작업 계약

사용자는 품질 재평가, Windows 원인 조사, 문서 정리·커밋·푸시·CI 확인1~3단계를 모두 승인했다. backend/frontend dev, architecture main. git-workflow/terminal-ops/troubleshooting-report 적용. 기존 코드·문서·검증 증거를 검토 후 게시하며 비밀값/로컬 환경/캐시 제외. 하네스 원본 동기화와 공개 서비스 배포, 게임/보안 프로그램 중지·변경 제외.

- [x] 수정 버전 rh1-3b9b53482a3791ef로 합성7사례 각1회 유료 재평가, 자동 재시도0: 자동6/7 PASS, 문맥 부족 실패 유지
- [x] Windows native 예외의 모듈/위치 확인: npggNT64.des+0x2769, nProtect GameGuard. 외부 모듈 동작 근본 수정/제거는 범위 밖
- [x] 게시 전 기존 문서의 현재/과거 상태 구분, Report 형식 정정, migration 구문 lint 수정
- [ ] 아키텍처 문서·도구 검증 후 main 게시
- [ ] backend/frontend architecture revision 갱신, local 빌드·테스트·secret/Git 제외 검수
- [ ] dev 커밋·푸시 및 원격 CI 확인
- [ ] 관측된 Git/CI 상태와 남은 한계 기록
