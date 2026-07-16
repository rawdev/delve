"""게임 상태 데이터 구조.

턴 시스템 v2 (에너지 스케줄러) 기준 (docs/04_turn_system_pivot.md):
    Actor는 `speed`(에너지 회복량)와 `energy`(행동 게이지)를 갖는다. 매 내부 tick에
    살아 있는 액터가 speed만큼 energy를 얻고, energy가 ENERGY_THRESHOLD 이상이면
    행동한다. 플레이어도 그냥 액터 하나다 — 이 대칭이 v2의 핵심이며, v1(즉시판정)이
    표현하지 못하던 속도차를 정수 결정론으로 표현한다.

    v1 → v2 전환의 근거와 대안 A/B/C 비교는 docs/04_turn_system_pivot.md에 있다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MAP_W = 64
MAP_H = 32

WALL = "#"
FLOOR = "."
STAIRS = ">"

MAX_FLOOR = 5

# 에너지 스케줄러 (v2, docs/04). energy가 이 값 이상이면 액터가 1회 행동하고 이만큼 차감.
ENERGY_THRESHOLD = 100


@dataclass
class Actor:
    """플레이어와 적이 공유하는 구조. actors[0]은 항상 플레이어다."""

    id: str
    kind: str  # "player" | "goblin"
    glyph: str
    x: int
    y: int
    hp: int
    max_hp: int
    atk: int
    def_: int
    xp: int = 0  # 처치 시 주는 경험치 (플레이어는 0)
    speed: int = 0  # 에너지 회복량 (v2). 플레이어 100 / Rat 150 / Goblin 100 / Golem 60
    energy: int = 0  # 행동 게이지 (v2). ENERGY_THRESHOLD 이상이면 1회 행동

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
class GameState:
    game_id: str
    seed: int
    turn: int
    floor: int
    map: Map
    actors: list[Actor]
    log: list[str] = field(default_factory=list)
    status: str = "playing"  # "playing" | "dead" | "won"

    # 플레이어 진행 (레벨업)
    level: int = 1
    player_xp: int = 0

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
        speed=100, energy=ENERGY_THRESHOLD,  # 새 게임에서 플레이어는 바로 행동 가능 (발견 1)
    )


# 적 스펙 (docs/02_game_design.md §3).
#
# v2 에너지 스케줄러 기준: `speed`가 make_enemy를 통해 Actor.speed로 올라간다.
# Rat 150 / Goblin 100 / Golem 60 — 플레이어(100)보다 빠르거나 느린 적이 존재하고,
# 그 비율대로 행동 빈도가 갈리는 것이 turn 시스템 v2의 존재 이유다.
# (v1 즉시판정은 이 비율을 표현할 수 없었다 → docs/04_turn_system_pivot.md)
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
        speed=spec["speed"],  # energy는 0에서 시작 — 내부 tick으로 채워진다
    )
