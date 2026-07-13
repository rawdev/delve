# 03. 아키텍처 — FastAPI + 순수 Python 엔진

## 1. 스택 결정 (그리고 기각된 대안)

### 채택: FastAPI + 순수 Python 게임 엔진 + 프레임워크 없는 단일 HTML

**왜:**
- **턴제이기 때문에 Python 서버가 게임 본체가 될 수 있다.** 한 칸 이동 = HTTP 요청
  1개 → 서버가 한 턴 진행 → JSON 상태 반환 → 브라우저는 그리드만 그린다. 실시간
  루프도 웹소켓도 필요 없다.
- 프론트를 최소화해야 **Python이 데모의 주인공으로 유지된다.**
- 게임 로직을 FastAPI에서 분리하면 프레임워크 교체·테스트가 자유롭다.

### 기각한 대안

| 대안 | 기각 이유 |
|---|---|
| **TypeScript + Canvas, 서버 없음 (GitHub Pages)** | 원 기획(`demo_scenario.md`)의 안. 배포는 가장 단순하지만 **게임 로직이 전부 JS로 넘어가 "Python 게임" 포지셔닝이 사라진다.** 또한 이 안은 "실시간 → 턴제 전환"을 사전 설계 통과 지점으로 잡았는데, 서버 권위 턴제 구조에서는 실시간 단계가 애초에 존재할 수 없으므로 그 전환은 **연출**이 된다. 원칙 2("작지만 진짜") 위반. |
| **타워 디펜스 (다른 장르)** | 실시간 시뮬이라 로직이 JS로 넘어감 — 위와 같은 이유로 탈락. |
| **Python 서버 + TypeScript 클라이언트 둘 다 제대로** | 범위가 2배가 되어 2~3주 일정과 "작지만 진짜" 원칙에 압박. |
| **BSP 던전 생성** | 랜덤 방 배치 + L자 복도로 충분. 과설계. |

> 이 표는 그대로 AiAkiv `결정` 이벤트로 저장된다 — 대안과 기각 이유가 결정 이벤트의
> 필수 4요소다. → [06_memory_protocol.md](06_memory_protocol.md)

## 2. 레이어 — 엔진은 FastAPI를 import하지 않는다

```
k2g-sample_game/
├─ docs/                  # 이 문서 세트
├─ app/
│  ├─ main.py             # FastAPI — HTTP 경계 "만". 게임 로직 0줄.
│  ├─ store.py            # 세션 저장소. Phase 1~3: dict / Phase 4: SQLite
│  └─ api/
│     └─ schemas.py       # Pydantic DTO (요청/응답). 엔진 타입과 분리.
├─ engine/                # ★ 순수 Python. FastAPI/Pydantic import 금지 ★
│  ├─ state.py            # GameState, Actor, Item — dataclass
│  ├─ rng.py              # 시드 RNG ("전역 시드")
│  ├─ dungeon.py          # 절차 생성 ("던전 생성")
│  ├─ fov.py              # 시야
│  ├─ turn.py             # ★ 턴 스케줄러 — 전환점의 무대 ("턴 시스템")
│  ├─ actions.py          # 행동 해석 → 턴 진행
│  ├─ combat.py           # 전투 판정
│  ├─ ai.py               # 적 AI ("적 AI")
│  ├─ items.py            # 아이템/인벤토리
│  └─ serialize.py        # ★ 세이브 포맷 ("세이브 포맷")
├─ static/
│  └─ index.html          # 프론트 전부. 빌드 도구 없음.
└─ tests/
   └─ test_*.py           # 엔진은 HTTP 없이 테스트 가능해야 한다
```

**불변식 (이걸 깨면 아키텍처가 무너진다):**

1. `engine/`은 `fastapi`, `pydantic`을 **import하지 않는다.** 순수 Python + 표준
   라이브러리만. → 엔진 단독 테스트 가능, 웹 프레임워크 교체 가능.
2. `app/main.py`에 **게임 규칙이 한 줄도 없다.** 요청 파싱 → 엔진 호출 → 응답 직렬화.
3. 모든 무작위성은 `engine/rng.py`를 거친다. **`random` 전역 모듈 직접 호출 금지.**
   → 재현성이 깨지는 가장 흔한 경로를 원천 차단.

> 괄호 안의 이름(`"턴 시스템"`, `"세이브 포맷"` 등)은 **AiAkiv 엔티티 이름**이다.
> 코드 모듈과 엔티티 이름을 1:1로 맞춰두면 "이 파일 왜 이렇게 됐어?"가 곧바로
> 그래프 질의가 된다. → [06_memory_protocol.md](06_memory_protocol.md) §3

## 3. 상태 모델

```python
@dataclass
class GameState:
    game_id: str
    seed: int              # ★ 전역 시드 — 이게 있어야 재현/리플레이가 가능
    turn: int
    floor: int             # 1..5
    rng_state: tuple       # ★ 현재 RNG 상태 (세이브에 반드시 포함)
    map: Map               # tiles[64][32], explored[][], visible[][]
    actors: list[Actor]    # actors[0] == player (관례)
    items: list[ItemOnFloor]
    inventory: list[Item]  # Phase 2에서 추가 → 세이브 포맷 변경 (BQ3)
    equipped: dict         # Phase 2에서 추가 → 세이브 포맷 변경 (BQ3)
    log: list[str]
    status: str            # "playing" | "dead" | "won"
```

**세이브 포맷의 함정 (미리 안다고 피해가지 말 것):**
`seed`만 저장하고 `rng_state`를 빼면, 세이브를 불러왔을 때 이후 생성이 원본과
어긋난다. 이건 실제로 자주 나오는 버그다. **미리 방어하려고 애쓰기보다, 터지면
규약대로 "증상 + 근본 원인(= 세이브 포맷 v1 결정)"으로 저장한다.** 그게 BQ2의
후보가 된다 — 심는 게 아니라 만나는 것.

## 4. API 계약

| 메서드 | 경로 | 요청 | 응답 |
|---|---|---|---|
| POST | `/api/game` | `{seed?: int}` | `GameView` |
| GET | `/api/game/{id}` | — | `GameView` |
| POST | `/api/game/{id}/action` | `{type, dir?, item_id?}` | `{view: GameView, events: [TurnEvent]}` |
| POST | `/api/game/{id}/save` | — | `{save_id}` (Phase 4) |
| POST | `/api/game/{id}/load` | `{save_id}` | `GameView` (Phase 4) |

`action.type`: `move` | `wait` | `pickup` | `use` | `equip` | `descend`

### `events[]` 배열이 왜 필요한가 — 전환점의 API 파급

v1(즉시판정)에서는 응답이 "새 상태" 하나면 충분했다. **v2(에너지 스케줄러)에서는
플레이어 1입력에 Rat이 2번 행동할 수 있다.** 클라이언트가 "무슨 일이 일어났는지"를
표현하려면 순서 있는 이벤트 목록이 필요하다:

```json
{ "view": { ... },
  "events": [
    {"t": "move",   "actor": "player", "to": [12, 7]},
    {"t": "attack", "actor": "rat#3", "target": "player", "dmg": 2},
    {"t": "attack", "actor": "rat#3", "target": "player", "dmg": 2}
  ] }
```

**즉 전환은 엔진 내부에서 끝나지 않고 API 계약까지 바꾼다.** 이 전환 비용을
결정 이벤트에 정확히 기록하는 것이 DQ1의 답을 두껍게 만든다.
→ [04_turn_system_pivot.md](04_turn_system_pivot.md)

## 5. 세션 저장소 (`store.py`)

| Phase | 구현 | 왜 |
|---|---|---|
| 1~3 | 프로세스 메모리 `dict[game_id] → GameState` | 가장 빠르게 굴러가는 것부터 |
| 4 | SQLite (`serialize.py`의 JSON을 blob으로) | "세이브 기능 추가" 세션에서 자연스럽게 도입 |

**인메모리 dict는 서버 재시작 시 전부 날아간다.** 이건 알려진 한계이며, Phase 4의
세이브 구현이 이걸 해결한다. 여기서 파생되는 버그가 나오면 근본 원인은 "Phase 1의
인메모리 상태 결정"으로 링크된다 — 다시 말하지만 **예상이지 계획이 아니다.**

## 6. 결정론 규칙 (전역 시드)

1. 게임 생성 시 `seed`를 받거나 생성해서 **응답에 항상 노출한다** (재현 가능한 버그
   리포트의 전제 — 동료 플레이테스트 피드백이 여기 의존한다).
2. 던전 생성, 아이템 배치, 적 배치 — 전부 `engine/rng.py`의 시드 RNG.
3. 전투에는 무작위가 없다(§02 §4) — 의도적. 무작위 표면적을 줄일수록 재현이 쉽다.
4. 세이브에는 `seed`와 `rng_state`를 **둘 다** 넣는다.

## 7. 배포

- Railway (기존 인프라 재사용). 단일 컨테이너, DB는 Phase 4의 SQLite 파일.
- 공개 URL 3종을 상호 링크: **플레이 / GitHub 저장소 / AiAkiv 공개 프로젝트**.
  이것이 "이 히스토리가 이 게임을 만들었다"의 폐루프.

## 8. 테스트

엔진이 순수 Python이므로 HTTP 없이 테스트한다. **최소한 다음은 테스트가 있어야 한다:**

- `test_dungeon.py` — 같은 시드 → 같은 맵 (결정론)
- `test_turn.py` — 속도 150/100/60 액터의 행동 횟수 비율 (전환 후 필수)
- `test_serialize.py` — 저장 → 로드 → 상태 동일 (rng_state 포함)

> 세 번째 테스트가 있으면 §3의 함정이 조기에 잡힌다. 있으면 좋고, 없어서 터지면
> 그것대로 BQ의 재료다. **어느 쪽이든 정직하게 기록한다.**
