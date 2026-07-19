
from __future__ import annotations

from engine.rng import Rng
from engine.state import (
    FLOOR,
    MAP_H,
    MAP_W,
    STAIRS,
    WALL,
    Actor,
    ItemOnFloor,
    Map,
    make_enemy,
    make_player,
)







FLOOR_PARAMS: dict[int, dict] = {
    1: {"rooms": (6, 8),  "enemies": {"rat": 2, "goblin": 1}, "items": 3},
    2: {"rooms": (6, 9),  "enemies": {"rat": 2, "goblin": 3, "golem": 1}, "items": 3},
    3: {"rooms": (7, 9),  "enemies": {"rat": 2, "goblin": 4, "golem": 2}, "items": 2},
    4: {"rooms": (7, 10), "enemies": {"rat": 2, "goblin": 4, "golem": 4}, "items": 2},
    5: {"rooms": (5, 6),  "enemies": {"rat": 1, "goblin": 2, "golem": 3}, "items": 2},
}

ROOM_MIN = 5
ROOM_MAX = 12
MAX_PLACEMENT_TRIES = 200


ITEM_POOL = ["potion", "potion", "potion", "sword", "shield", "scroll"]



ENEMY_KINDS = ("rat", "goblin", "golem")




LAYOUT_NS = "dungeon/layout/v1"
ITEMS_NS = "dungeon/items/v1"
ENEMIES_NS = "dungeon/enemies/v1"


def _overlaps(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return (
        ax - 1 < bx + bw
        and ax + aw + 1 > bx
        and ay - 1 < by + bh
        and ay + ah + 1 > by
    )


def _center(room: tuple[int, int, int, int]) -> tuple[int, int]:
    x, y, w, h = room
    return x + w // 2, y + h // 2


def _carve_room(tiles: list[list[str]], room: tuple[int, int, int, int]) -> None:
    x, y, w, h = room
    for ty in range(y, y + h):
        for tx in range(x, x + w):
            tiles[ty][tx] = FLOOR


def _carve_h(tiles: list[list[str]], x1: int, x2: int, y: int) -> None:
    for x in range(min(x1, x2), max(x1, x2) + 1):
        tiles[y][x] = FLOOR


def _carve_v(tiles: list[list[str]], y1: int, y2: int, x: int) -> None:
    for y in range(min(y1, y2), max(y1, y2) + 1):
        tiles[y][x] = FLOOR


def _carve_corridor(
    tiles: list[list[str]], a: tuple[int, int], b: tuple[int, int], rng: Rng
) -> None:
    (x1, y1), (x2, y2) = a, b
    if rng.chance(0.5):
        _carve_h(tiles, x1, x2, y1)
        _carve_v(tiles, y1, y2, x2)
    else:
        _carve_v(tiles, y1, y2, x1)
        _carve_h(tiles, x1, x2, y2)


def generate(floor: int, rng: Rng) -> tuple[Map, list[Actor], list[ItemOnFloor]]:
    params = FLOOR_PARAMS[floor]

    layout_rng = rng.derive(LAYOUT_NS, floor)
    items_rng = rng.derive(ITEMS_NS, floor)
    enemies_rng = rng.derive(ENEMIES_NS, floor)


    tiles = [[WALL for _ in range(MAP_W)] for _ in range(MAP_H)]
    rooms: list[tuple[int, int, int, int]] = []

    target = layout_rng.randint(*params["rooms"])
    tries = 0
    while len(rooms) < target and tries < MAX_PLACEMENT_TRIES:
        tries += 1
        w = layout_rng.randint(ROOM_MIN, ROOM_MAX)
        h = layout_rng.randint(ROOM_MIN, min(ROOM_MAX, MAP_H - 4))
        x = layout_rng.randint(1, MAP_W - w - 2)
        y = layout_rng.randint(1, MAP_H - h - 2)
        room = (x, y, w, h)
        if any(_overlaps(room, other) for other in rooms):
            continue
        _carve_room(tiles, room)
        if rooms:
            _carve_corridor(tiles, _center(rooms[-1]), _center(room), layout_rng)
        rooms.append(room)


    px, py = _center(rooms[0])
    sx, sy = _center(rooms[-1])
    tiles[sy][sx] = STAIRS

    spawn_rooms = rooms[1:] or rooms
    reserved = {(px, py), (sx, sy)}


    floor_items: list[ItemOnFloor] = []
    for i in range(params.get("items", 0)):
        for _ in range(50):
            rx, ry, rw, rh = items_rng.choice(spawn_rooms)
            ix = items_rng.randint(rx, rx + rw - 1)
            iy = items_rng.randint(ry, ry + rh - 1)
            if (ix, iy) not in reserved:
                reserved.add((ix, iy))
                floor_items.append(


                    ItemOnFloor(
                        id=f"f{floor}-item#{i}",
                        kind=items_rng.choice(ITEM_POOL),
                        x=ix,
                        y=iy,
                    )
                )
                break


    actors: list[Actor] = [make_player(px, py)]
    occupied = set(reserved)


    roster: list[str] = []
    for kind in ENEMY_KINDS:
        roster += [kind] * params["enemies"].get(kind, 0)

    for i, kind in enumerate(roster):
        for _ in range(50):
            rx, ry, rw, rh = enemies_rng.choice(spawn_rooms)
            ex = enemies_rng.randint(rx, rx + rw - 1)
            ey = enemies_rng.randint(ry, ry + rh - 1)
            if (ex, ey) not in occupied:
                occupied.add((ex, ey))
                actors.append(make_enemy(kind, i, ex, ey))
                break

    game_map = Map(
        tiles=tiles,
        explored=[[False] * MAP_W for _ in range(MAP_H)],
        visible=[[False] * MAP_W for _ in range(MAP_H)],
        rooms=rooms,
    )
    return game_map, actors, floor_items
