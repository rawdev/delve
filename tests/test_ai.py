"""적 AI 종류별 도주 정책 (설계 evt_81fb3979, 엔티티 "적 AI").

@critic(ChatGPT)가 설계한 인수 조건을 검증한다:
- Rat/Golem은 HP 1에서도 시야 내 추격한다.
- Goblin은 정확히 HP 30%부터 도주하고, 30% 초과에서는 추격한다.
- 시야 밖에서는 모두 정지한다.
- 동일 입력은 동일한 정수 튜플을 반환한다 (rng 없음).
"""

from __future__ import annotations

from engine import ai
from engine.state import FLOOR, MAP_H, MAP_W, GameState, Map, make_enemy, make_player


def _plain_state(px: int, py: int) -> GameState:
    """벽 없는 평지 — 방향 계산만 보기 위한 최소 상태."""
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
    """플레이어 동쪽 3칸(시야 안)에 적을 놓는다. 추격이면 dx=-1(서쪽), 도주면 dx=+1."""
    state = _plain_state(10, 10)
    enemy = make_enemy(kind, 0, 13, 10)
    if hp is not None:
        enemy.hp = hp
    state.actors.append(enemy)
    return state, enemy


def test_rat_chases_even_at_1_hp() -> None:
    state, rat = _enemy_east_of_player("rat", hp=1)
    assert ai.decide(state, rat)[0] == -1  # 플레이어(서쪽)로 다가간다


def test_golem_chases_even_at_1_hp() -> None:
    state, golem = _enemy_east_of_player("golem", hp=1)
    assert ai.decide(state, golem)[0] == -1


def test_goblin_flees_at_exactly_30_percent() -> None:
    state, goblin = _enemy_east_of_player("goblin", hp=3)  # max_hp 10 → 30% = 3
    assert ai.decide(state, goblin)[0] == +1  # 플레이어 반대(동쪽)로 도주


def test_goblin_chases_above_30_percent() -> None:
    state, goblin = _enemy_east_of_player("goblin", hp=4)  # 40% → 추격
    assert ai.decide(state, goblin)[0] == -1


def test_all_kinds_idle_out_of_sight() -> None:
    for kind in ("rat", "goblin", "golem"):
        state = _plain_state(10, 10)
        far = make_enemy(kind, 0, 10 + ai.SIGHT + 2, 10)  # 시야 밖
        state.actors.append(far)
        assert ai.decide(state, far) == (0, 0)


def test_decide_is_deterministic() -> None:
    for kind in ("rat", "goblin", "golem"):
        s1, e1 = _enemy_east_of_player(kind, hp=5)
        s2, e2 = _enemy_east_of_player(kind, hp=5)
        assert ai.decide(s1, e1) == ai.decide(s2, e2)
