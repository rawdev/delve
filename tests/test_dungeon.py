"""던전 생성 테스트 — 핵심은 결정론이다.

같은 시드 → 같은 던전이 깨지면 버그 재현이 불가능해지고, 재현이 안 되면 버그 이벤트를
규약대로(증상 + 근본 원인) 저장할 수 없다. BQ1·BQ2가 여기 걸려 있다.
"""

from __future__ import annotations

from collections import Counter

import pytest

from engine.dungeon import FLOOR_PARAMS, generate
from engine.rng import Rng
from engine.state import FLOOR, MAP_H, MAP_W, STAIRS, WALL

FLOORS = list(FLOOR_PARAMS)


@pytest.mark.parametrize("floor", FLOORS)
def test_same_seed_same_dungeon(floor: int) -> None:
    """같은 시드는 항상 같은 맵과 같은 액터 배치를 만든다."""
    map_a, actors_a, items_a = generate(floor, Rng(42))
    map_b, actors_b, items_b = generate(floor, Rng(42))

    assert map_a.tiles == map_b.tiles
    assert map_a.rooms == map_b.rooms
    assert [(a.id, a.kind, a.x, a.y) for a in actors_a] == [
        (b.id, b.kind, b.x, b.y) for b in actors_b
    ]
    assert [(i.id, i.kind, i.x, i.y) for i in items_a] == [
        (j.id, j.kind, j.x, j.y) for j in items_b
    ]  # 아이템 배치도 시드 결정론적이다


def test_different_seed_different_dungeon() -> None:
    """시드가 다르면 맵도 다르다 (시드가 실제로 쓰이고 있다는 증거)."""
    map_a, _, _ = generate(1, Rng(42))
    map_b, _, _ = generate(1, Rng(43))
    assert map_a.tiles != map_b.tiles


@pytest.mark.parametrize("floor", FLOORS)
def test_player_and_stairs_placed(floor: int) -> None:
    game_map, actors, _ = generate(floor, Rng(7))

    player = actors[0]
    assert player.is_player
    assert game_map.walkable(player.x, player.y)

    stairs = [
        (x, y)
        for y in range(MAP_H)
        for x in range(MAP_W)
        if game_map.tiles[y][x] == STAIRS
    ]
    assert len(stairs) == 1, "계단은 정확히 하나여야 한다"
    assert stairs[0] != (player.x, player.y), "계단 위에서 시작하면 층을 건너뛴다"


@pytest.mark.parametrize("floor", FLOORS)
def test_enemies_spawn_walkable_and_not_stacked(floor: int) -> None:
    game_map, actors, _ = generate(floor, Rng(7))
    enemies = actors[1:]

    assert len(enemies) == sum(FLOOR_PARAMS[floor]["enemies"].values())

    positions = [(a.x, a.y) for a in actors]
    assert len(positions) == len(set(positions)), "액터가 같은 칸에 겹쳐 있다"

    for e in enemies:
        assert game_map.walkable(e.x, e.y), "적이 벽 안에 갇혀 있다"


@pytest.mark.parametrize("floor", FLOORS)
def test_items_spawn_walkable_and_not_on_actors(floor: int) -> None:
    game_map, actors, floor_items = generate(floor, Rng(7))

    assert len(floor_items) == FLOOR_PARAMS[floor]["items"]

    actor_pos = {(a.x, a.y) for a in actors}
    item_pos = {(it.x, it.y) for it in floor_items}
    assert len(item_pos) == len(floor_items), "아이템이 같은 칸에 겹쳐 있다"

    for it in floor_items:
        assert game_map.walkable(it.x, it.y), "아이템이 벽 안에 있다"
        assert (it.x, it.y) not in actor_pos, "아이템이 액터 위에 있다"


def test_item_ids_are_unique_across_floors() -> None:
    """아이템 ID는 층을 넘어 유일하다 — 인벤토리가 층 사이 유지되므로 (evt_5e7f2360 높음3)."""
    _, _, items1 = generate(1, Rng(7))
    _, _, items2 = generate(2, Rng(7))
    assert {it.id for it in items1}.isdisjoint({it.id for it in items2})


@pytest.mark.parametrize("floor", FLOORS)
def test_enemy_composition_matches_floor_params(floor: int) -> None:
    """던전 생성이 밸런스 v1의 층별 적 조합(FLOOR_PARAMS['enemies'])을 그대로 배치한다.

    수치 자체를 테스트에 박지 않는다 — FLOOR_PARAMS를 읽어 대조하므로, 밸런스가 v2로
    바뀌어도 이 계약(생성기가 선언된 조합을 지킨다)은 그대로 통과한다.
    """
    _, actors, _ = generate(floor, Rng(7))
    counts = Counter(a.kind for a in actors[1:])
    assert dict(counts) == FLOOR_PARAMS[floor]["enemies"]


@pytest.mark.parametrize("floor", FLOORS)
def test_map_is_enclosed(floor: int) -> None:
    """맵 가장자리는 벽이어야 한다 (밖으로 걸어나갈 수 없다)."""
    game_map, _, _ = generate(floor, Rng(7))
    for x in range(MAP_W):
        assert game_map.tiles[0][x] == WALL
        assert game_map.tiles[MAP_H - 1][x] == WALL
    for y in range(MAP_H):
        assert game_map.tiles[y][0] == WALL
        assert game_map.tiles[y][MAP_W - 1] == WALL


@pytest.mark.parametrize("floor", FLOORS)
def test_all_floor_tiles_reachable(floor: int) -> None:
    """플레이어 위치에서 모든 바닥·계단 타일에 도달할 수 있다.

    복도 연결이 끊기면 계단에 못 가고 게임이 진행 불가가 된다.
    """
    game_map, actors, _ = generate(floor, Rng(7))
    player = actors[0]

    walkable = {
        (x, y)
        for y in range(MAP_H)
        for x in range(MAP_W)
        if game_map.tiles[y][x] in (FLOOR, STAIRS)
    }

    seen = {(player.x, player.y)}
    stack = [(player.x, player.y)]
    while stack:
        x, y = stack.pop()
        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if (nx, ny) in walkable and (nx, ny) not in seen:
                seen.add((nx, ny))
                stack.append((nx, ny))

    assert seen == walkable, f"도달 불가 타일 {len(walkable - seen)}개"
