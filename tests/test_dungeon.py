
from __future__ import annotations

from collections import Counter

import pytest

from engine.dungeon import FLOOR_PARAMS, generate
from engine.rng import Rng
from engine.state import FLOOR, MAP_H, MAP_W, STAIRS, WALL

FLOORS = list(FLOOR_PARAMS)


@pytest.mark.parametrize("floor", FLOORS)
def test_same_seed_same_dungeon(floor: int) -> None:
    map_a, actors_a, items_a = generate(floor, Rng(42))
    map_b, actors_b, items_b = generate(floor, Rng(42))

    assert map_a.tiles == map_b.tiles
    assert map_a.rooms == map_b.rooms
    assert [(a.id, a.kind, a.x, a.y) for a in actors_a] == [
        (b.id, b.kind, b.x, b.y) for b in actors_b
    ]
    assert [(i.id, i.kind, i.x, i.y) for i in items_a] == [
        (j.id, j.kind, j.x, j.y) for j in items_b
    ]


def test_different_seed_different_dungeon() -> None:
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
    assert len(stairs) == 1
    assert stairs[0] != (player.x, player.y)


@pytest.mark.parametrize("floor", FLOORS)
def test_enemies_spawn_walkable_and_not_stacked(floor: int) -> None:
    game_map, actors, _ = generate(floor, Rng(7))
    enemies = actors[1:]

    assert len(enemies) == sum(FLOOR_PARAMS[floor]["enemies"].values())

    positions = [(a.x, a.y) for a in actors]
    assert len(positions) == len(set(positions))

    for e in enemies:
        assert game_map.walkable(e.x, e.y)


@pytest.mark.parametrize("floor", FLOORS)
def test_items_spawn_walkable_and_not_on_actors(floor: int) -> None:
    game_map, actors, floor_items = generate(floor, Rng(7))

    assert len(floor_items) == FLOOR_PARAMS[floor]["items"]

    actor_pos = {(a.x, a.y) for a in actors}
    item_pos = {(it.x, it.y) for it in floor_items}
    assert len(item_pos) == len(floor_items)

    for it in floor_items:
        assert game_map.walkable(it.x, it.y)
        assert (it.x, it.y) not in actor_pos


def test_item_ids_are_unique_across_floors() -> None:
    _, _, items1 = generate(1, Rng(7))
    _, _, items2 = generate(2, Rng(7))
    assert {it.id for it in items1}.isdisjoint({it.id for it in items2})





def test_enemy_composition_change_does_not_move_layout_or_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base_map, _, base_items = generate(1, Rng(20260716))

    monkeypatch.setitem(
        FLOOR_PARAMS, 1, {**FLOOR_PARAMS[1], "enemies": {"rat": 5, "goblin": 4}}
    )
    new_map, new_actors, new_items = generate(1, Rng(20260716))

    assert len(new_actors) - 1 == 9
    assert new_map.tiles == base_map.tiles
    assert new_map.rooms == base_map.rooms
    assert [(i.id, i.kind, i.x, i.y) for i in new_items] == [
        (j.id, j.kind, j.x, j.y) for j in base_items
    ]


def test_floor1_enemy_change_does_not_affect_floor2(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rng_a = Rng(20260716)
    generate(1, rng_a)
    map_a, actors_a, items_a = generate(2, rng_a)

    monkeypatch.setitem(FLOOR_PARAMS, 1, {**FLOOR_PARAMS[1], "enemies": {"rat": 7}})

    rng_b = Rng(20260716)
    generate(1, rng_b)
    map_b, actors_b, items_b = generate(2, rng_b)

    assert map_b.tiles == map_a.tiles
    assert [(a.kind, a.x, a.y) for a in actors_b] == [(a.kind, a.x, a.y) for a in actors_a]
    assert [(i.kind, i.x, i.y) for i in items_b] == [(i.kind, i.x, i.y) for i in items_a]


@pytest.mark.parametrize("floor", FLOORS)
def test_enemy_composition_matches_floor_params(floor: int) -> None:
    _, actors, _ = generate(floor, Rng(7))
    counts = Counter(a.kind for a in actors[1:])
    assert dict(counts) == FLOOR_PARAMS[floor]["enemies"]


@pytest.mark.parametrize("floor", FLOORS)
def test_map_is_enclosed(floor: int) -> None:
    game_map, _, _ = generate(floor, Rng(7))
    for x in range(MAP_W):
        assert game_map.tiles[0][x] == WALL
        assert game_map.tiles[MAP_H - 1][x] == WALL
    for y in range(MAP_H):
        assert game_map.tiles[y][0] == WALL
        assert game_map.tiles[y][MAP_W - 1] == WALL


@pytest.mark.parametrize("floor", FLOORS)
def test_all_floor_tiles_reachable(floor: int) -> None:
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

    assert seen == walkable
