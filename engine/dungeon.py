"""던전 생성 — 랜덤 방 배치 + 겹침 거부 + L자 복도.

BSP는 기각했다 (과설계). 이 게임의 방은 6~10개뿐이고, 방을 무작위로 던진 뒤
겹치면 버리는 것으로 충분하다.

생성은 전적으로 시드 결정론적이다. 같은 시드 → 같은 던전. 이건 편의 기능이 아니라
버그 재현의 전제다 (docs/10_running.md §5).
"""

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

# 층별 파라미터 v1 — 이 수치는 틀릴 것이다.
# Phase 3에서 동료 플레이테스트로 흔들고 v2를 낸다 (docs/02_game_design.md §2).
FLOOR_PARAMS: dict[int, dict] = {
    1: {"rooms": (6, 8), "monsters": 4, "items": 3},
    2: {"rooms": (6, 9), "monsters": 6, "items": 3},
    3: {"rooms": (7, 9), "monsters": 8, "items": 2},
    4: {"rooms": (7, 10), "monsters": 10, "items": 2},
    5: {"rooms": (5, 6), "monsters": 6, "items": 2},
}

ROOM_MIN = 5
ROOM_MAX = 12
MAX_PLACEMENT_TRIES = 200

# 바닥 아이템 종류 풀 (가중치 = 등장 빈도). 포션이 흔하고 장비는 드물다. docs/02 §5
ITEM_POOL = ["potion", "potion", "potion", "sword", "shield", "scroll"]

# 적 종류 (docs/02 §3). 종류별 도주 정책이 관찰되도록 각 종류를 최소 1마리씩 보장한다.
# 층별 조합·비율·가중치·난이도 곡선은 확정하지 않고 Phase 3(DQ2)에 남긴다 — 여기서
# 가중 풀을 만들지 않는다 (설계 evt_81fb3979).
ENEMY_KINDS = ("rat", "goblin", "golem")


def _overlaps(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> bool:
    """방 사이에 최소 1칸 벽이 남도록 1칸 여유를 두고 판정."""
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
    """L자 복도. 가로 먼저 갈지 세로 먼저 갈지는 시드가 정한다."""
    (x1, y1), (x2, y2) = a, b
    if rng.chance(0.5):
        _carve_h(tiles, x1, x2, y1)  # 가로 먼저
        _carve_v(tiles, y1, y2, x2)
    else:
        _carve_v(tiles, y1, y2, x1)  # 세로 먼저
        _carve_h(tiles, x1, x2, y2)


def generate(floor: int, rng: Rng) -> tuple[Map, list[Actor], list[ItemOnFloor]]:
    """한 층을 생성한다. actors[0]은 플레이어."""
    params = FLOOR_PARAMS[floor]

    tiles = [[WALL for _ in range(MAP_W)] for _ in range(MAP_H)]
    rooms: list[tuple[int, int, int, int]] = []

    target = rng.randint(*params["rooms"])
    tries = 0
    while len(rooms) < target and tries < MAX_PLACEMENT_TRIES:
        tries += 1
        w = rng.randint(ROOM_MIN, ROOM_MAX)
        h = rng.randint(ROOM_MIN, min(ROOM_MAX, MAP_H - 4))
        x = rng.randint(1, MAP_W - w - 2)
        y = rng.randint(1, MAP_H - h - 2)
        room = (x, y, w, h)
        if any(_overlaps(room, other) for other in rooms):
            continue
        _carve_room(tiles, room)
        if rooms:
            _carve_corridor(tiles, _center(rooms[-1]), _center(room), rng)
        rooms.append(room)

    # 플레이어는 첫 방, 계단은 마지막 방.
    px, py = _center(rooms[0])
    sx, sy = _center(rooms[-1])
    tiles[sy][sx] = STAIRS

    actors: list[Actor] = [make_player(px, py)]

    # 적 배치 — 첫 방(플레이어 시작 방)에는 넣지 않는다.
    occupied = {(px, py), (sx, sy)}
    spawn_rooms = rooms[1:] or rooms

    # 각 종류를 최소 1마리씩 보장하고 나머지는 균등 랜덤으로 채운다. 비율은 미확정.
    roster = list(ENEMY_KINDS)[: params["monsters"]]
    while len(roster) < params["monsters"]:
        roster.append(rng.choice(ENEMY_KINDS))

    for i, kind in enumerate(roster):
        for _ in range(50):
            room = rng.choice(spawn_rooms)
            rx, ry, rw, rh = room
            ex = rng.randint(rx, rx + rw - 1)
            ey = rng.randint(ry, ry + rh - 1)
            if (ex, ey) not in occupied:
                occupied.add((ex, ey))
                actors.append(make_enemy(kind, i, ex, ey))
                break

    # 바닥 아이템 — 적과 같은 방식으로 겹치지 않게 놓는다 (첫 방 제외).
    floor_items: list[ItemOnFloor] = []
    for i in range(params.get("items", 0)):
        for _ in range(50):
            room = rng.choice(spawn_rooms)
            rx, ry, rw, rh = room
            ix = rng.randint(rx, rx + rw - 1)
            iy = rng.randint(ry, ry + rh - 1)
            if (ix, iy) not in occupied:
                occupied.add((ix, iy))
                floor_items.append(
                    # ID에 층 번호를 넣는다 — 인벤토리는 층을 넘어 유지되므로 층마다
                    # item#0을 재사용하면 서로 다른 아이템이 같은 id를 갖는다 (evt_5e7f2360 높음3).
                    ItemOnFloor(id=f"f{floor}-item#{i}", kind=rng.choice(ITEM_POOL), x=ix, y=iy)
                )
                break

    game_map = Map(
        tiles=tiles,
        explored=[[False] * MAP_W for _ in range(MAP_H)],
        visible=[[False] * MAP_W for _ in range(MAP_H)],
        rooms=rooms,
    )
    return game_map, actors, floor_items
