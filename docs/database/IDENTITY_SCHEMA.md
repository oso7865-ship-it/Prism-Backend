# 인증·팀 테이블 6개


> 구현 입력 snapshot, 2026-09-25. 원본: Prism-Architecture / docs/architecture/contracts/schema/IDENTITY.md.
> 게시된 원본 커밋: 665a2003f43c851d4fa3bcd9569059a4533f5409.
> 원본 SHA256 (Git LF): cd85b4d74d92ccb08b54ddd130956c574574ccaf2c9c442ec74fabc1c313789f
> 이 사본은 독립 clone에서 구현 기준을 확인하기 위한 기록이다. 새 정책을 여기서 독립 변경하지 않는다.

모든 테이블에 공통 id UUID PK(Python uuid4 기본값), created_at timestamptz NOT NULL DEFAULT now()가 있다. H256은 varchar(64)와 소문자 16진수 64자리 CHECK다. 공통 잠금·삭제·관계 규칙은 [COMMON_SCHEMA](COMMON_SCHEMA.md)를 따른다.


> 원본 문서 ID: `DB-IDENTITY` · 소유: `data-contracts` · 기준: `2026-09-25`

> 읽는 때: User·Auth·Workspace 컬럼과 인덱스를 구현할 때



공통 타입·물리 FK 없는 관계 규칙 (아키텍처 원본 참조)을 함께 적용한다. 각 표에 공통 id/created_at을 더한다. 업무 정책은 User (아키텍처 원본 참조), Auth (아키텍처 원본 참조), Workspace (아키텍처 원본 참조)가 소유한다.



<a id="table-users"></a>



## users



| 컬럼 | 타입 | NULL | 기본값·의미 |

|---|---|---|---|

| github_user_id | bigint | N | 외부 사용자 ID, 양수 |

| login | varchar(255) | N | 현재 GitHub login, 계정 키 아님 |

| display_name | varchar(255) | Y | 표시 이름 |

| avatar_url | text | Y | 표시 전용, 서버 대리 취득 금지 |

| status | varchar(16) | N | ACTIVE 기본, ACTIVE/INACTIVE CHECK |

| updated_at | timestamptz | N | now() |



UQ(github_user_id). 프로필 upsert는 외부 숫자 ID 충돌을 처리한다. 이메일·GitHub token 컬럼은 없다. 비활성화는 세션과 실행 권한을 차단하되 감사 관계를 위해 행은 유지한다.



<a id="table-login_attempts"></a>



## login_attempts



| 컬럼 | 타입 | NULL | 기본값·의미 |

|---|---|---|---|

| purpose | varchar(24) | N | OAUTH_LOGIN/GITHUB_INSTALL CHECK |

| state_hash | H256 | N | 일회성 난수 state의 해시 |

| browser_binding_hash | H256 | N | 별도 브라우저 바인딩 쿠키의 해시 |

| user_id / workspace_id | uuid | Y | 설치 흐름의 요청자/팀 논리 참조 |

| return_path | varchar(1024) | N | 서버 allowlist로 검증한 앱 내 상대 경로 |

| expires_at | timestamptz | N | 생성 시 만료 시각 제공 |

| consumed_at | timestamptz | Y | 원자적 소비 시각 |



UQ(state_hash), IDX(expires_at). CHECK expires_at > created_at. OAUTH_LOGIN이면 두 참조 모두 NULL, GITHUB_INSTALL이면 둘 다 NOT NULL인 CHECK를 둔다. state와 브라우저 바인딩을 확인하고 consumed_at IS NULL 및 만료 전 조건으로 한 번만 소비한다. 만료 여부를 now() 기반 CHECK/partial index로 구현하지 않는다. 설치 완료 때도 현재 사용자·Workspace 권한을 다시 확인한다. code/token 원문은 저장하지 않는다.



설치 연결용 state도 이 만료 레코드를 사용하여 별도 18번째 테이블을 만들지 않는다. 인증·설치의 사용 목적은 엄격히 구분한다. 만료 시간은 로그인/설치 handler의 설정이며 저장한 expires_at이 판단 기준이다.



<a id="table-refresh_sessions"></a>



## refresh_sessions



| 컬럼 | 타입 | NULL | 기본값·의미 |

|---|---|---|---|

| user_id | uuid | N | users 논리 참조 |

| token_hash | H256 | N | Refresh 원문 대신 해시 |

| family_id | uuid | N | 최초 로그인 세션 계열 ID |

| expires_at | timestamptz | N | 계열의 절대 만료 시각 |

| rotated_at | timestamptz | Y | 성공적으로 교체된 시각 |

| replaced_by_id | uuid | Y | 다음 Refresh 행 논리 참조 |

| revoked_at | timestamptz | Y | 명시 철회/재사용 탐지 |

| revoke_reason | varchar(64) | Y | 공개 사유 코드 |



UQ(token_hash), UQ(replaced_by_id) WHERE replaced_by_id IS NOT NULL. IDX(user_id,family_id), IDX(expires_at). CHECK expires_at > created_at, rotated_at과 replaced_by_id의 NULL 여부가 같음, replaced_by_id IS NULL OR replaced_by_id <> id, revoked_at/revoke_reason의 NULL 여부가 같음.



user 행을 FOR UPDATE로 잠근 뒤 유효한 이전 token을 조건부 소비하고 새 행 insert·연결을 같은 트랜잭션에 수행한다. 같은 user/family·같은 절대 만료를 새 행에 복사한다. Auth (아키텍처 원본 참조)의 7일 기본값은 최초 발급 기준이며 rotation으로 연장하지 않는다. 이미 rotated인 토큰 재사용은 해당 family 전체 철회다. 기존 행을 즉시 삭제하면 재사용을 판별할 수 없으므로 계열 만료 및 보관 정책까지 유지한다.



<a id="table-workspaces"></a>



## workspaces



| 컬럼 | 타입 | NULL | 기본값·의미 |

|---|---|---|---|

| name | varchar(100) | N | 표시용 팀 이름, 전역 UNIQUE 아님 |

| status | varchar(16) | N | ACTIVE 기본, ACTIVE/INACTIVE CHECK |

| created_by | uuid | N | 생성자 users 논리 참조, 현재 OWNER 의미 아님 |

| updated_at | timestamptz | N | now() |



IDX(created_by,created_at DESC,id DESC). CHECK btrim(name) <> ''. OWNER는 workspace_members에서만 결정한다. 생성자 컬럼과 소유권 이전을 연동해 덮어쓰지 않는다. INACTIVE는 모든 새 업무 쓰기를 차단하며 cleanup만 허용한다.



<a id="table-workspace_members"></a>



## workspace_members



| 컬럼 | 타입 | NULL | 기본값·의미 |

|---|---|---|---|

| workspace_id / user_id | uuid | N | workspaces/users 논리 참조 |

| role | varchar(16) | N | OWNER/ADMIN/MEMBER CHECK |

| status | varchar(16) | N | ACTIVE 기본, ACTIVE/LEFT/REMOVED CHECK |

| joined_at | timestamptz | N | now(), 최근 가입 시각 |

| ended_at | timestamptz | Y | 탈퇴/제거 시각 |

| updated_at | timestamptz | N | now() |



UQ(workspace_id,user_id). UQ(workspace_id) WHERE role='OWNER' AND status='ACTIVE'로 **최대 한 명**을 제한한다. IDX(user_id,status,workspace_id), IDX(workspace_id,status,id). CHECK (status='ACTIVE' AND ended_at IS NULL) OR (status IN ('LEFT','REMOVED') AND ended_at IS NOT NULL).



정확히 한 OWNER는 Workspace 잠금 아래 서비스 트랜잭션이 보장한다. 이전 OWNER 강등→새 OWNER 승격→최종 OWNER 수 검증→commit. 중간 오류는 전부 rollback한다. 재가입은 기존 membership 행을 갱신하며 새 중복 행을 만들지 않는다.



<a id="table-invitations"></a>



## invitations



| 컬럼 | 타입 | NULL | 기본값·의미 |

|---|---|---|---|

| workspace_id | uuid | N | workspaces 논리 참조 |

| target_github_user_id | bigint | N | 양수, 아직 users에 없어도 되는 외부 ID |

| invited_by | uuid | N | users 논리 참조 |

| token_hash | H256 | N | 초대 난수 토큰 해시 |

| role | varchar(16) | N | MEMBER 기본, MEMBER/ADMIN CHECK |

| status | varchar(16) | N | PENDING 기본, PENDING/ACCEPTED/REVOKED/EXPIRED CHECK |

| expires_at | timestamptz | N | Workspace 정책의 만료 시각 |

| accepted_at / revoked_at | timestamptz | Y | 수락/철회 시각 |

| accepted_by | uuid | Y | 수락한 users 논리 참조 |

| updated_at | timestamptz | N | now() |



UQ(token_hash), UQ(workspace_id,target_github_user_id) WHERE status='PENDING'. IDX(expires_at) WHERE status='PENDING'. CHECK expires_at > created_at. ACCEPTED일 때만 accepted_at/accepted_by 둘 다 NOT NULL, REVOKED일 때만 revoked_at NOT NULL.



Workspace 잠금 아래 만료된 PENDING을 EXPIRED로 바꾼 뒤 재초대한다. 수락 시 로그인한 GitHub 숫자 ID·만료·미소비를 검증하고 membership upsert와 초대 소비를 원자적으로 처리한다. MEMBER 초대는 OWNER/ADMIN, ADMIN 초대는 OWNER만 허용한다. 초대 재발급은 이전 토큰을 재사용하지 않는다.
