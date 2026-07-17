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
# 밸런스 v2 (Phase 3 / DQ2). 층별 적 조합. v1은 초반 Rat 압박 / 후반 Golem 편중이었으나,
# 동료 플레이테스트(시드 20260716)에서 준비 수단 없는 1층 Golem 조기 조우가 치명적임이
# 드러나(1층·3층 사망), v2에서 1층 Golem 1마리를 제거했다 (롤백 결정 evt_a33581a1).
# Golem 스탯과 2~5층 조합은 유지 — 한 변수만 되돌려 동일 시드로 인과를 비교한다.
FLOOR_PARAMS: dict[int, dict] = {
    1: {"rooms": (6, 8),  "enemies": {"rat": 2, "goblin": 1}, "items": 3},  # v2: Golem 제거
    2: {"rooms": (6, 9),  "enemies": {"rat": 2, "goblin": 3, "golem": 1}, "items": 3},
    3: {"rooms": (7, 9),  "enemies": {"rat": 2, "goblin": 4, "golem": 2}, "items": 2},
    4: {"rooms": (7, 10), "enemies": {"rat": 2, "goblin": 4, "golem": 4}, "items": 2},
    5: {"rooms": (5, 6),  "enemies": {"rat": 1, "goblin": 2, "golem": 3}, "items": 2},
}

ROOM_MIN = 5
ROOM_MAX = 12
MAX_PLACEMENT_TRIES = 200

# 바닥 아이템 종류 풀 (가중치 = 등장 빈도). 포션이 흔하고 장비는 드물다. docs/02 §5
ITEM_POOL = ["potion", "potion", "potion", "sword", "shield", "scroll"]

# 적 종류 (docs/02 §3). roster를 펼치는 고정 순서로 쓴다 — 층별 조합은 FLOOR_PARAMS의
# "enemies"가 정하고, 여기서는 결정론적 배치 순서만 담당한다.
ENEMY_KINDS = ("rat", "goblin", "golem")

# RNG 스트림 namespace (설계 evt_5c9d0278). 층마다 root seed에서 독립 파생해, 한 스트림의
# 소비량 변화가 다른 스트림이나 이후 층을 흔들지 않게 한다. 버전을 넣어 규칙이 바뀌어도
# 과거 스트림과 충돌하지 않게 한다.
LAYOUT_NS = "dungeon/layout/v1"
ITEMS_NS = "dungeon/items/v1"
ENEMIES_NS = "dungeon/enemies/v1"


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
    """한 층을 생성한다. actors[0]은 플레이어.

    ## RNG 분리 (설계 evt_5c9d0278)

    층마다 root seed에서 layout / items / enemies **독립 스트림**을 파생한다. 파생은 부모를
    소비하지 않으므로, 한 스트림의 소비량이 달라져도 나머지와 **이후 층**이 그대로다.

    생성 순서는 **구조 → 아이템 예약 → 적 배치**다. 아이템을 먼저 확정하고 적이 그 칸을
    피하게 해야, 적 수 변화가 아이템의 충돌 판정까지 흔들지 않는다. (반대 순서면 적 조합에
    따라 아이템 재시도 결과가 달라진다.)

    덕분에 **적 조합만 바꾼 동일 시드 비교가 실제 통제 실험**이 된다 — 밸런스 v2 재시험
    evt_5d80dac6에서 적 1마리 제거가 아이템·후속 층까지 흔들어 비교가 무의미해졌던 문제의
    수정이다.
    """
    params = FLOOR_PARAMS[floor]

    layout_rng = rng.derive(LAYOUT_NS, floor)
    items_rng = rng.derive(ITEMS_NS, floor)
    enemies_rng = rng.derive(ENEMIES_NS, floor)

    # 1) 구조 — 방·복도·계단 (layout 스트림)
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

    # 플레이어는 첫 방, 계단은 마지막 방.
    px, py = _center(rooms[0])
    sx, sy = _center(rooms[-1])
    tiles[sy][sx] = STAIRS

    spawn_rooms = rooms[1:] or rooms  # 첫 방(시작 방)에는 아무것도 놓지 않는다
    reserved = {(px, py), (sx, sy)}

    # 2) 아이템 예약 — 적보다 **먼저** 확정한다 (items 스트림).
    floor_items: list[ItemOnFloor] = []
    for i in range(params.get("items", 0)):
        for _ in range(50):
            rx, ry, rw, rh = items_rng.choice(spawn_rooms)
            ix = items_rng.randint(rx, rx + rw - 1)
            iy = items_rng.randint(ry, ry + rh - 1)
            if (ix, iy) not in reserved:
                reserved.add((ix, iy))
                floor_items.append(
                    # ID에 층 번호를 넣는다 — 인벤토리는 층을 넘어 유지되므로 층마다
                    # item#0을 재사용하면 서로 다른 아이템이 같은 id를 갖는다 (evt_5e7f2360 높음3).
                    ItemOnFloor(
                        id=f"f{floor}-item#{i}",
                        kind=items_rng.choice(ITEM_POOL),
                        x=ix,
                        y=iy,
                    )
                )
                break

    # 3) 적 배치 — 예약된 칸(플레이어·계단·아이템)을 피한다 (enemies 스트림).
    actors: list[Actor] = [make_player(px, py)]
    occupied = set(reserved)

    # 층별 조합(밸런스)을 ENEMY_KINDS 순서로 펼친다. 조합은 결정, 위치만 rng.
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
