"""턴 시스템 v2 (에너지 스케줄러) 테스트.

docs/04_turn_system_pivot.md가 예고한 대로, 이 파일이 v1의 tests/test_turn_v1.py를
대체한다. 두 축을 검증한다:

1. v2가 새로 표현하는 것 — speed 비율대로 갈리는 행동 빈도 (v1은 못 했다).
2. 전환에도 살아남아야 하는 것 — 결정론, 전투/XP, 층 이동, invalid action 계약.

속도가 모두 같은(goblin 100) 층에서는 v2가 v1과 동일하게 "각자 1회"로 환원된다.
파열은 속도가 갈릴 때만 드러난다.
"""

from __future__ import annotations

import pytest

from engine import actions, turn
from engine.state import ENERGY_THRESHOLD, MAX_FLOOR, STAIRS, make_enemy


def _fresh(seed: int = 42):
    return turn.new_game("t", seed)


# --------------------------------------------------------------------------- #
# v2가 새로 표현하는 것 — 속도 비율                                            #
# --------------------------------------------------------------------------- #


def _idle_action_log(kinds: list[str], turns: int) -> tuple[list, list[dict]]:
    """적들을 시야 밖에 세워 idle시키고 플레이어가 `turns`번 대기하며 적별 행동을 센다.

    시야 밖이라 매 행동은 wait(actor=적 id)로 찍힌다. 반환: (enemies, per_turn) —
    per_turn[i]는 i번째 입력 사이 각 적이 행동한 횟수.
    """
    state, rng = turn.new_game("ratio", 42)
    player = state.player
    enemies = [
        make_enemy(k, i, player.x + 20, player.y + i) for i, k in enumerate(kinds)
    ]
    state.actors = [player] + enemies

    per_turn: list[dict] = []
    for _ in range(turns):
        events = turn.process_turn(state, rng, {"type": "wait"})
        counts = {e.id: 0 for e in enemies}
        for ev in events:
            if ev["actor"] in counts:
                counts[ev["actor"]] += 1
        per_turn.append(counts)
    return enemies, per_turn


def test_action_count_scales_with_speed() -> None:
    """장기적으로 적의 행동 횟수는 speed에 비례한다: Rat 150 > Goblin 100 > Golem 60.

    (v1에서는 셋 다 동률이라 실패했다 — 이 테스트의 통과가 v2 전환의 정의다.)
    """
    _, per_turn = _idle_action_log(["rat", "goblin", "golem"], turns=60)
    total = {"rat#0": 0, "goblin#1": 0, "golem#2": 0}
    for c in per_turn:
        for k in total:
            total[k] += c[k]

    assert total["rat#0"] > total["goblin#1"] > total["golem#2"]
    # 60입력 동안 speed 비율(1.5 : 1 : 0.6)대로: 90 / 60 / 36.
    assert (total["rat#0"], total["goblin#1"], total["golem#2"]) == (90, 60, 36)


def test_fast_enemy_can_act_twice_between_inputs() -> None:
    """Rat(150)은 어떤 한 입력 사이에 2번 행동할 수 있다 (v1은 항상 1이었다)."""
    _, per_turn = _idle_action_log(["rat"], turns=4)
    assert max(c["rat#0"] for c in per_turn) >= 2


def test_slow_enemy_sometimes_skips_a_turn() -> None:
    """Golem(60)은 어떤 입력 사이에는 아예 행동하지 못한다 (energy가 안 찬다)."""
    _, per_turn = _idle_action_log(["golem"], turns=4)
    assert any(c["golem#0"] == 0 for c in per_turn)


def test_same_speed_reduces_to_lockstep() -> None:
    """속도가 모두 같으면(goblin 100) v2는 v1과 동일하게 '각자 정확히 1회'가 된다."""
    enemies, per_turn = _idle_action_log(["goblin", "goblin", "goblin"], turns=5)
    for c in per_turn:
        assert all(c[e.id] == 1 for e in enemies)


# --------------------------------------------------------------------------- #
# 전환에도 살아남아야 하는 것 — 결정론                                          #
# --------------------------------------------------------------------------- #


def test_new_game_is_deterministic() -> None:
    a, _ = _fresh(42)
    b, _ = _fresh(42)
    assert a.map.tiles == b.map.tiles
    assert (a.player.x, a.player.y) == (b.player.x, b.player.y)
    assert a.seed == b.seed == 42


def test_seed_is_generated_when_absent() -> None:
    state, _ = turn.new_game("t", None)
    assert isinstance(state.seed, int)  # 응답에 항상 시드가 실린다 (버그 재현의 전제)


def test_same_seed_same_events() -> None:
    """같은 시드 + 같은 입력열 → 완전히 동일한 events 순서 (정수 스케줄러의 결정론).

    BQ1·BQ2가 여기 걸려 있다: events가 재현되지 않으면 버그를 규약대로 저장할 수 없다.
    """
    inputs = [{"type": "wait"}] * 12

    def play(seed: int) -> list:
        state, rng = turn.new_game("d", seed)
        out = []
        for a in inputs:
            out.append(turn.process_turn(state, rng, a))
        return out

    assert play(2026) == play(2026)


# --------------------------------------------------------------------------- #
# 전환에도 살아남아야 하는 것 — 전투 / 진행 / 계약                              #
# --------------------------------------------------------------------------- #


def test_invalid_action_consumes_neither_turn_nor_energy() -> None:
    """성립하지 않는 행동은 turn도 energy도 소비하지 않는다 (v1과 동일한 계약)."""
    state, rng = _fresh(42)
    room = state.map.rooms[0]
    rx, ry, _, _ = room
    state.player.x, state.player.y = rx, ry  # 방 좌상단 모서리 → 북/서가 벽

    blocked = next(
        name
        for name, (dx, dy) in actions.DIRECTIONS.items()
        if not state.map.walkable(state.player.x + dx, state.player.y + dy)
    )
    turn_before = state.turn
    energy_before = state.player.energy

    with pytest.raises(actions.InvalidAction):
        turn.process_turn(state, rng, {"type": "move", "dir": blocked})

    assert state.turn == turn_before
    assert state.player.energy == energy_before


def test_moving_into_enemy_is_an_attack() -> None:
    state, rng = _fresh(42)
    player = state.player
    target = make_enemy("goblin", 0, player.x + 1, player.y)
    state.actors = [player, target]  # 격리 — advance의 다른 적 이동 잡음 제거
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
    enemy = make_enemy("goblin", 0, player.x + 1, player.y)
    state.actors = [player, enemy]

    turn.process_turn(state, rng, {"type": "wait"})

    assert state.status == "dead"
    assert player.hp <= 0


def test_death_mid_advance_stops_immediately() -> None:
    """플레이어가 내부 진행 중 죽으면 그 자리에서 중단한다 (이후 적 행동 없음)."""
    state, rng = _fresh(42)
    player = state.player
    player.hp = 1
    player.def_ = 0
    # 인접한 적 둘. 첫 적이 플레이어를 죽이면 둘째 적은 행동하지 못해야 한다.
    e1 = make_enemy("goblin", 0, player.x + 1, player.y)
    e2 = make_enemy("goblin", 1, player.x - 1, player.y)
    state.actors = [player, e1, e2]

    events = turn.process_turn(state, rng, {"type": "wait"})

    assert state.status == "dead"
    attackers = [e["actor"] for e in events if e["t"] == "attack"]
    assert "goblin#1" not in attackers, "죽은 뒤 둘째 적이 행동하면 안 된다"


def test_killing_enemy_grants_xp() -> None:
    state, rng = _fresh(42)
    player = state.player
    player.atk = 999  # 한 방
    target = make_enemy("goblin", 0, player.x + 1, player.y)
    state.actors = [player, target]

    events = turn.process_turn(state, rng, {"type": "move", "dir": "east"})

    assert any(e["t"] == "death" for e in events)
    assert state.player_xp == 8, "goblin 처치 XP"
    assert state.level == 1  # 8 < 10 → 아직 레벨업 아님
    assert not any(e["t"] == "levelup" for e in events)


def test_second_kill_levels_up() -> None:
    state, rng = _fresh(42)
    player = state.player
    player.atk = 999
    hp_before, atk_before = player.max_hp, player.atk

    g1 = make_enemy("goblin", 0, player.x + 1, player.y)
    g2 = make_enemy("goblin", 1, player.x + 20, player.y)  # 처음엔 시야 밖
    state.actors = [player, g1, g2]

    turn.process_turn(state, rng, {"type": "move", "dir": "east"})  # g1 처치
    g2.x, g2.y = player.x + 1, player.y
    turn.process_turn(state, rng, {"type": "move", "dir": "east"})  # g2 처치

    assert state.level == 2, "XP 16 >= 10 → 레벨업"
    assert player.max_hp == hp_before + 5
    assert player.atk == atk_before + 1
    assert player.def_ == 3, "2레벨마다 DEF +1"


# --------------------------------------------------------------------------- #
# 전환에도 살아남아야 하는 것 — 층 이동 (에너지 리셋 규칙 포함)                 #
# --------------------------------------------------------------------------- #


def test_descend_requires_stairs() -> None:
    state, rng = _fresh(42)
    with pytest.raises(actions.InvalidAction):
        turn.process_turn(state, rng, {"type": "descend"})


def test_descend_advances_floor_and_resets_energy() -> None:
    state, rng = _fresh(42)
    player = state.player
    player.hp = 7  # 층을 넘어가도 유지되어야 한다

    _teleport_to_stairs(state)
    events = turn.process_turn(state, rng, {"type": "descend"})

    assert state.floor == 2
    assert any(e["t"] == "floor" for e in events)
    assert state.player is player, "플레이어 객체가 교체되면 HP/레벨이 초기화된다"
    assert state.player.hp == 7
    # 새 층은 에너지 경제를 리셋한다 — 플레이어는 바로 행동 가능해야 한다.
    assert state.player.energy == ENERGY_THRESHOLD


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
