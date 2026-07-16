"""적 AI — 종류별 도주 정책 (idle / chase / flee).

공통 판단 흐름은 '시야 밖이면 정지 → 도주 조건이면 도주 → 그 외 추격'이고, 종류별
차이는 FLEE_POLICY 테이블의 flee_hp_percent 하나로만 표현한다. 규칙을 한곳에서 감사
하기 위해 판단 코드에 kind 조건문을 흩뿌리지 않는다.

설계: @critic(ChatGPT) `evt_81fb3979` / 구현: Claude Code. 엔티티 **"적 AI"** —
IQ1(ChatGPT↔Claude)·IQ2(동료↔소유자)의 재료다.

`decide()`는 (dx, dy)만 돌려준다 — 실제 이동/공격은 actions/turn이 한다. 이 인터페이스를
유지해 턴 시스템 v2 전환에도 ai.py는 살아남았다 (레이어 분리의 배당금).
"""

from __future__ import annotations

from engine.state import Actor, GameState

SIGHT = 8  # 적의 시야 (플레이어 FOV와 같은 반경)

# 종류별 도주 정책 (docs/02 §3, 설계 evt_81fb3979). 값 = 도주를 시작하는 HP 퍼센트.
# None이면 절대 도주하지 않는다. 규칙은 이 테이블 한곳에서만 산다.
FLEE_POLICY: dict[str, int | None] = {
    "rat": None,     # 시야 내 항상 추격
    "goblin": 30,    # HP 30% 이하에서 도주, 초과에서는 추격
    "golem": None,   # 절대 도주하지 않음
}


def decide(state: GameState, enemy: Actor) -> tuple[int, int]:
    """이 적이 이번 행동에 움직일 방향. (0, 0)이면 대기."""
    player = state.player

    if _chebyshev(enemy, player) > SIGHT:
        return (0, 0)  # idle — 플레이어를 못 봤다

    if _should_flee(enemy):
        return _step_away(state, enemy, player)  # flee

    return _step_toward(state, enemy, player)  # chase


def _should_flee(enemy: Actor) -> bool:
    """정책 테이블의 flee_hp_percent로 판정. rng 없이 정수식이라 결정론적이다.

    hp*100 <= max_hp*threshold — 부동소수 없이 '정확히 threshold% 이하'를 판정한다.
    """
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
