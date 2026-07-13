"""턴 시스템 v1 (즉시판정) 테스트.

이 파일의 핵심은 `test_v1_every_enemy_acts_exactly_once`다.
**Phase 2에서 에너지 스케줄러로 전환하면 이 테스트는 깨져야 한다** — 그게 전환이
실제로 일어났다는 증거다. 그때 이 파일은 tests/test_turn.py(속도 비율 검증)로
대체된다. docs/04_turn_system_pivot.md
"""

from __future__ import annotations

import pytest

from engine import actions, turn
from engine.state import FLOOR, MAX_FLOOR, STAIRS, make_enemy


def _fresh(seed: int = 42):
    return turn.new_game("t", seed)


def test_new_game_is_deterministic() -> None:
    a, _ = _fresh(42)
    b, _ = _fresh(42)
    assert a.map.tiles == b.map.tiles
    assert (a.player.x, a.player.y) == (b.player.x, b.player.y)
    assert a.seed == b.seed == 42


def test_seed_is_generated_when_absent() -> None:
    state, _ = turn.new_game("t", None)
    assert isinstance(state.seed, int)  # 응답에 항상 시드가 실린다 (버그 재현의 전제)


def test_v1_every_enemy_acts_exactly_once() -> None:
    """★ v1의 정의 — 플레이어 1입력 = 모든 적이 각각 정확히 1회 행동.

    적을 플레이어에게서 멀리 떨어뜨려 두면 전부 idle(wait)이 되므로,
    이벤트에 찍힌 액터 수가 곧 '행동한 적의 수'다.
    """
    state, rng = _fresh(42)

    # 모든 적을 시야(8) 밖으로 옮긴다 → 전부 idle → 각각 wait 이벤트 정확히 1개
    for i, e in enumerate(state.enemies):
        e.x, e.y = state.player.x + 20, state.player.y + i

    enemy_ids = [e.id for e in state.enemies]
    events = turn.process_turn(state, rng, {"type": "wait"})

    acted = [e["actor"] for e in events if e["actor"] != "player"]
    assert sorted(acted) == sorted(enemy_ids), "모든 적이 정확히 1회씩 행동해야 한다"


def test_v1_has_no_speed_concept() -> None:
    """v1 Actor에는 speed/energy가 없다.

    지금 필드를 넣어두면 Phase 2의 전환이 '아키텍처 전환'이 아니라 '필드 활성화'가
    된다. 그러면 결정 사슬이 안 생기고 DQ1이 죽는다 (docs/09_risks_checklist.md R4).
    """
    state, _ = _fresh()
    player = state.player
    assert not hasattr(player, "speed")
    assert not hasattr(player, "energy")


def test_move_into_wall_does_not_consume_turn() -> None:
    state, rng = _fresh(42)

    # 플레이어는 방 중앙에서 시작하므로 인접한 벽이 없다. 벽에 붙여 놓는다.
    room = state.map.rooms[0]
    rx, ry, _, _ = room
    state.player.x, state.player.y = rx, ry  # 방의 좌상단 모서리 → 북/서가 벽

    blocked = next(
        name
        for name, (dx, dy) in actions.DIRECTIONS.items()
        if not state.map.walkable(state.player.x + dx, state.player.y + dy)
    )
    before = state.turn

    with pytest.raises(actions.InvalidAction):
        turn.process_turn(state, rng, {"type": "move", "dir": blocked})

    assert state.turn == before, "성립하지 않은 행동은 턴을 소비하지 않는다"


def test_moving_into_enemy_is_an_attack() -> None:
    state, rng = _fresh(42)
    player = state.player

    # 플레이어 바로 동쪽에 적을 놓는다
    target = state.enemies[0]
    target.x, target.y = player.x + 1, player.y
    hp_before = target.hp

    events = turn.process_turn(state, rng, {"type": "move", "dir": "east"})

    assert any(e["t"] == "attack" and e["actor"] == "player" for e in events)
    assert target.hp < hp_before
    assert (player.x, player.y) != (target.x, target.y), "공격은 이동이 아니다"


def test_player_death_sets_status() -> None:
    state, rng = _fresh(42)
    player = state.player
    player.hp = 1
    player.def_ = 0

    enemy = state.enemies[0]
    enemy.x, enemy.y = player.x + 1, player.y

    turn.process_turn(state, rng, {"type": "wait"})

    assert state.status == "dead"
    assert player.hp <= 0


def test_killing_enemy_grants_xp() -> None:
    state, rng = _fresh(42)
    player = state.player
    player.atk = 999  # 한 방

    target = state.enemies[0]
    target.x, target.y = player.x + 1, player.y

    events = turn.process_turn(state, rng, {"type": "move", "dir": "east"})

    assert any(e["t"] == "death" for e in events)
    assert state.player_xp == 8, "goblin 처치 XP"
    # Goblin 하나(8)로는 레벨업(10 * level = 10)에 못 미친다 — 두 마리째에 오른다.
    assert state.level == 1
    assert not any(e["t"] == "levelup" for e in events)


def test_second_kill_levels_up() -> None:
    state, rng = _fresh(42)
    player = state.player
    player.atk = 999
    hp_before, atk_before = player.max_hp, player.atk

    for target in state.enemies[:2]:
        target.x, target.y = player.x + 1, player.y
        turn.process_turn(state, rng, {"type": "move", "dir": "east"})

    assert state.level == 2, "XP 16 >= 10 → 레벨업"
    assert player.max_hp == hp_before + 5
    assert player.atk == atk_before + 1
    assert player.def_ == 3, "2레벨마다 DEF +1"


def test_descend_requires_stairs() -> None:
    state, rng = _fresh(42)
    with pytest.raises(actions.InvalidAction):
        turn.process_turn(state, rng, {"type": "descend"})


def test_descend_advances_floor_and_keeps_player() -> None:
    state, rng = _fresh(42)
    player = state.player
    player.hp = 7  # 층을 넘어가도 유지되어야 한다

    _teleport_to_stairs(state)
    events = turn.process_turn(state, rng, {"type": "descend"})

    assert state.floor == 2
    assert any(e["t"] == "floor" for e in events)
    assert state.player is player, "플레이어 객체가 교체되면 HP/레벨이 초기화된다"
    assert state.player.hp == 7


def test_clearing_last_floor_wins() -> None:
    state, rng = _fresh(42)
    state.floor = MAX_FLOOR

    _teleport_to_stairs(state)
    events = turn.process_turn(state, rng, {"type": "descend"})

    assert state.status == "won"
    assert any(e["t"] == "win" for e in events)


def test_fov_marks_explored() -> None:
    state, _ = _fresh(42)
    p = state.player
    assert state.map.visible[p.y][p.x]
    assert state.map.explored[p.y][p.x]
    assert not state.map.visible[1][1], "먼 구석이 보이면 안 된다"


def _teleport_to_stairs(state) -> None:
    for y, row in enumerate(state.map.tiles):
        for x, tile in enumerate(row):
            if tile == STAIRS:
                state.player.x, state.player.y = x, y
                return
    raise AssertionError("계단이 없다")
