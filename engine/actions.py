
from __future__ import annotations

from engine import combat, items
from engine.state import MAP_H, MAP_W, STAIRS, Actor, GameState, Item

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
    """Raised when an action is invalid and must not consume a turn."""

    pass


def move_or_attack(state: GameState, actor: Actor, dx: int, dy: int) -> list[dict]:
    if dx == 0 and dy == 0:
        return wait(state, actor)

    nx, ny = actor.x + dx, actor.y + dy

    if not state.map.walkable(nx, ny):
        raise InvalidAction("Blocked by a wall")

    target = state.actor_at(nx, ny)
    if target is not None:
        if target is actor:
            raise InvalidAction("Cannot target yourself")
        return combat.attack(state, actor, target)

    actor.x, actor.y = nx, ny
    return [{"t": "move", "actor": actor.id, "to": [nx, ny]}]


def wait(state: GameState, actor: Actor) -> list[dict]:
    return [{"t": "wait", "actor": actor.id}]


def descend(state: GameState) -> list[dict]:
    player = state.player
    if state.map.tiles[player.y][player.x] != STAIRS:
        raise InvalidAction("You are not standing on the stairs")
    return [{"t": "descend", "actor": player.id}]


def pickup(state: GameState) -> list[dict]:
    p = state.player
    here = next((it for it in state.floor_items if it.x == p.x and it.y == p.y), None)
    if here is None:
        raise InvalidAction("There is nothing to pick up")
    if len(state.inventory) >= items.INVENTORY_MAX:
        raise InvalidAction("Your bag is full")

    state.floor_items.remove(here)
    state.inventory.append(Item(id=here.id, kind=here.kind))
    state.log.append(f"Picked up {items.name_of(here.kind)}.")
    return [{"t": "pickup", "actor": "player", "item": here.kind}]


def use(state: GameState, item_id: str | None) -> list[dict]:
    it = _find_in_inventory(state, item_id)

    if it.kind == "potion":
        p = state.player
        healed = min(items.POTION_HEAL, p.max_hp - p.hp)
        p.hp += healed
        state.inventory.remove(it)
        state.log.append(f"Drank a Potion. HP +{healed}.")
        return [{"t": "use", "actor": "player", "item": "potion", "heal": healed}]

    if it.kind == "scroll":

        sx, sy = _free_tile_near(state, *_floor_start(state))
        state.player.x, state.player.y = sx, sy
        state.inventory.remove(it)
        state.log.append("Used a Recall Scroll and returned to the floor entrance.")
        return [{"t": "use", "actor": "player", "item": "scroll", "to": [sx, sy]}]

    raise InvalidAction("This item cannot be used; equip it instead")


def equip(state: GameState, item_id: str | None) -> list[dict]:
    it = _find_in_inventory(state, item_id)
    slot = items.slot_of(it.kind)
    if slot is None:
        raise InvalidAction("This item cannot be equipped")

    state.inventory.remove(it)
    previous = state.equipped.get(slot)
    state.equipped[slot] = Item(id=it.id, kind=it.kind)
    if previous is not None:
        state.inventory.append(previous)
    state.log.append(f"Equipped {items.name_of(it.kind)}.")
    return [{"t": "equip", "actor": "player", "slot": slot, "item": it.kind}]


def _find_in_inventory(state: GameState, item_id: str | None) -> Item:
    it = next((x for x in state.inventory if x.id == item_id), None)
    if it is None:
        raise InvalidAction("That item is not in your bag")
    return it


def _floor_start(state: GameState) -> tuple[int, int]:
    x, y, w, h = state.map.rooms[0]
    return x + w // 2, y + h // 2


def _free_tile_near(state: GameState, x0: int, y0: int) -> tuple[int, int]:
    best_key: tuple[int, int, int] | None = None
    best_xy = (x0, y0)
    for y in range(MAP_H):
        for x in range(MAP_W):
            if state.map.walkable(x, y) and state.actor_at(x, y) is None:
                key = (max(abs(x - x0), abs(y - y0)), y, x)
                if best_key is None or key < best_key:
                    best_key, best_xy = key, (x, y)
    return best_xy
