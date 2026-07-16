"""아이템 스펙과 순수 헬퍼. (엔티티: "인벤토리")

여기에는 **검증도 InvalidAction도 없다.** pickup/use/equip의 규칙과 거부는
engine/actions.py가 한다 — items가 actions를 import하면 순환이 되기 때문이다
(actions → combat → items). items는 state만 의존하는 잎(leaf) 모듈로 둔다.

장착 보너스는 combat이 effective_atk/effective_def로 참조한다. 이 인벤토리가
GameState에 들어오면서 세이브 포맷이 v1 → v2로 올라간다 (BQ3, docs/02 §5).
"""

from __future__ import annotations

from engine.state import GameState, Item

# docs/02_game_design.md §5
ITEM_SPECS: dict[str, dict] = {
    "potion": {"glyph": "!", "name": "포션", "slot": None},
    "sword": {"glyph": "/", "name": "검", "slot": "weapon", "atk": 3},
    "shield": {"glyph": "[", "name": "방패", "slot": "armor", "def": 2},
    "scroll": {"glyph": "?", "name": "귀환 스크롤", "slot": None},
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
    """플레이어는 장착 무기 보너스를 더한다. 적은 장착이 없다."""
    base = actor.atk
    return base + _bonus(state.equipped.get("weapon"), "atk") if actor.is_player else base


def effective_def(state: GameState, actor) -> int:
    base = actor.def_
    return base + _bonus(state.equipped.get("armor"), "def") if actor.is_player else base
