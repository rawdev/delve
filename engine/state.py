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


# 적 스펙 (docs/02_game_design.md §3).
#
# Phase 2-a 진행 중 — 크리틱 Phase 2 사전 리뷰 권장 순서 1: Rat/Goblin/Golem의
# `speed`를 **스펙 데이터로만** 추가한다. 이 speed는 아직 (1) Actor 필드가 아니고
# (2) 던전 스폰에도 쓰이지 않는다. 지금은 "v1이 만족할 수 없는 요구"를 수치로
# 적어둔 것뿐이고, tests/test_turn.py가 그 요구를 v1에 걸어 xfail로 파열을 증명한다.
#
# ⚠️ make_enemy는 speed를 Actor에 복사하지 않는다. Actor에 speed/energy가 올라가는
# 순간 전환이 '아키텍처 교체'가 아니라 '필드 활성화'로 전락해 DQ1 결정 사슬이
# 죽는다 (R4). speed/energy가 Actor로 올라가고 던전이 3종을 스폰하는 것은 에너지
# 스케줄러 전환(v2) 커밋에서 함께 일어난다 → docs/04_turn_system_pivot.md
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
    )
