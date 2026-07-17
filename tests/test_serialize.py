"""세이브 포맷 라운드트립 — 저장 → 로드 → 상태 동일 (rng_state 포함).

docs/03 §3의 함정: seed만 저장하고 rng_state를 빼면 로드 후 생성이 원본과 어긋난다.
이 테스트가 그 함정을 조기에 잡는다 — BQ2의 후보를 예방한다(심는 게 아니라 막는다).
"""

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
    """복원된 rng는 저장 시점의 '이미 소비된' 상태에서 이어진다 — seed만으론 안 된다.

    RNG 스트림 분리(evt_5c9d0278) 이후 던전 생성은 **파생 스트림**을 쓰므로 부모 RNG를
    소비하지 않는다. 그래서 계약을 "던전 생성이 부모를 소비한다"(구현 세부)가 아니라
    "저장 시점의 소비 상태가 복원된다"로 검증한다.
    """
    state, rng = _played()
    for _ in range(5):
        rng.randint(0, 1000)  # 부모 RNG가 실제로 소비된 상태를 만든다
    saved = serialize.to_json(state, rng)

    _, rng_restored = serialize.from_json(saved)
    assert rng.randint(0, 10**9) == rng_restored.randint(0, 10**9)

    # seed만으로 새로 만든 rng는 (이미 소비됐으므로) 다르다 — 이게 §3 함정의 실체.
    fresh = Rng(state.seed)
    _, rng_again = serialize.from_json(saved)
    assert fresh.randint(0, 10**9) != rng_again.randint(0, 10**9)


def test_load_is_independent_of_original() -> None:
    """로드된 상태를 바꿔도 원본은 그대로다 (깊은 복사)."""
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
    """세이브 포맷 v2 — 인벤토리/장착/바닥 아이템이 살아 돌아온다 (BQ3의 실물)."""
    from engine import actions
    from engine.state import Item, ItemOnFloor

    state, rng = turn.new_game("s", 42)
    p = state.player
    state.floor_items = [
        ItemOnFloor(id="i1", kind="sword", x=p.x, y=p.y),
        ItemOnFloor(id="i2", kind="potion", x=p.x + 1, y=p.y),
    ]
    state.inventory = []
    actions.pickup(state)            # 발밑의 검을 줍고
    actions.equip(state, "i1")       # 장착
    state.inventory.append(Item(id="p9", kind="potion"))  # 가방에 포션 하나

    assert serialize.to_dict(state, rng)["version"] == 2

    state2, _ = serialize.from_json(serialize.to_json(state, rng))
    assert state2.equipped["weapon"].kind == "sword"
    assert [it.kind for it in state2.inventory] == ["potion"]
    assert [(f.kind, f.x, f.y) for f in state2.floor_items] == [("potion", p.x + 1, p.y)]
    assert state2.equipped["armor"] is None
