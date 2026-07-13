"""API DTO — 엔진 타입과 분리한다.

engine/의 dataclass를 그대로 노출하지 않는 이유: 엔진이 pydantic을 몰라야 하고
(불변식 1), API 계약이 엔진 내부 구조 변경에 끌려다니면 안 되기 때문이다.

## v1 응답에는 events[] 배열이 없다 (의도적)

엔진의 `process_turn()`은 이미 이벤트 목록을 만든다. 그런데 API로는 노출하지 않고
`log[]`(사람이 읽는 문장)만 내보낸다.

**왜 참는가**: v1은 "플레이어 1행동 → 적 각 1행동"이 항상 참이라, 클라이언트가 순서를
알 필요가 없다. 새 상태를 통째로 다시 그리면 그만이다.

v2(에너지 스케줄러)에서는 플레이어 1입력에 Rat이 2번 행동할 수 있다. 그때 비로소
"무슨 일이 순서대로 일어났는지"를 클라이언트가 알아야 하고, `events[]`가 필요해진다.
**그게 전환 비용의 일부다** (docs/04_turn_system_pivot.md §4).

지금 배열을 미리 넣어두면 Phase 2의 전환이 "API 계약 변경"이 아니라 "이미 있던 배열
채우기"가 된다. Actor에 speed/energy를 미리 넣지 않은 것과 같은 이유다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class NewGameRequest(BaseModel):
    seed: int | None = None


class ActionRequest(BaseModel):
    type: Literal["move", "wait", "descend"]
    dir: str | None = None


class ActorView(BaseModel):
    id: str
    kind: str
    glyph: str
    x: int
    y: int
    hp: int
    max_hp: int


class GameView(BaseModel):
    game_id: str
    seed: int  # 항상 실린다 — 버그 재현의 전제 (docs/10_running.md §5)
    turn: int
    floor: int
    status: str  # "playing" | "dead" | "won"

    width: int
    height: int
    tiles: list[str]  # 행 단위 문자열. 미탐색 칸은 " "
    lit: list[str]  # "1"/"0" — 지금 보이는 칸(밝게) / 기억(어둡게)

    player: ActorView
    level: int
    xp: int
    xp_needed: int
    actors: list[ActorView]  # 지금 보이는 적만
    log: list[str]  # 최근 로그. v1은 이걸로 충분하다.
