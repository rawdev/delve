
from __future__ import annotations

import json

from engine.rng import Rng
from engine.state import Actor, GameState, Item, ItemOnFloor, Map

FORMAT_VERSION = 2

_ACTOR_FIELDS = (
    "id", "kind", "glyph", "x", "y", "hp", "max_hp", "atk", "def_", "xp", "speed", "energy",
)


def to_dict(state: GameState, rng: Rng) -> dict:
    return {
        "version": FORMAT_VERSION,
        "game_id": state.game_id,
        "seed": state.seed,
        "rng_state": _rng_to_json(rng.get_state()),
        "turn": state.turn,
        "floor": state.floor,
        "status": state.status,
        "level": state.level,
        "player_xp": state.player_xp,
        "map": {
            "tiles": ["".join(row) for row in state.map.tiles],
            "explored": state.map.explored,
            "visible": state.map.visible,
            "rooms": [list(r) for r in state.map.rooms],
        },
        "actors": [_actor_to_dict(a) for a in state.actors],
        "inventory": [_item_to_dict(it) for it in state.inventory],
        "equipped": {
            slot: (None if it is None else _item_to_dict(it))
            for slot, it in state.equipped.items()
        },
        "floor_items": [_floor_item_to_dict(f) for f in state.floor_items],
        "log": list(state.log),
    }


def from_dict(data: dict) -> tuple[GameState, Rng]:
    version = data.get("version")
    if version != FORMAT_VERSION:
        raise ValueError(f"Unsupported save format version: {version} (expected {FORMAT_VERSION})")

    m = data["map"]
    game_map = Map(
        tiles=[list(row) for row in m["tiles"]],
        explored=[list(row) for row in m["explored"]],
        visible=[list(row) for row in m["visible"]],
        rooms=[tuple(r) for r in m["rooms"]],
    )
    state = GameState(
        game_id=data["game_id"],
        seed=data["seed"],
        turn=data["turn"],
        floor=data["floor"],
        map=game_map,
        actors=[_actor_from_dict(a) for a in data["actors"]],
        log=list(data["log"]),
        status=data["status"],
        level=data["level"],
        player_xp=data["player_xp"],
        inventory=[_item_from_dict(d) for d in data.get("inventory", [])],
        equipped={
            slot: (None if d is None else _item_from_dict(d))
            for slot, d in data.get("equipped", {"weapon": None, "armor": None}).items()
        },
        floor_items=[_floor_item_from_dict(d) for d in data.get("floor_items", [])],
    )

    rng = Rng(data["seed"])
    rng.set_state(_rng_from_json(data["rng_state"]))
    return state, rng


def to_json(state: GameState, rng: Rng) -> str:
    return json.dumps(to_dict(state, rng))


def from_json(text: str) -> tuple[GameState, Rng]:
    return from_dict(json.loads(text))


def _actor_to_dict(a: Actor) -> dict:
    return {f: getattr(a, f) for f in _ACTOR_FIELDS}


def _actor_from_dict(d: dict) -> Actor:
    return Actor(**{f: d[f] for f in _ACTOR_FIELDS})


def _item_to_dict(it: Item) -> dict:
    return {"id": it.id, "kind": it.kind}


def _item_from_dict(d: dict) -> Item:
    return Item(id=d["id"], kind=d["kind"])


def _floor_item_to_dict(f: ItemOnFloor) -> dict:
    return {"id": f.id, "kind": f.kind, "x": f.x, "y": f.y}


def _floor_item_from_dict(d: dict) -> ItemOnFloor:
    return ItemOnFloor(id=d["id"], kind=d["kind"], x=d["x"], y=d["y"])


def _rng_to_json(state: tuple) -> list:
    # random.getstate() -> (version:int, internal:tuple[int, ...], gauss:float|None)
    version, internal, gauss = state
    return [version, list(internal), gauss]


def _rng_from_json(data: list) -> tuple:
    version, internal, gauss = data
    return (version, tuple(internal), gauss)
