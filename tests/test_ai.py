
from __future__ import annotations

from engine import ai
from engine.state import FLOOR, MAP_H, MAP_W, GameState, Map, make_enemy, make_player


def _plain_state(px: int, py: int) -> GameState:
    game_map = Map(
        tiles=[[FLOOR] * MAP_W for _ in range(MAP_H)],
        explored=[[True] * MAP_W for _ in range(MAP_H)],
        visible=[[True] * MAP_W for _ in range(MAP_H)],
        rooms=[(0, 0, MAP_W, MAP_H)],
    )
    return GameState(
        game_id="ai", seed=1, turn=0, floor=1, map=game_map, actors=[make_player(px, py)]
    )


def _enemy_east_of_player(kind: str, hp: int | None = None):
    state = _plain_state(10, 10)
    enemy = make_enemy(kind, 0, 13, 10)
    if hp is not None:
        enemy.hp = hp
    state.actors.append(enemy)
    return state, enemy


def test_rat_chases_even_at_1_hp() -> None:
    state, rat = _enemy_east_of_player("rat", hp=1)
    assert ai.decide(state, rat)[0] == -1


def test_golem_chases_even_at_1_hp() -> None:
    state, golem = _enemy_east_of_player("golem", hp=1)
    assert ai.decide(state, golem)[0] == -1


def test_goblin_flees_at_exactly_30_percent() -> None:
    state, goblin = _enemy_east_of_player("goblin", hp=3)  # max_hp 10 → 30% = 3
    assert ai.decide(state, goblin)[0] == +1


def test_goblin_chases_above_30_percent() -> None:
    state, goblin = _enemy_east_of_player("goblin", hp=4)
    assert ai.decide(state, goblin)[0] == -1


def test_all_kinds_idle_out_of_sight() -> None:
    for kind in ("rat", "goblin", "golem"):
        state = _plain_state(10, 10)
        far = make_enemy(kind, 0, 10 + ai.SIGHT + 2, 10)
        state.actors.append(far)
        assert ai.decide(state, far) == (0, 0)


def test_decide_is_deterministic() -> None:
    for kind in ("rat", "goblin", "golem"):
        s1, e1 = _enemy_east_of_player(kind, hp=5)
        s2, e2 = _enemy_east_of_player(kind, hp=5)
        assert ai.decide(s1, e1) == ai.decide(s2, e2)
