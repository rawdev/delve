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
from app.schemas import ActionRequest, ActorView, GameView, NewGameRequest
from engine import actions, turn
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
    )


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
    found = store.get(game_id)
    if found is None:
        raise HTTPException(404, "그런 게임이 없다 (서버가 재시작됐을 수 있다)")
    return _view(found[0])


@app.post("/api/game/{game_id}/action", response_model=GameView)
def do_action(game_id: str, req: ActionRequest) -> GameView:
    found = store.get(game_id)
    if found is None:
        raise HTTPException(404, "그런 게임이 없다 (서버가 재시작됐을 수 있다)")

    state, rng = found
    try:
        turn.process_turn(state, rng, req.model_dump())
    except actions.InvalidAction as e:
        # 성립하지 않는 행동 — 턴은 소비되지 않았다. 상태를 그대로 돌려준다.
        raise HTTPException(409, str(e)) from e

    return _view(state)
