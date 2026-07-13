"""적 AI — 상태머신 (idle / chase / flee).

Phase 1은 Goblin 1종뿐이다. Phase 2에서 이 모듈은 ChatGPT 설계 · Claude Code 구현 ·
Gemini 리뷰로 다시 다뤄진다 (IQ1의 재료).

`decide()`는 (dx, dy)만 돌려준다 — 실제 이동/공격은 actions/turn이 한다.
이 인터페이스를 유지하면 Phase 2의 턴 시스템 전환 때 ai.py는 **변경 없이 살아남는다.**
레이어 분리의 배당금이다 (docs/04_turn_system_pivot.md §4).
"""

from __future__ import annotations

from engine.state import Actor, GameState

FLEE_HP_RATIO = 0.3  # HP가 30% 이하면 도망
SIGHT = 8  # 적의 시야 (플레이어 FOV와 같은 반경)


def decide(state: GameState, enemy: Actor) -> tuple[int, int]:
    """이 적이 이번 행동에 움직일 방향. (0, 0)이면 대기."""
    player = state.player
    dist = _chebyshev(enemy, player)

    if dist > SIGHT:
        return (0, 0)  # idle — 플레이어를 못 봤다

    if enemy.hp <= enemy.max_hp * FLEE_HP_RATIO:
        return _step_away(state, enemy, player)  # flee

    return _step_toward(state, enemy, player)  # chase


def _chebyshev(a: Actor, b: Actor) -> int:
    return max(abs(a.x - b.x), abs(a.y - b.y))


def _sign(n: int) -> int:
    return (n > 0) - (n < 0)


def _step_toward(state: GameState, enemy: Actor, target: Actor) -> tuple[int, int]:
    dx = _sign(target.x - enemy.x)
    dy = _sign(target.y - enemy.y)

    # 대각선 우선. 막히면 축 하나씩 시도한다.
    for cand in ((dx, dy), (dx, 0), (0, dy)):
        if cand == (0, 0):
            continue
        if _can_step(state, enemy, cand, target):
            return cand
    return (0, 0)


def _step_away(state: GameState, enemy: Actor, target: Actor) -> tuple[int, int]:
    dx = -_sign(target.x - enemy.x)
    dy = -_sign(target.y - enemy.y)

    for cand in ((dx, dy), (dx, 0), (0, dy)):
        if cand == (0, 0):
            continue
        if _can_step(state, enemy, cand, target):
            return cand
    return (0, 0)  # 구석에 몰렸다 — 대기(= 맞고 있는다)


def _can_step(
    state: GameState, enemy: Actor, step: tuple[int, int], target: Actor
) -> bool:
    nx, ny = enemy.x + step[0], enemy.y + step[1]

    if not state.map.walkable(nx, ny):
        return False

    occupant = state.actor_at(nx, ny)
    if occupant is None:
        return True

    # 플레이어가 있는 칸으로 "이동"하면 그게 공격이다. 다른 적은 통과 못 한다.
    return occupant is target
