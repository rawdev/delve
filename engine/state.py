
from __future__ import annotations

from dataclasses import dataclass, field

MAP_W = 64
MAP_H = 32

WALL = "#"
FLOOR = "."
STAIRS = ">"

MAX_FLOOR = 5


ENERGY_THRESHOLD = 100


@dataclass
class Actor:

    id: str
    kind: str  # "player" | "goblin"
    glyph: str
    x: int
    y: int
    hp: int
    max_hp: int
    atk: int
    def_: int
    xp: int = 0
    speed: int = 0
    energy: int = 0

    @property
    def is_player(self) -> bool:
        return self.kind == "player"

    @property
    def alive(self) -> bool:
        return self.hp > 0


@dataclass
class Map:
    tiles: list[list[str]]
    explored: list[list[bool]]
    visible: list[list[bool]]
    rooms: list[tuple[int, int, int, int]] = field(default_factory=list)  # (x, y, w, h)

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < MAP_W and 0 <= y < MAP_H

    def walkable(self, x: int, y: int) -> bool:
        return self.in_bounds(x, y) and self.tiles[y][x] != WALL


@dataclass
class Item:

    id: str
    kind: str  # potion | sword | shield | scroll


@dataclass
class ItemOnFloor:

    id: str
    kind: str
    x: int
    y: int


@dataclass
class GameState:
    game_id: str
    seed: int
    turn: int
    floor: int
    map: Map
    actors: list[Actor]
    log: list[str] = field(default_factory=list)
    status: str = "playing"  # "playing" | "dead" | "won"


    level: int = 1
    player_xp: int = 0


    inventory: list[Item] = field(default_factory=list)
    equipped: dict = field(default_factory=lambda: {"weapon": None, "armor": None})
    floor_items: list[ItemOnFloor] = field(default_factory=list)

    @property
    def player(self) -> Actor:
        return self.actors[0]

    @property
    def enemies(self) -> list[Actor]:
        return [a for a in self.actors[1:] if a.alive]

    def actor_at(self, x: int, y: int) -> Actor | None:
        for a in self.actors:
            if a.alive and a.x == x and a.y == y:
                return a
        return None


def make_player(x: int, y: int) -> Actor:
    return Actor(
        id="player", kind="player", glyph="@", x=x, y=y, hp=20, max_hp=20, atk=5, def_=2,
        speed=100, energy=ENERGY_THRESHOLD,
    )



#




ENEMY_SPECS: dict[str, dict] = {
    "rat":    {"glyph": "r", "hp": 4,  "atk": 2, "def_": 0, "xp": 3,  "speed": 150},
    "goblin": {"glyph": "g", "hp": 10, "atk": 4, "def_": 1, "xp": 8,  "speed": 100},
    "golem":  {"glyph": "G", "hp": 26, "atk": 8, "def_": 4, "xp": 20, "speed": 60},
}


def make_enemy(kind: str, idx: int, x: int, y: int) -> Actor:
    spec = ENEMY_SPECS[kind]
    return Actor(
        id=f"{kind}#{idx}",
        kind=kind,
        glyph=spec["glyph"],
        x=x,
        y=y,
        hp=spec["hp"],
        max_hp=spec["hp"],
        atk=spec["atk"],
        def_=spec["def_"],
        xp=spec["xp"],
        speed=spec["speed"],
    )
