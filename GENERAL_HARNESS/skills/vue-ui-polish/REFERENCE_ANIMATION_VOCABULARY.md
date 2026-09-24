# Animation Vocabulary

> `skills/vue-ui-polish/SKILL.md`의 보조 참조 문서다. 단독 스킬이 아니며, 상위 스킬의 Harness Control Rule(Vue 3 스택 한정 포함)을 그대로 따른다.

사용자가 원하는 움직임을 설명하지 못할 때만 이 표를 참고하라. 가장 가까운 용어를 먼저 제시하고, 비슷한 용어가 있으면 차이를 한 줄로 설명하라.

| 표현 | 의미 |
| --- | --- |
| Fade | opacity로 나타나거나 사라지는 전환 |
| Slide | 한 방향에서 밀려 들어오거나 나가는 전환 |
| Scale in | 작게 시작해 원래 크기로 나타나는 전환 |
| Pop in | 약간의 overshoot를 포함한 등장 |
| Reveal | clip-path나 mask로 콘텐츠가 드러나는 효과 |
| Stagger | 여러 요소를 짧은 간격으로 순차 실행 |
| Orchestration | 여러 애니메이션의 타이밍을 하나의 흐름으로 조정 |
| Transform origin | 확대·회전이 시작되는 기준점 |
| Origin-aware animation | 트리거 위치에서 시작되는 팝오버 같은 전환 |
| Crossfade | 같은 위치에서 한 요소가 사라지며 다른 요소가 나타남 |
| Morph | 하나의 형태가 다른 형태로 변함 |
| Shared element transition | 같은 요소가 화면 사이를 이동·변형하며 연결됨 |
| Layout animation | 위치나 크기 변경이 순간이동하지 않고 이어짐 |
| Direction-aware transition | 진행·복귀 방향에 맞춰 반대 방향으로 움직임 |
| Press feedback | 누를 때 작게 축소되는 등 즉시 주는 반응 |
| Hold to confirm | 일정 시간 누르는 동안 진행도가 차는 확인 방식 |
| Swipe to dismiss | 요소를 화면 밖으로 밀어 닫는 제스처 |
| Rubber-banding | 경계를 넘겨 당길 때 저항하고 되돌아오는 움직임 |
| Ease-out | 빠르게 시작해 부드럽게 멈추는 곡선 |
| Ease-in-out | 화면 안의 이동에 적합한 느림-빠름-느림 곡선 |
| Spring | 고정 시간 대신 물리 값으로 목표에 수렴하는 움직임 |
| Interruptible animation | 실행 중에도 새 목표로 자연스럽게 전환되는 모션 |
| Scroll reveal | viewport에 들어올 때 콘텐츠가 나타나는 효과 |
| Parallax | 스크롤 때 전경과 배경이 다른 속도로 움직이는 효과 |
| Skeleton/Shimmer | 로딩 중 구조를 보여주는 움직이는 자리 표시자 |
| Number ticker | 숫자가 굴러가거나 세어지는 전환 |
| Jank | 프레임 누락으로 보이는 끊김 |
| Layout thrashing | 반복적인 레이아웃 계산 때문에 생기는 성능 문제 |
| Reduced motion | 사용자의 모션 감소 설정에 맞춰 움직임을 완화함 |

