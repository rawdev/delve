
from __future__ import annotations

from engine.state import GameState, Item

# docs/02_game_design.md §5
ITEM_SPECS: dict[str, dict] = {
    "potion": {"glyph": "!", "name": "Potion", "slot": None},
    "sword": {"glyph": "/", "name": "Sword", "slot": "weapon", "atk": 3},
    "shield": {"glyph": "[", "name": "Shield", "slot": "armor", "def": 2},
    "scroll": {"glyph": "?", "name": "Recall Scroll", "slot": None},
}

POTION_HEAL = 10
INVENTORY_MAX = 10
EQUIP_SLOTS = ("weapon", "armor")


def glyph_of(kind: str) -> str:
    return ITEM_SPECS[kind]["glyph"]


def name_of(kind: str) -> str:
    return ITEM_SPECS[kind]["name"]


def slot_of(kind: str) -> str | None:
    return ITEM_SPECS[kind]["slot"]


def _bonus(item: Item | None, key: str) -> int:
    if item is None:
        return 0
    return ITEM_SPECS[item.kind].get(key, 0)


def effective_atk(state: GameState, actor) -> int:
    base = actor.atk
    return base + _bonus(state.equipped.get("weapon"), "atk") if actor.is_player else base


def effective_def(state: GameState, actor) -> int:
    base = actor.def_
    return base + _bonus(state.equipped.get("armor"), "def") if actor.is_player else base
