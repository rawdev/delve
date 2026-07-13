"""던전 생성 테스트 — 핵심은 결정론이다.

같은 시드 → 같은 던전이 깨지면 버그 재현이 불가능해지고, 재현이 안 되면 버그 이벤트를
규약대로(증상 + 근본 원인) 저장할 수 없다. BQ1·BQ2가 여기 걸려 있다.
"""

from __future__ import annotations

import pytest

from engine.dungeon import FLOOR_PARAMS, generate
from engine.rng import Rng
from engine.state import FLOOR, MAP_H, MAP_W, STAIRS, WALL

FLOORS = list(FLOOR_PARAMS)


@pytest.mark.parametrize("floor", FLOORS)
def test_same_seed_same_dungeon(floor: int) -> None:
    """같은 시드는 항상 같은 맵과 같은 액터 배치를 만든다."""
    map_a, actors_a = generate(floor, Rng(42))
    map_b, actors_b = generate(floor, Rng(42))

    assert map_a.tiles == map_b.tiles
    assert map_a.rooms == map_b.rooms
    assert [(a.id, a.kind, a.x, a.y) for a in actors_a] == [
        (b.id, b.kind, b.x, b.y) for b in actors_b
    ]


def test_different_seed_different_dungeon() -> None:
    """시드가 다르면 맵도 다르다 (시드가 실제로 쓰이고 있다는 증거)."""
    map_a, _ = generate(1, Rng(42))
    map_b, _ = generate(1, Rng(43))
    assert map_a.tiles != map_b.tiles


@pytest.mark.parametrize("floor", FLOORS)
def test_player_and_stairs_placed(floor: int) -> None:
    game_map, actors = generate(floor, Rng(7))

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
    game_map, actors = generate(floor, Rng(7))
    enemies = actors[1:]

    assert len(enemies) == FLOOR_PARAMS[floor]["monsters"]

    positions = [(a.x, a.y) for a in actors]
    assert len(positions) == len(set(positions)), "액터가 같은 칸에 겹쳐 있다"

    for e in enemies:
        assert game_map.walkable(e.x, e.y), "적이 벽 안에 갇혀 있다"


@pytest.mark.parametrize("floor", FLOORS)
def test_only_goblins_in_phase1(floor: int) -> None:
    """Phase 1은 Goblin 1종뿐이다.

    속도가 다른 적(Rat/Golem)이 들어오는 순간 v1 즉시판정 턴 시스템이 깨진다.
    그건 Phase 2의 사전 설계된 전환점이다 (docs/04_turn_system_pivot.md).
    이 테스트는 그 전환을 Phase 1에서 실수로 앞당기지 않도록 막는 가드다.
    """
    _, actors = generate(floor, Rng(7))
    assert {a.kind for a in actors[1:]} <= {"goblin"}


@pytest.mark.parametrize("floor", FLOORS)
def test_map_is_enclosed(floor: int) -> None:
    """맵 가장자리는 벽이어야 한다 (밖으로 걸어나갈 수 없다)."""
    game_map, _ = generate(floor, Rng(7))
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
    game_map, actors = generate(floor, Rng(7))
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
