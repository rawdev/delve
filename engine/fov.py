"""시야 — 그림자 캐스팅(recursive shadowcasting).

visible = 지금 보이는 곳, explored = 가본 적 있는 곳. 둘을 분리해야 "가봤지만 지금은
안 보이는 곳"(기억)을 어둡게 그릴 수 있다.

무작위성이 없다 — 순수 기하 계산이다. Rng를 받지 않는다.
"""

from __future__ import annotations

from engine.state import WALL, Map

RADIUS = 8

# 8분면 변환 (xx, xy, yx, yy)
_OCTANTS = [
    (1, 0, 0, 1),
    (0, 1, 1, 0),
    (0, -1, 1, 0),
    (-1, 0, 0, 1),
    (-1, 0, 0, -1),
    (0, -1, -1, 0),
    (0, 1, -1, 0),
    (1, 0, 0, -1),
]


def _cast(
    game_map: Map,
    cx: int,
    cy: int,
    row: int,
    start: float,
    end: float,
    xx: int,
    xy: int,
    yx: int,
    yy: int,
) -> None:
    if start < end:
        return

    for j in range(row, RADIUS + 1):
        dx, dy = -j - 1, -j
        blocked = False
        new_start = start

        while dx <= 0:
            dx += 1
            mx = cx + dx * xx + dy * xy
            my = cy + dx * yx + dy * yy

            l_slope = (dx - 0.5) / (dy + 0.5)
            r_slope = (dx + 0.5) / (dy - 0.5)

            if start < r_slope:
                continue
            if end > l_slope:
                break

            if dx * dx + dy * dy <= RADIUS * RADIUS and game_map.in_bounds(mx, my):
                game_map.visible[my][mx] = True
                game_map.explored[my][mx] = True

            wall = not game_map.in_bounds(mx, my) or game_map.tiles[my][mx] == WALL

            if blocked:
                if wall:
                    new_start = r_slope
                    continue
                blocked = False
                start = new_start
            elif wall:
                blocked = True
                _cast(game_map, cx, cy, j + 1, start, l_slope, xx, xy, yx, yy)
                new_start = r_slope

        if blocked:
            break


def compute(game_map: Map, cx: int, cy: int) -> None:
    """(cx, cy)에서의 시야를 계산해 game_map.visible / explored를 갱신한다."""
    for row in game_map.visible:
        for x in range(len(row)):
            row[x] = False

    game_map.visible[cy][cx] = True
    game_map.explored[cy][cx] = True

    for xx, xy, yx, yy in _OCTANTS:
        _cast(game_map, cx, cy, 1, 1.0, 0.0, xx, xy, yx, yy)
