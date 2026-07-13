"""게임 상태 데이터 구조.

주의 (docs/04_turn_system_pivot.md):
    Actor에 `speed` / `energy` 필드가 **없다.** v1은 즉시판정(lockstep)이라
    "1입력 = 전원 1행동"이고, 속도 개념 자체가 없다.

    적이 1종(Goblin)뿐인 현 조건에서 에너지 시스템은 과설계다. 적에 속도를 넣는
    순간 이 결정을 재검토해야 한다 — 그때 v1은 구조적으로 깨진다.
"""

from __future__ import annotations

from dataclasses import dataclass, field

MAP_W = 64
MAP_H = 32

WALL = "#"
FLOOR = "."
STAIRS = ">"

MAX_FLOOR = 5


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
        id="player", kind="player", glyph="@", x=x, y=y, hp=20, max_hp=20, atk=5, def_=2
    )


# 적 스펙 — Phase 1은 Goblin 1종뿐이다.
#
# Phase 2에서 Rat(speed 150) / Golem(speed 60)을 추가하는 순간 v1 턴 시스템이
# 깨진다. 그게 사전 설계된 유일한 전환점이다 (docs/04_turn_system_pivot.md).
# 여기에 속도가 다른 적을 미리 넣지 말 것 — 전환이 일어나지 않으면 DQ1이 죽는다.
ENEMY_SPECS: dict[str, dict] = {
    "goblin": {"glyph": "g", "hp": 10, "atk": 4, "def_": 1, "xp": 8},
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
    )
