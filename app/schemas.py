"""API DTO — 엔진 타입과 분리한다.

engine/의 dataclass를 그대로 노출하지 않는 이유: 엔진이 pydantic을 몰라야 하고
(불변식 1), API 계약이 엔진 내부 구조 변경에 끌려다니면 안 되기 때문이다.

## v2에서 events[]가 생겼다 (전환 비용)

엔진의 `process_turn()`은 순서 있는 이벤트 목록을 돌려준다. v1에서는 이걸 API로
노출하지 않고 `log[]`(사람이 읽는 문장)만 내보냈다 — "1입력 = 전원 1행동"이라
클라이언트가 순서를 알 필요가 없었기 때문이다.

v2(에너지 스케줄러)에서는 플레이어 1입력에 Rat이 2번 행동할 수 있다. 이제 "무슨 일이
순서대로 일어났는지"를 클라이언트가 알아야 하므로 `POST /action` 응답을
`{view, events}`로 바꾼다 (GET은 여전히 `GameView`). **이것이 전환 비용의 일부다**
(docs/04_turn_system_pivot.md §4). v1에서 이 배열을 미리 넣지 않았기에, 이 변경이
"이미 있던 배열 채우기"가 아니라 실제 API 계약 변경으로 남는다.

**정보 은닉**: events[]도 FOV를 존중한다 — 보이지 않는 적의 이동/대기는 싣지 않고,
플레이어 자신·플레이어를 향한 행동·현재 보이는 적의 행동만 노출한다 (app/main.py의
`_visible_events`). GameView가 안 보이는 적을 숨기는 것과 같은 계약이다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class NewGameRequest(BaseModel):
    seed: int | None = None


class ActionRequest(BaseModel):
    type: Literal["move", "wait", "descend", "pickup", "use", "equip"]
    dir: str | None = None
    item_id: str | None = None  # use / equip 대상


class ActorView(BaseModel):
    id: str
    kind: str
    glyph: str
    x: int
    y: int
    hp: int
    max_hp: int


class ItemView(BaseModel):
    id: str
    kind: str
    glyph: str
    name: str


class FloorItemView(BaseModel):
    kind: str
    glyph: str
    x: int
    y: int


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
    log: list[str]  # 최근 로그 (사람이 읽는 문장)

    inventory: list[ItemView]
    equipped: dict[str, ItemView | None]  # "weapon" / "armor"
    floor_items: list[FloorItemView]  # 지금 보이는 것만 (FOV)


class TurnEvent(BaseModel):
    """한 입력 사이에 순서대로 일어난 일 하나. 종류(`t`)에 따라 쓰이는 필드가 다르다.

    move: to / attack: target, dmg / death, wait: actor / levelup: level / floor: floor.
    응답에서는 `response_model_exclude_none`으로 안 쓰는 필드가 빠진다.
    """

    t: str  # move | attack | wait | death | levelup | descend | floor | win
    actor: str | None = None
    target: str | None = None
    to: list[int] | None = None
    dmg: int | None = None
    level: int | None = None
    floor: int | None = None


class ActionResponse(BaseModel):
    """POST /action 응답 — v2. 최종 상태(view) + 그 사이 순서대로 일어난 일(events)."""

    view: GameView
    events: list[TurnEvent]
