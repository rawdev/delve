
from __future__ import annotations

import pytest

from engine import serialize, turn
from engine.rng import Rng


def _played(seed: int = 42, steps: int = 6):
    state, rng = turn.new_game("s", seed)
    for _ in range(steps):
        turn.process_turn(state, rng, {"type": "wait"})
    return state, rng


def test_roundtrip_preserves_state() -> None:
    state, rng = _played()
    state2, _ = serialize.from_json(serialize.to_json(state, rng))

    assert state2.game_id == state.game_id
    assert state2.seed == state.seed
    assert (state2.turn, state2.floor, state2.status) == (state.turn, state.floor, state.status)
    assert (state2.level, state2.player_xp) == (state.level, state.player_xp)
    assert state2.map.tiles == state.map.tiles
    assert state2.map.explored == state.map.explored
    assert state2.map.visible == state.map.visible
    assert state2.map.rooms == state.map.rooms
    assert [vars(a) for a in state2.actors] == [vars(a) for a in state.actors]
    assert state2.log == state.log


def test_rng_state_is_restored_not_just_seed() -> None:
    state, rng = _played()
    for _ in range(5):
        rng.randint(0, 1000)
    saved = serialize.to_json(state, rng)

    _, rng_restored = serialize.from_json(saved)
    assert rng.randint(0, 10**9) == rng_restored.randint(0, 10**9)


    fresh = Rng(state.seed)
    _, rng_again = serialize.from_json(saved)
    assert fresh.randint(0, 10**9) != rng_again.randint(0, 10**9)


def test_load_is_independent_of_original() -> None:
    state, rng = _played()
    state2, _ = serialize.from_json(serialize.to_json(state, rng))

    state2.actors[0].hp = -999
    assert state.actors[0].hp > 0


def test_format_carries_a_version() -> None:
    state, rng = _played()
    assert serialize.to_dict(state, rng)["version"] == serialize.FORMAT_VERSION


def test_rejects_unknown_version() -> None:
    with pytest.raises(ValueError):
        serialize.from_dict({"version": 999})


def test_inventory_and_equipment_roundtrip_at_v2() -> None:
    from engine import actions
    from engine.state import Item, ItemOnFloor

    state, rng = turn.new_game("s", 42)
    p = state.player
    state.floor_items = [
        ItemOnFloor(id="i1", kind="sword", x=p.x, y=p.y),
        ItemOnFloor(id="i2", kind="potion", x=p.x + 1, y=p.y),
    ]
    state.inventory = []
    actions.pickup(state)
    actions.equip(state, "i1")
    state.inventory.append(Item(id="p9", kind="potion"))

    assert serialize.to_dict(state, rng)["version"] == 2

    state2, _ = serialize.from_json(serialize.to_json(state, rng))
    assert state2.equipped["weapon"].kind == "sword"
    assert [it.kind for it in state2.inventory] == ["potion"]
    assert [(f.kind, f.x, f.y) for f in state2.floor_items] == [("potion", p.x + 1, p.y)]
    assert state2.equipped["armor"] is None
