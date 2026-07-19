
from __future__ import annotations

import pytest

from engine import actions, turn
from engine.state import ENERGY_THRESHOLD, MAX_FLOOR, STAIRS, make_enemy


def _fresh(seed: int = 42):
    return turn.new_game("t", seed)


# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #


def _idle_action_log(kinds: list[str], turns: int) -> tuple[list, list[dict]]:
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
    _, per_turn = _idle_action_log(["rat", "goblin", "golem"], turns=60)
    total = {"rat#0": 0, "goblin#1": 0, "golem#2": 0}
    for c in per_turn:
        for k in total:
            total[k] += c[k]

    assert total["rat#0"] > total["goblin#1"] > total["golem#2"]

    assert (total["rat#0"], total["goblin#1"], total["golem#2"]) == (90, 60, 36)


def test_fast_enemy_can_act_twice_between_inputs() -> None:
    _, per_turn = _idle_action_log(["rat"], turns=4)
    assert max(c["rat#0"] for c in per_turn) >= 2


def test_slow_enemy_sometimes_skips_a_turn() -> None:
    _, per_turn = _idle_action_log(["golem"], turns=4)
    assert any(c["golem#0"] == 0 for c in per_turn)


def test_same_speed_reduces_to_lockstep() -> None:
    enemies, per_turn = _idle_action_log(["goblin", "goblin", "goblin"], turns=5)
    for c in per_turn:
        assert all(c[e.id] == 1 for e in enemies)


# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #


def test_new_game_is_deterministic() -> None:
    a, _ = _fresh(42)
    b, _ = _fresh(42)
    assert a.map.tiles == b.map.tiles
    assert (a.player.x, a.player.y) == (b.player.x, b.player.y)
    assert a.seed == b.seed == 42


def test_seed_is_generated_when_absent() -> None:
    state, _ = turn.new_game("t", None)
    assert isinstance(state.seed, int)


def test_same_seed_same_events() -> None:
    inputs = [{"type": "wait"}] * 12

    def play(seed: int) -> list:
        state, rng = turn.new_game("d", seed)
        out = []
        for a in inputs:
            out.append(turn.process_turn(state, rng, a))
        return out

    assert play(2026) == play(2026)


# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #


def test_invalid_action_consumes_neither_turn_nor_energy() -> None:
    state, rng = _fresh(42)
    room = state.map.rooms[0]
    rx, ry, _, _ = room
    state.player.x, state.player.y = rx, ry

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
    state.actors = [player, target]
    hp_before = target.hp

    events = turn.process_turn(state, rng, {"type": "move", "dir": "east"})

    assert any(e["t"] == "attack" and e["actor"] == "player" for e in events)
    assert target.hp < hp_before
    assert (player.x, player.y) != (target.x, target.y)


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
    state, rng = _fresh(42)
    player = state.player
    player.hp = 1
    player.def_ = 0

    e1 = make_enemy("goblin", 0, player.x + 1, player.y)
    e2 = make_enemy("goblin", 1, player.x - 1, player.y)
    state.actors = [player, e1, e2]

    events = turn.process_turn(state, rng, {"type": "wait"})

    assert state.status == "dead"
    attackers = [e["actor"] for e in events if e["t"] == "attack"]
    assert "goblin#1" not in attackers


def test_killing_enemy_grants_xp() -> None:
    state, rng = _fresh(42)
    player = state.player
    player.atk = 999
    target = make_enemy("goblin", 0, player.x + 1, player.y)
    state.actors = [player, target]

    events = turn.process_turn(state, rng, {"type": "move", "dir": "east"})

    assert any(e["t"] == "death" for e in events)
    assert state.player_xp == 8
    assert state.level == 1
    assert not any(e["t"] == "levelup" for e in events)


def test_second_kill_levels_up() -> None:
    state, rng = _fresh(42)
    player = state.player
    player.atk = 999
    hp_before, atk_before = player.max_hp, player.atk

    g1 = make_enemy("goblin", 0, player.x + 1, player.y)
    g2 = make_enemy("goblin", 1, player.x + 20, player.y)
    state.actors = [player, g1, g2]

    turn.process_turn(state, rng, {"type": "move", "dir": "east"})
    g2.x, g2.y = player.x + 1, player.y
    turn.process_turn(state, rng, {"type": "move", "dir": "east"})

    assert state.level == 2
    assert player.max_hp == hp_before + 5
    assert player.atk == atk_before + 1
    assert player.def_ == 3


# --------------------------------------------------------------------------- #

# --------------------------------------------------------------------------- #


def test_descend_requires_stairs() -> None:
    state, rng = _fresh(42)
    with pytest.raises(actions.InvalidAction):
        turn.process_turn(state, rng, {"type": "descend"})


def test_descend_advances_floor_and_resets_energy() -> None:
    state, rng = _fresh(42)
    player = state.player
    player.hp = 7

    _teleport_to_stairs(state)
    events = turn.process_turn(state, rng, {"type": "descend"})

    assert state.floor == 2
    assert any(e["t"] == "floor" for e in events)
    assert state.player is player
    assert state.player.hp == 7

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
    assert not state.map.visible[1][1]


def _teleport_to_stairs(state) -> None:
    for y, row in enumerate(state.map.tiles):
        for x, tile in enumerate(row):
            if tile == STAIRS:
                state.player.x, state.player.y = x, y
                return
    raise AssertionError("Stairs not found")
