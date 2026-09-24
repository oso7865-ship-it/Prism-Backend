# Stack Profile: PrimeVue + Tailwind CSS

> 목적: `skills/ui-ux-design/SKILL.md`가 기술 중립적으로 유지되도록, PrimeVue + Tailwind CSS를 사용하는 **특정 프로젝트**에서만 이 파일을 활성화해 적용한다.
> **이 파일은 `GENERAL_HARNESS`의 전역 규칙이 아니다.** 다른 UI 스택(예: Vuetify, Element Plus, 순수 CSS)을 쓰는 프로젝트는 이 파일을 참고하지 않고, 필요하면 같은 형식으로 자신만의 Stack Profile을 새로 만든다.

---

## 0. 활성화 방법

이 하네스를 부착한 프로젝트가 실제로 PrimeVue + Tailwind CSS를 쓴다면, 그 프로젝트 사본의 `05.WORKING_CONTEXT.md`에 다음을 기록해서 활성화한다(원본 템플릿에는 기록하지 않는다).

```text
기술 스택: Vue + PrimeVue + Tailwind CSS
UI Stack Profile: skills/ui-ux-design/STACK_PROFILE_PRIMEVUE_TAILWIND.md
```

이 기록이 없으면 `skills/ui-ux-design/SKILL.md`는 이 Profile을 참고하지 않고 라이브러리 독립적으로 진행한다.

---

## 1. PrimeVue의 소유 범위

동작·상태·접근성이 필요한 표준 컴포넌트는 PrimeVue가 담당한다.

- Button, InputText, Textarea, Select(또는 프로젝트 채택 동등 컴포넌트)
- Checkbox, RadioButton, DatePicker
- DataTable, Pagination
- Dialog, Drawer, ConfirmDialog
- Menu, Tabs
- Toast
- FileUpload, Skeleton, ProgressSpinner
- 그 외 키보드 상호작용과 접근성이 필요한 복합 UI

**원칙:** PrimeVue에 적합한 표준 컴포넌트가 존재하면, 동일 기능을 Tailwind CSS만으로 새로 만들지 않는다.

---

## 2. Tailwind CSS의 소유 범위

페이지 배치와 컴포넌트 외부 레이아웃은 Tailwind CSS가 담당한다.

- 페이지 전체 레이아웃, Grid/Flex, 컨테이너 너비
- 외부·내부 여백, 요소 간 간격, 정렬
- 반응형 배치 전환
- 타이포그래피
- 카드·섹션의 외부 구조
- 이미지 크기·비율, 표시/숨김, Overflow 처리

---

## 3. 혼합 사용 우선순위

```text
1. PrimeVue가 컴포넌트의 동작·상태·접근성을 담당한다.
2. PrimeVue 공식 테마·설정 방식으로 기본 표현을 통제한다.
3. Tailwind CSS가 페이지 배치와 컴포넌트 외부 레이아웃을 담당한다.
4. PrimeVue가 공식적으로 허용하는 스타일 지점에만 Tailwind를 제한적으로 적용한다.
5. Custom Vue Component는 프로젝트 고유 UI이거나 PrimeVue로 해결하기 어려운 경우에 한해 제한적으로 사용한다.
6. 일반 CSS와 내부 선택자 수정은 마지막 수단으로만 사용한다.
```

---

## 4. 금지 규칙

- Bootstrap, Vuetify, Element Plus 등 다른 UI 프레임워크를 임의로 추가하지 않는다.
- PrimeVue에 존재하는 표준 컴포넌트를 Tailwind CSS만으로 중복 구현하지 않는다.
- PrimeVue 내부 DOM 구조·비공개 클래스에 강하게 의존한 덮어쓰기를 하지 않는다.
- 반복적인 `!important` 사용을 하지 않는다.
- 근거 없는 Tailwind arbitrary value(임의 값)를 반복 사용하지 않는다.
- 같은 역할의 컴포넌트에 서로 다른 디자인 규칙을 적용하지 않는다.

---

## 5. 디자인 토큰과 테마 연결

이 Profile은 공통 `ui-ux-design` 스킬이 정한 화면 목적·시각적 품질 검토를 구현 규칙으로 바꿀 뿐, 새 브랜드 스타일을 임의로 만들지 않는다.

1. 프로젝트에 기존 디자인 토큰이 있으면 그것을 유일한 기준으로 삼는다. 색상·타이포그래피·간격·모서리·그림자·상태 값의 출처를 컴포넌트마다 새로 정하지 않는다.
2. PrimeVue의 테마·토큰 설정에는 Button, Input, Overlay, DataTable처럼 PrimeVue가 담당하는 표준 컴포넌트의 기본 표현을 연결한다. 컴포넌트별 개별 CSS 덮어쓰기는 테마로 해결할 수 없을 때만 사용한다.
3. Tailwind CSS에는 페이지 배치와 외부 레이아웃에 필요한 의미 기반 토큰만 연결한다. 같은 의미의 값을 여러 arbitrary value로 흩어 쓰지 않는다.
4. 상태 색상, 포커스 표시, 오류 안내, 비활성 상태는 PrimeVue 테마와 Tailwind 레이아웃에서 같은 의미로 표현한다. 색상만으로 상태를 전달하지 않는 접근성 원칙은 공통 스킬을 따른다.
5. 기존 토큰이 없으면 화면 구현 전에 최소한 색상 역할, 타이포그래피 단계, 간격 단계, 모서리·그림자 단계를 정하고, 이후 공통 컴포넌트와 화면이 그 기준을 공유하게 한다.

---

## 6. 커스텀 컴포넌트와 스타일 예외

Custom Vue Component 또는 개별 스타일 예외는 아래 중 하나가 성립할 때만 허용한다.

- 프로젝트 고유의 사용자 흐름·데이터 표현·브랜드 패턴이라 PrimeVue 표준 컴포넌트로 충분히 표현할 수 없음
- PrimeVue 표준 컴포넌트를 조합해도 접근성 또는 사용성 요구를 충족할 수 없음
- 기존 공통 컴포넌트의 변형으로 해결할 수 없고, 이후 재사용할 명확한 범위가 있음

예외를 만들 때는 다음을 설계 또는 구현 인계에 남긴다.

- 표준 컴포넌트/기존 공통 컴포넌트로 해결하지 않은 이유
- 적용한 디자인 토큰과 상태(기본, hover, focus, disabled, error)
- 재사용 범위와 새 공통 컴포넌트 승격 여부
- 키보드 조작·포커스·레이블·모바일 동작 확인 결과

예외 근거가 없으면 Tailwind arbitrary value, 내부 선택자 덮어쓰기, `!important`를 늘려서 해결하지 않는다.

---

## 7. 구현 전·후 확인

구현 전에는 컴포넌트 담당 범위와 토큰 연결 위치를 정한다. 구현 후에는 실제 화면에서 아래를 확인한다.

- 같은 역할의 PrimeVue 컴포넌트가 화면마다 다른 표면 규칙을 갖지 않는지
- Tailwind가 PrimeVue의 동작·접근성 책임을 침범하지 않는지
- 기본/hover/focus/disabled/error 상태가 토큰과 접근성 기준에 맞는지
- 모바일 전환에서 Primary Action과 핵심 정보의 우선순위가 유지되는지
- 화면 목적과 무관한 반복·장식·추상 문구가 구현 과정에서 다시 생기지 않았는지

이 확인은 공통 `skills/ui-ux-design/SKILL.md`의 시각적 품질 검토와 `gates/ui-ux-gate.md` 판정을 대체하지 않는다. 실제 구현 코드가 있으면 `skills/verification-loop/SKILL.md`도 함께 적용한다.

---

## 8. 실제 적용 전 확인할 것 (버전 종속 정보)

PrimeVue와 Tailwind CSS는 버전에 따라 설정 방식과 API가 달라질 수 있다. 이 문서는 특정 버전의 API를 고정하지 않는다 — 실제 작업 전 다음을 프로젝트에서 직접 확인한다.

- `package.json`의 PrimeVue/Tailwind 실제 버전
- PrimeVue 테마 설정, Styled/Unstyled mode 선택 여부
- Tailwind 설정 방식과 전역 CSS 진입점
- 기존 디자인 토큰, 기존 공통 컴포넌트

버전별 공식 문서를 확인하지 않고 이 문서에만 의존해 특정 API 사용법을 단정하지 않는다.
