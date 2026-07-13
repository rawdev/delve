"""전투 판정.

    데미지 = max(1, 공격자.atk - 방어자.def_)

명중 판정 없음(항상 명중), 크리티컬 없음, 무작위 없음. **의도적으로 단순하다.**

전투의 복잡도는 수치가 아니라 **턴 순서**에서 나온다. 그게 이 게임의 유일한 전술적
깊이고, 동시에 Phase 2 전환점이 겨냥하는 지점이다 (docs/02_game_design.md §4).

무작위가 없으므로 Rng를 받지 않는다 — 재현 표면적이 그만큼 줄어든다.
"""

from __future__ import annotations

from engine.state import Actor, GameState

# XP 곡선: 레벨업에 필요한 누적 XP = LEVEL_XP_FACTOR * level
LEVEL_XP_FACTOR = 10


def attack(state: GameState, attacker: Actor, target: Actor) -> list[dict]:
    """공격 1회. 발생한 이벤트 목록을 돌려준다."""
    dmg = max(1, attacker.atk - target.def_)
    target.hp -= dmg

    events: list[dict] = [
        {"t": "attack", "actor": attacker.id, "target": target.id, "dmg": dmg}
    ]
    state.log.append(f"{_name(attacker)}이(가) {_name(target)}에게 {dmg} 피해.")

    if not target.alive:
        events.append({"t": "death", "actor": target.id})
        state.log.append(f"{_name(target)} 쓰러짐!")

        if target.is_player:
            state.status = "dead"
            state.log.append("당신은 죽었다. (permadeath)")
        elif attacker.is_player:
            events += _gain_xp(state, target.xp)

    return events


def _gain_xp(state: GameState, amount: int) -> list[dict]:
    state.player_xp += amount
    events: list[dict] = []

    while state.player_xp >= LEVEL_XP_FACTOR * state.level:
        state.player_xp -= LEVEL_XP_FACTOR * state.level
        state.level += 1

        player = state.player
        player.max_hp += 5
        player.hp += 5
        player.atk += 1
        if state.level % 2 == 0:
            player.def_ += 1

        events.append({"t": "levelup", "level": state.level})
        state.log.append(f"레벨 {state.level}! (HP+5, ATK+1)")

    return events


def _name(actor: Actor) -> str:
    return "당신" if actor.is_player else actor.kind
