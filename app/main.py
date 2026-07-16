"""FastAPI — HTTP 경계 "만".

불변식 2 (docs/03_architecture.md §2): **이 파일에 게임 규칙이 한 줄도 없다.**
요청 파싱 → 엔진 호출 → 응답 직렬화. 그게 전부다.

규칙(벽에 부딪히면 어떻게 되나, 적이 언제 행동하나, 데미지가 얼마인가)을 여기 넣기
시작하면 엔진이 더 이상 게임 본체가 아니게 되고, 순수 Python 테스트도 무의미해진다.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app import store
from app.schemas import (
    ActionRequest,
    ActionResponse,
    ActorView,
    FloorItemView,
    GameView,
    ItemView,
    NewGameRequest,
    TurnEvent,
)
from engine import actions, items, turn
from engine.combat import LEVEL_XP_FACTOR
from engine.state import MAP_H, MAP_W, GameState

app = FastAPI(title="Delve", description="턴제 로그라이크 — 개발 궤적이 주인공")

STATIC = Path(__file__).resolve().parent.parent / "static"


def _view(state: GameState) -> GameView:
    """GameState → 클라이언트가 볼 수 있는 것만."""
    tiles: list[str] = []
    lit: list[str] = []

    for y in range(MAP_H):
        row_chars: list[str] = []
        row_lit: list[str] = []
        for x in range(MAP_W):
            if state.map.visible[y][x]:
                row_chars.append(state.map.tiles[y][x])
                row_lit.append("1")
            elif state.map.explored[y][x]:
                row_chars.append(state.map.tiles[y][x])
                row_lit.append("0")
            else:
                row_chars.append(" ")  # 미탐색 — 아예 보내지 않는다
                row_lit.append("0")
        tiles.append("".join(row_chars))
        lit.append("".join(row_lit))

    visible_enemies = [
        ActorView(
            id=a.id,
            kind=a.kind,
            glyph=a.glyph,
            x=a.x,
            y=a.y,
            hp=a.hp,
            max_hp=a.max_hp,
        )
        for a in state.enemies
        if state.map.visible[a.y][a.x]
    ]

    def _item_view(it) -> ItemView:
        return ItemView(
            id=it.id, kind=it.kind, glyph=items.glyph_of(it.kind), name=items.name_of(it.kind)
        )

    inventory = [_item_view(it) for it in state.inventory]
    equipped = {
        slot: (None if it is None else _item_view(it))
        for slot, it in state.equipped.items()
    }
    floor_items = [
        FloorItemView(kind=f.kind, glyph=items.glyph_of(f.kind), x=f.x, y=f.y)
        for f in state.floor_items
        if state.map.visible[f.y][f.x]  # 안 보이는 바닥 아이템은 숨긴다 (FOV)
    ]

    p = state.player
    return GameView(
        game_id=state.game_id,
        seed=state.seed,
        turn=state.turn,
        floor=state.floor,
        status=state.status,
        width=MAP_W,
        height=MAP_H,
        tiles=tiles,
        lit=lit,
        player=ActorView(
            id=p.id, kind=p.kind, glyph=p.glyph, x=p.x, y=p.y, hp=p.hp, max_hp=p.max_hp
        ),
        level=state.level,
        xp=state.player_xp,
        xp_needed=LEVEL_XP_FACTOR * state.level,
        actors=visible_enemies,
        log=state.log[-8:],
        inventory=inventory,
        equipped=equipped,
        floor_items=floor_items,
    )


def _visible_events(state: GameState, events: list[dict]) -> list[TurnEvent]:
    """events를 FOV로 필터링한다 — GameView가 안 보이는 적을 숨기는 것과 같은 계약.

    노출: 플레이어 자신의 행동 / 플레이어를 향한 행동(맞으면 안다) / 지금 보이는 적의
    행동 / 액터 없는 전역 이벤트(floor·win). 감춤: 어둠 속 적의 이동·대기.
    (게임 규칙이 아니라 응답 성형이다 — _view가 하는 일과 같은 범주. 불변식 2 유지.)
    """
    visible_ids = {a.id for a in state.enemies if state.map.visible[a.y][a.x]}
    visible_ids.add("player")

    out: list[TurnEvent] = []
    for e in events:
        actor = e.get("actor")
        if actor is None or actor in visible_ids or e.get("target") == "player":
            out.append(TurnEvent(**e))
    return out


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


@app.post("/api/game", response_model=GameView)
def new_game(req: NewGameRequest) -> GameView:
    state, rng = turn.new_game(store.new_id(), req.seed)
    store.put(state, rng)
    return _view(state)


@app.get("/api/game/{game_id}", response_model=GameView)
def get_game(game_id: str) -> GameView:
    with store.session(game_id) as found:
        if found is None:
            raise HTTPException(404, "그런 게임이 없다 (서버가 재시작됐을 수 있다)")
        state, _ = found
        return _view(state)


@app.post(
    "/api/game/{game_id}/action",
    response_model=ActionResponse,
    response_model_exclude_none=True,
)
def do_action(game_id: str, req: ActionRequest) -> ActionResponse:
    # store.session()이 게임별 Lock을 잡는다 — 같은 게임의 동시 요청이 직렬화된다.
    # 잠금 없이 두면 state.turn과 Rng 소비가 겹쳐 시드 결정론이 깨진다 (app/store.py).
    with store.session(game_id) as found:
        if found is None:
            raise HTTPException(404, "그런 게임이 없다 (서버가 재시작됐을 수 있다)")

        state, rng = found
        try:
            events = turn.process_turn(state, rng, req.model_dump())
        except actions.InvalidAction as e:
            # 성립하지 않는 행동 — 턴은 소비되지 않았다. 상태를 그대로 돌려준다.
            raise HTTPException(409, str(e)) from e

        # v2: 최종 상태 + 그 사이 순서대로 일어난 일(FOV 필터). Rat이 2번 행동하면
        # events에 두 번 나온다 — 이게 전환이 클라이언트까지 파급되는 지점이다.
        return ActionResponse(view=_view(state), events=_visible_events(state, events))
