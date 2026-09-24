# Vue Patterns

> `skills/vue-ui-polish/SKILL.md`의 보조 참조 문서다. 단독 스킬이 아니며, 상위 스킬의 Harness Control Rule(Vue 3 스택 한정 포함)을 그대로 따른다.

## 0. 프로젝트 관례 보존

- Composition API와 Options API가 섞여 있다면 대상 폴더의 기존 방식을 따른다.
- Router, Pinia, TanStack Query, 폼·검증 라이브러리의 현재 책임을 디자인 작업 중 옮기지 않는다.
- 공통 컴포넌트가 있으면 props·slots·events 계약을 먼저 읽고 재사용한다.
- 서버 상태, 전역 제품 상태, 컴포넌트 로컬 상태를 구분한다.
- 스타일 방식은 프로젝트의 Tailwind, scoped CSS, CSS Modules 중 기존 방식을 유지한다.

### PrimeVue

- 현재 프로젝트가 styled mode인지 unstyled mode인지 확인한다.
- 테마 preset, semantic token, PassThrough 설정이 있으면 페이지 내부 override보다 우선한다.
- 접근성·포커스·키보드 동작을 이미 제공하는 primitive를 CSS 때문에 다시 구현하지 않는다.
- PrimeVue 내부 클래스에 깨지기 쉬운 전역 선택자를 덧대기보다 공식 토큰·PassThrough·wrapper API를 사용한다.

### Tailwind

- 설정된 theme token과 프로젝트 utility 조합을 우선한다.
- 같은 의미의 긴 class 조합이 반복되면 기존 Base 컴포넌트나 프로젝트가 사용하는 추출 방식을 검토한다.
- 임의 값은 한 번의 예외에만 사용하고, 반복되면 의미 토큰으로 승격한다.
- Tailwind와 scoped CSS 중 어느 쪽이 더 예쁜지가 아니라 현재 컴포넌트의 책임과 프로젝트 규칙으로 선택한다.

## 1. `Transition`

단일 요소나 컴포넌트의 등장·퇴장에는 Vue의 `<Transition>`을 우선 고려하라.

```vue
<Transition name="fade-scale">
  <Modal v-if="isOpen" />
</Transition>

<style scoped>
.fade-scale-enter-active,
.fade-scale-leave-active {
  transition:
    opacity 180ms cubic-bezier(0.23, 1, 0.32, 1),
    transform 180ms cubic-bezier(0.23, 1, 0.32, 1);
}

.fade-scale-enter-from,
.fade-scale-leave-to {
  opacity: 0;
  transform: scale(0.97);
}
</style>
```

- DOM에 추가·제거되어야 하면 `v-if`를 사용하라.
- 자주 열고 닫으며 상태와 DOM을 보존해야 하면 `v-show`를 검토하라.
- `appear`는 최초 렌더링에서 정말 필요한 경우에만 사용하라.
- enter와 leave의 목적이 다르면 시간을 대칭으로 맞추지 않아도 된다.

## 2. `TransitionGroup`

목록의 추가·삭제·순서 변경에만 사용하라. 각 항목에는 안정적이고 고유한 `key`를 제공하라.

```vue
<TransitionGroup name="list" tag="ul">
  <li v-for="item in items" :key="item.id">
    {{ item.title }}
  </li>
</TransitionGroup>
```

- 배열 index를 key로 사용하지 마라.
- 게시물 피드처럼 빈번하게 갱신되는 긴 목록에는 모든 항목의 입장 모션을 피하라.
- 재정렬 이동은 `.list-move`에서 `transform` 기반으로 처리하라.
- 페이지네이션·무한 스크롤 항목이 한꺼번에 춤추지 않게 하라.

## 3. 상태 변경과 재실행

- Pinia의 넓은 store 객체 전체를 감시해 애니메이션을 시작하지 마라.
- 실제 시각 상태에 필요한 값만 `computed`, `storeToRefs`, 좁은 `watch`로 구독하라.
- `watchEffect`가 렌더링마다 DOM 애니메이션을 다시 시작하지 않는지 확인하라.
- 비동기 요청 상태는 `idle`, `loading`, `success`, `error`처럼 명시적으로 표현하라.
- 새로고침 후 복구되는 서버 상태와 단순한 화면 애니메이션 상태를 섞지 마라.

## 4. 라우트와 화면 전환

- Router 이동은 정보 탐색의 핵심이므로 기본적으로 즉각 반응하게 하라.
- 모든 경로에 긴 페이지 전환을 전역 적용하지 마라.
- 방향성이 의미 있는 온보딩 단계나 드문 상세 확장에만 전환을 고려하라.
- 접근성 포커스 이동과 스크롤 복구가 애니메이션 때문에 늦어지지 않게 하라.

## 5. 모바일 우선 반응형

- 작은 화면에서 단일 열과 주요 행동을 먼저 성립시켜라.
- 넓은 화면에서는 `max-width`, grid, 보조 패널로 정보 밀도를 확장하라.
- flex 자식의 텍스트 줄바꿈이 막히면 `min-width: 0`을 확인하라.
- 고정 px 너비보다 `min()`, `max()`, `clamp()`, `%`, `rem`을 맥락에 맞게 사용하라.
- 버튼·링크가 너무 작거나 서로 붙어 있지 않은지 확인하라.
- safe area와 모바일 키보드가 하단 고정 UI를 가리지 않는지 확인하라.

## 6. 라이브러리 선택

다음 순서로 결정하라.

1. 현재 프로젝트에서 이미 사용 중인 라이브러리
2. Vue 기본 기능과 CSS
3. 접근성과 포커스 관리가 검증된 Vue UI primitive
4. 동적 제스처가 필요할 때 Vue 호환 모션 라이브러리

React 전용 라이브러리를 Vue 프로젝트에 추천하지 마라. 새 의존성을 제안할 때는 유지보수 상태, Vue 버전 호환성, 번들 비용, 접근성을 현재 공식 자료로 확인하라.

## 7. 검증

- 컴포넌트를 빠르게 연속 조작해 중간 상태가 깨지지 않는지 확인하라.
- 모바일 터치와 PC 키보드·마우스를 각각 확인하라.
- reduced-motion 환경에서 의미 전달이 유지되는지 확인하라.
- 브라우저 콘솔 오류와 Vue 경고가 없는지 확인하라.
- 네트워크가 느릴 때 loading, success, error 전환이 겹치지 않는지 확인하라.
- hydration, console, accessibility 경고를 디자인 문제와 별개로 넘기지 마라.
- PrimeVue overlay와 Teleport가 z-index, focus, scroll lock을 올바르게 처리하는지 확인하라.
- Tailwind production build에서 동적 class 이름이 누락되지 않는지 확인하라.
