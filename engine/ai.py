
from __future__ import annotations

from engine.state import Actor, GameState

SIGHT = 8



FLEE_POLICY: dict[str, int | None] = {
    "rat": None,
    "goblin": 30,
    "golem": None,
}


def decide(state: GameState, enemy: Actor) -> tuple[int, int]:
    player = state.player

    if _chebyshev(enemy, player) > SIGHT:
        return (0, 0)

    if _should_flee(enemy):
        return _step_away(state, enemy, player)  # flee

    return _step_toward(state, enemy, player)  # chase


def _should_flee(enemy: Actor) -> bool:
    threshold = FLEE_POLICY.get(enemy.kind)
    if threshold is None:
        return False
    return enemy.hp * 100 <= enemy.max_hp * threshold


def _chebyshev(a: Actor, b: Actor) -> int:
    return max(abs(a.x - b.x), abs(a.y - b.y))


def _sign(n: int) -> int:
    return (n > 0) - (n < 0)


def _step_toward(state: GameState, enemy: Actor, target: Actor) -> tuple[int, int]:
    dx = _sign(target.x - enemy.x)
    dy = _sign(target.y - enemy.y)


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
    return (0, 0)


def _can_step(
    state: GameState, enemy: Actor, step: tuple[int, int], target: Actor
) -> bool:
    nx, ny = enemy.x + step[0], enemy.y + step[1]

    if not state.map.walkable(nx, ny):
        return False

    occupant = state.actor_at(nx, ny)
    if occupant is None:
        return True


    return occupant is target
