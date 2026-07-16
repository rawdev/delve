"""행동 해석 — 한 액터의 한 행동을 상태에 적용한다.

이동하려는 칸에 적이 있으면 = 공격 (별도 attack 명령이 없다). 로그라이크 관례이고,
플레이어와 적이 같은 코드를 쓴다.
"""

from __future__ import annotations

from engine import combat, items
from engine.state import STAIRS, Actor, GameState, Item

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


def pickup(state: GameState) -> list[dict]:
    """플레이어가 선 칸의 바닥 아이템을 줍는다. 없거나 가방이 가득이면 거부."""
    p = state.player
    here = next((it for it in state.floor_items if it.x == p.x and it.y == p.y), None)
    if here is None:
        raise InvalidAction("주울 것이 없다")
    if len(state.inventory) >= items.INVENTORY_MAX:
        raise InvalidAction("가방이 가득 찼다")

    state.floor_items.remove(here)
    state.inventory.append(Item(id=here.id, kind=here.kind))
    state.log.append(f"{items.name_of(here.kind)}을(를) 주웠다.")
    return [{"t": "pickup", "actor": "player", "item": here.kind}]


def use(state: GameState, item_id: str | None) -> list[dict]:
    """소비 아이템(포션/스크롤)을 쓴다. 장착 아이템은 거부한다."""
    it = _find_in_inventory(state, item_id)

    if it.kind == "potion":
        p = state.player
        healed = min(items.POTION_HEAL, p.max_hp - p.hp)
        p.hp += healed
        state.inventory.remove(it)
        state.log.append(f"포션을 마셨다. HP +{healed}.")
        return [{"t": "use", "actor": "player", "item": "potion", "heal": healed}]

    if it.kind == "scroll":
        sx, sy = _floor_start(state)
        state.player.x, state.player.y = sx, sy
        state.inventory.remove(it)
        state.log.append("귀환 스크롤 — 층 입구로 돌아왔다.")
        return [{"t": "use", "actor": "player", "item": "scroll", "to": [sx, sy]}]

    raise InvalidAction("마실 수 없다 (장착 아이템은 equip)")


def equip(state: GameState, item_id: str | None) -> list[dict]:
    """무기/방어구를 장착한다. 쓰던 건 가방으로 돌아온다."""
    it = _find_in_inventory(state, item_id)
    slot = items.slot_of(it.kind)
    if slot is None:
        raise InvalidAction("장착할 수 없는 아이템")

    state.inventory.remove(it)
    previous = state.equipped.get(slot)
    state.equipped[slot] = Item(id=it.id, kind=it.kind)
    if previous is not None:
        state.inventory.append(previous)
    state.log.append(f"{items.name_of(it.kind)} 장착.")
    return [{"t": "equip", "actor": "player", "slot": slot, "item": it.kind}]


def _find_in_inventory(state: GameState, item_id: str | None) -> Item:
    it = next((x for x in state.inventory if x.id == item_id), None)
    if it is None:
        raise InvalidAction("가방에 그런 아이템이 없다")
    return it


def _floor_start(state: GameState) -> tuple[int, int]:
    x, y, w, h = state.map.rooms[0]  # 플레이어 시작 방 = 첫 방
    return x + w // 2, y + h // 2
