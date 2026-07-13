"""행동 해석 — 한 액터의 한 행동을 상태에 적용한다.

이동하려는 칸에 적이 있으면 = 공격 (별도 attack 명령이 없다). 로그라이크 관례이고,
플레이어와 적이 같은 코드를 쓴다.
"""

from __future__ import annotations

from engine import combat
from engine.state import STAIRS, Actor, GameState

DIRECTIONS: dict[str, tuple[int, int]] = {
    "north": (0, -1),
    "south": (0, 1),
    "west": (-1, 0),
    "east": (1, 0),
    "northwest": (-1, -1),
    "northeast": (1, -1),
    "southwest": (-1, 1),
    "southeast": (1, 1),
}


class InvalidAction(Exception):
    """행동 자체가 성립하지 않는다 (턴을 소비하지 않는다)."""


def move_or_attack(state: GameState, actor: Actor, dx: int, dy: int) -> list[dict]:
    if dx == 0 and dy == 0:
        return wait(state, actor)

    nx, ny = actor.x + dx, actor.y + dy

    if not state.map.walkable(nx, ny):
        raise InvalidAction("벽이다")

    target = state.actor_at(nx, ny)
    if target is not None:
        if target is actor:
            raise InvalidAction("자기 자신")
        return combat.attack(state, actor, target)

    actor.x, actor.y = nx, ny
    return [{"t": "move", "actor": actor.id, "to": [nx, ny]}]


def wait(state: GameState, actor: Actor) -> list[dict]:
    return [{"t": "wait", "actor": actor.id}]


def descend(state: GameState) -> list[dict]:
    """계단 위에서만 가능. 다음 층은 turn 레이어가 생성한다."""
    player = state.player
    if state.map.tiles[player.y][player.x] != STAIRS:
        raise InvalidAction("계단 위가 아니다")
    return [{"t": "descend", "actor": player.id}]
