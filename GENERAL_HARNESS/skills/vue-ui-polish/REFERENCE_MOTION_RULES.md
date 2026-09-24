# Motion Rules

> `skills/vue-ui-polish/SKILL.md`의 보조 참조 문서다. 단독 스킬이 아니며, 상위 스킬의 Harness Control Rule(Vue 3 스택 한정 포함)을 그대로 따른다.

필요한 부분만 선택해 적용하라. 모든 요소에 애니메이션을 추가하는 체크리스트로 사용하지 마라.

## 1. Easing

- 화면에 들어오거나 나가는 UI에는 빠르게 반응하고 부드럽게 멈추는 `ease-out`을 사용하라.
- 화면 안에서 위치나 형태가 이동하는 요소에는 `ease-in-out`을 사용하라.
- 색상이나 단순 hover 변화에는 `ease`를 허용하라.
- 스피너·마키처럼 일정 속도가 의미 있는 경우에만 `linear`를 사용하라.
- UI 반응에 `ease-in`을 사용하지 마라. 시작이 느려 입력이 무시된 것처럼 느껴진다.

기존 프로젝트 토큰이 없다면 다음 값을 우선 고려하라.

```css
:root {
  --ease-out-ui: cubic-bezier(0.23, 1, 0.32, 1);
  --ease-in-out-ui: cubic-bezier(0.77, 0, 0.175, 1);
  --ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);
}
```

프로젝트에 이미 유사한 토큰이 있다면 새 토큰을 만들지 말고 기존 체계를 확장하라.

## 2. Duration

| 요소 | 권장 범위 |
| --- | --- |
| 버튼 누름 피드백 | 100–160ms |
| 툴팁·작은 팝오버 | 125–200ms |
| 드롭다운·셀렉트 | 150–250ms |
| 일반 모달 | 180–260ms |
| 큰 드로어·화면 전환 | 250–500ms, 이동 거리에 근거가 있을 때 |
| 설명·마케팅 모션 | 맥락에 따라 더 길게 |

일반적인 조작 UI는 300ms 안에서 끝내라. 300ms를 넘긴다면 큰 이동 거리나 정보 전달 목적을 근거로 설명하라. 단지 고급스럽게 보이기 위해 느리게 만들지 마라.

## 3. Physicality

- 버튼과 눌러지는 요소에는 필요할 때 `scale(0.97)` 수준의 짧은 active 피드백을 사용하라.
- 등장 요소를 `scale(0)`에서 시작하지 마라. `scale(0.95–0.98)`과 opacity를 조합하라.
- 팝오버·드롭다운·툴팁은 트리거 방향을 `transform-origin`으로 사용하라.
- 화면 중앙에 독립적으로 나타나는 모달은 중앙 origin을 유지하라.
- 들어온 방향과 사라지는 방향을 일관되게 유지하라.
- 여러 요소의 등장은 필요한 경우에만 30–80ms 정도로 stagger하되 상호작용을 막지 마라.

## 4. Interruptibility

- 빠르게 반복되는 토글, 토스트, 목록 변화에는 중간에 목표를 바꿀 수 있는 transition을 선호하라.
- 동적 드래그와 제스처에는 현재 속도를 이어받는 spring을 고려하라.
- 반복 입력 때 처음부터 재시작하는 keyframes를 피하라.
- 스프링이 필요하면 작게 시작하라. 예: `{ type: "spring", duration: 0.5, bounce: 0.2 }`.

## 5. Performance

- 기본적으로 `transform`과 `opacity`를 움직여라.
- `width`, `height`, `margin`, `padding`, `top`, `left`를 프레임마다 움직이지 마라.
- 레이아웃 크기를 반드시 바꿔야 하는 아코디언은 측정·레이아웃 비용을 확인하고 범위를 제한하라.
- `transition: all`을 사용하지 말고 실제 변하는 속성을 명시하라.
- `filter: blur()`는 작은 범위와 짧은 시간에만 사용하라.
- `will-change`를 항상 켜두지 말고 실제로 이득이 확인될 때만 제한적으로 사용하라.

## 6. Accessibility

움직임을 완전히 없애야 한다고 단정하지 말고, 공간 이동과 확대를 줄이면서 opacity·색상 같은 상태 전달은 보존하라.

```css
@media (prefers-reduced-motion: reduce) {
  .animated {
    transform: none;
    transition-duration: 1ms;
  }
}

@media (hover: hover) and (pointer: fine) {
  .interactive:hover {
    transform: translateY(-1px);
  }
}
```

위 예시는 출발점이다. 컴포넌트 상태가 사라지지 않도록 프로젝트에 맞게 조정하라.

## 7. 즉시 경고할 패턴

- `transition: all`
- UI 진입에 `ease-in`
- `scale(0)` 등장
- 키보드 단축키 화면의 긴 진입·퇴장
- 이유 없는 300ms 초과 UI 모션
- 팝오버의 잘못된 중앙 origin
- 이동 모션에 reduced-motion 대응 없음
- 모바일에서도 hover가 있어야만 정보를 알 수 있는 구조
- 프레임마다 레이아웃 속성을 갱신하는 구현
