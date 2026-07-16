"""아이템 — 줍기 / 사용(포션·스크롤) / 장착(검·방패)과 전투 반영.

인벤토리가 GameState에 들어오면서 세이브 포맷이 v1 → v2로 올라갔다 (BQ3). 여기서는
아이템 규칙 자체를 HTTP 없이 순수 Python으로 검증한다.
"""

from __future__ import annotations

import pytest

from engine import actions, combat, items, turn
from engine.state import Item, ItemOnFloor, make_enemy


def _game(seed: int = 42):
    state, rng = turn.new_game("it", seed)
    # 던전이 뿌린 아이템 대신 통제된 상황을 쓴다.
    state.floor_items = []
    state.inventory = []
    state.equipped = {"weapon": None, "armor": None}
    return state, rng


def _damage(state, attacker, target) -> int:
    """전투를 한 번 돌려 데미지를 읽고 target을 원상복구한다."""
    hp_before = target.hp
    combat.attack(state, attacker, target)
    dmg = hp_before - target.hp
    target.hp = hp_before
    return dmg


def test_pickup_moves_floor_item_to_inventory() -> None:
    state, _ = _game()
    p = state.player
    state.floor_items = [ItemOnFloor(id="i1", kind="potion", x=p.x, y=p.y)]

    events = actions.pickup(state)

    assert [it.kind for it in state.inventory] == ["potion"]
    assert state.floor_items == []
    assert any(e["t"] == "pickup" for e in events)


def test_pickup_with_nothing_here_is_rejected() -> None:
    state, _ = _game()
    with pytest.raises(actions.InvalidAction):
        actions.pickup(state)


def test_pickup_rejected_when_bag_is_full() -> None:
    state, _ = _game()
    p = state.player
    state.inventory = [Item(id=f"x{i}", kind="potion") for i in range(items.INVENTORY_MAX)]
    state.floor_items = [ItemOnFloor(id="i1", kind="sword", x=p.x, y=p.y)]

    with pytest.raises(actions.InvalidAction):
        actions.pickup(state)


def test_use_potion_heals_but_not_over_max() -> None:
    state, _ = _game()
    p = state.player
    p.hp = p.max_hp - 3
    state.inventory = [Item(id="p1", kind="potion")]

    actions.use(state, "p1")

    assert p.hp == p.max_hp  # 10 회복이지만 최대치 초과 안 함
    assert state.inventory == []


def test_use_scroll_teleports_to_floor_start() -> None:
    state, _ = _game()
    p = state.player
    p.x, p.y = p.x + 3, p.y + 3
    state.inventory = [Item(id="s1", kind="scroll")]
    start = actions._floor_start(state)

    actions.use(state, "s1")

    assert (p.x, p.y) == start
    assert state.inventory == []


def test_use_on_equippable_is_rejected() -> None:
    state, _ = _game()
    state.inventory = [Item(id="w1", kind="sword")]
    with pytest.raises(actions.InvalidAction):
        actions.use(state, "w1")


def test_equip_sword_increases_attack_damage() -> None:
    state, _ = _game()
    p = state.player
    target = make_enemy("goblin", 0, p.x + 5, p.y)

    base = _damage(state, p, target)
    state.inventory = [Item(id="w1", kind="sword")]
    actions.equip(state, "w1")
    boosted = _damage(state, p, target)

    assert boosted == base + 3
    assert state.equipped["weapon"].kind == "sword"


def test_equip_shield_reduces_incoming_damage() -> None:
    state, _ = _game()
    p = state.player
    enemy = make_enemy("goblin", 0, p.x + 5, p.y)

    base = _damage(state, enemy, p)  # 적이 플레이어를 때린다
    state.inventory = [Item(id="a1", kind="shield")]
    actions.equip(state, "a1")
    reduced = _damage(state, enemy, p)

    assert reduced == max(1, base - 2)


def test_equip_swaps_and_returns_previous_to_bag() -> None:
    state, _ = _game()
    state.inventory = [Item(id="w1", kind="sword"), Item(id="w2", kind="sword")]

    actions.equip(state, "w1")
    actions.equip(state, "w2")

    assert state.equipped["weapon"].id == "w2"
    assert [it.id for it in state.inventory] == ["w1"], "쓰던 무기가 가방으로 돌아와야 한다"


def test_enemies_ignore_player_equipment() -> None:
    """장착 보너스는 플레이어만 받는다 — 적의 공격/방어에는 반영되지 않는다."""
    state, _ = _game()
    p = state.player
    enemy = make_enemy("goblin", 0, p.x + 5, p.y)
    state.equipped = {"weapon": Item(id="w", kind="sword"), "armor": Item(id="a", kind="shield")}

    # 적이 적을 때리는 상황엔 플레이어 장착이 끼어들지 않는다.
    other = make_enemy("goblin", 1, p.x + 6, p.y)
    assert _damage(state, enemy, other) == max(1, enemy.atk - other.def_)
