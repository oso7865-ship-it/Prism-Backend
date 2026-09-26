# AI 검토 범위 설명 설계·작업 계약

## 목표와 범위

사용자의 PRism 다음 개발 지시에 따라 현재 AI 리뷰의 검토 범위를 설명한다. backend/frontend dev, architecture main. 기존 UI/UX Design·Vue UI Polish 지침과 Security Gate를 적용한다. 접근 권한과 전송 한도는 바꾸지 않는다. DB schema 변경·기존 결과 수정·추가 유료 호출은 없다.

## 설계

- 성공 결과 result.coverage에 서버가 만든 파일 ID→경로/제공 줄 수, 제외 파일→정제된 사유 코드를 보관한다. LLM이 이 metadata를 만들거나 변경하지 못한다.
- 제외 사유: 잘못된 경로, 미지원 언어, patch 없음, 제외 경로, 비밀 의심, patch 크기, 파일 개수, 전체 입력 크기, HEAD 줄 없음. 비밀 내용·원문 patch는 기록하지 않는다. 잘못된/비밀 패턴 경로는 이름도 저장하지 않는다.
- GitHub 첫100개 뒤 파일은 별도 미취득 수로 표시한다. total changed_files가 확인되지 않으면 unknown을 표시한다. 미취득을 검토/제외 상세로 위장하지 않는다.
- 결과 JSON에 optional coverage를 추가한다. 과거 결과는 당시 상세 기록 없음 안내만 보여 주며 현재 GitHub에서 역추정/덮어쓰기하지 않는다. 실패 결과의 상세 목록 저장은 이번 범위 밖이다.
- 완료 화면의 파일 수 아래 접기/펼치기: 검토 파일(f1·경로·제공 줄 수·고정 HEAD 링크), 제외 파일(경로·사유), 미취득 안내. 기본 접힘, 기존 파란색 토큰과 native details/summary 사용. 긴 경로는 줄바꿈, 목록 단일 열, 키보드 지원. 토큰/리뷰 본문과 구분한다.
- 테스트: provider payload에 경로/coverage 미포함, 제외 사유/수 정합성, 비밀 미저장, schema 결과에 metadata 추가, 기존 결과/새 결과 Vue SSR 렌더링, 악성 텍스트 escaping, 기존 통합 테스트/타입/빌드.

## 체크리스트

- [x] 현황 조사·설계·권한/비밀 경계 사전 검토
- [x] 서버 metadata 수집·응답
- [x] 프런트 검토 범위·기존 이력 안내
- [x] 테스트·타입·빌드
- [x] 문서·리포트·실행 반영
