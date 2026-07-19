
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

app = FastAPI(title="Delve", description="A turn-based roguelike whose development trail is the protagonist")

STATIC = Path(__file__).resolve().parent.parent / "static"


def _view(state: GameState) -> GameView:
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
                row_chars.append(" ")
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
        if state.map.visible[f.y][f.x]
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
            raise HTTPException(404, "Game not found; the server may have restarted")
        state, _ = found
        return _view(state)


@app.post(
    "/api/game/{game_id}/action",
    response_model=ActionResponse,
    response_model_exclude_none=True,
)
def do_action(game_id: str, req: ActionRequest) -> ActionResponse:


    with store.session(game_id) as found:
        if found is None:
            raise HTTPException(404, "Game not found; the server may have restarted")

        state, rng = found
        try:
            events = turn.process_turn(state, rng, req.model_dump())
        except actions.InvalidAction as e:

            raise HTTPException(409, str(e)) from e



        return ActionResponse(view=_view(state), events=_visible_events(state, events))
