
from __future__ import annotations

from engine import items
from engine.state import Actor, GameState


LEVEL_XP_FACTOR = 10


def attack(state: GameState, attacker: Actor, target: Actor) -> list[dict]:
    dmg = max(1, items.effective_atk(state, attacker) - items.effective_def(state, target))
    target.hp -= dmg

    events: list[dict] = [
        {"t": "attack", "actor": attacker.id, "target": target.id, "dmg": dmg}
    ]
    state.log.append(f"{_name(attacker)} dealt {dmg} damage to {_name(target)}.")

    if not target.alive:
        events.append({"t": "death", "actor": target.id})
        state.log.append(f"{_name(target)} fell!")

        if target.is_player:
            state.status = "dead"
            state.log.append("You died. (permadeath)")
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
        state.log.append(f"Level {state.level}! (HP+5, ATK+1)")

    return events


def _name(actor: Actor) -> str:
    return "You" if actor.is_player else actor.kind.capitalize()
