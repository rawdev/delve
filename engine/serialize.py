"""세이브 포맷 — GameState + Rng를 JSON으로 직렬화한다. (엔티티: "세이브 포맷")

## 왜 이 포맷인가 (그리고 기각한 대안)

- **JSON + 버전 필드**를 쓴다. `pickle`은 임의 코드 실행 위험 + Python 버전 종속이라
  기각. JSON은 사람이 읽을 수 있고 언어 중립이며, 공개 데모의 정직성과도 맞는다.
- **`rng_state`를 반드시 넣는다.** `seed`만 저장하면 로드 후 생성이 원본과 어긋난다 —
  시드는 시작점일 뿐이고 RNG는 이미 N번 소비된 상태이기 때문이다 (docs/03 §3의 함정).
  이걸 빠뜨리면 세이브/로드가 결정론을 깨고, 그게 BQ2의 후보가 된다. tests/test_serialize.py가
  이 함정을 조기에 잡는다.
- **`version` 필드**를 둔다. 인벤토리가 들어오면 포맷이 바뀐다 — 그때 버전을 올린다.
  이 파일이 v1이고, 인벤토리 추가가 v2다. 두 변경이 엔티티 "세이브 포맷"을 공유하는
  것이 BQ3의 전부다 (docs/04 §4, docs/02 §5).

## 왜 지금(2-b) 만드나

v2 전환으로 Actor에 speed/energy가 생겼다. 그 상태를 기준으로 포맷 v1을 만든다.
세이브/로드 HTTP 엔드포인트와 SQLite는 Phase 4다 — 여기서는 포맷과 라운드트립만
확정한다.
"""

from __future__ import annotations

import json

from engine.rng import Rng
from engine.state import Actor, GameState, Map

FORMAT_VERSION = 1

_ACTOR_FIELDS = (
    "id", "kind", "glyph", "x", "y", "hp", "max_hp", "atk", "def_", "xp", "speed", "energy",
)


def to_dict(state: GameState, rng: Rng) -> dict:
    """세이브 가능한 dict로. seed와 rng_state를 **둘 다** 담는다."""
    return {
        "version": FORMAT_VERSION,
        "game_id": state.game_id,
        "seed": state.seed,
        "rng_state": _rng_to_json(rng.get_state()),
        "turn": state.turn,
        "floor": state.floor,
        "status": state.status,
        "level": state.level,
        "player_xp": state.player_xp,
        "map": {
            "tiles": ["".join(row) for row in state.map.tiles],
            "explored": state.map.explored,
            "visible": state.map.visible,
            "rooms": [list(r) for r in state.map.rooms],
        },
        "actors": [_actor_to_dict(a) for a in state.actors],
        "log": list(state.log),
    }


def from_dict(data: dict) -> tuple[GameState, Rng]:
    version = data.get("version")
    if version != FORMAT_VERSION:
        raise ValueError(f"지원하지 않는 세이브 포맷 버전: {version} (기대: {FORMAT_VERSION})")

    m = data["map"]
    game_map = Map(
        tiles=[list(row) for row in m["tiles"]],
        explored=[list(row) for row in m["explored"]],
        visible=[list(row) for row in m["visible"]],
        rooms=[tuple(r) for r in m["rooms"]],
    )
    state = GameState(
        game_id=data["game_id"],
        seed=data["seed"],
        turn=data["turn"],
        floor=data["floor"],
        map=game_map,
        actors=[_actor_from_dict(a) for a in data["actors"]],
        log=list(data["log"]),
        status=data["status"],
        level=data["level"],
        player_xp=data["player_xp"],
    )

    rng = Rng(data["seed"])
    rng.set_state(_rng_from_json(data["rng_state"]))
    return state, rng


def to_json(state: GameState, rng: Rng) -> str:
    return json.dumps(to_dict(state, rng))


def from_json(text: str) -> tuple[GameState, Rng]:
    return from_dict(json.loads(text))


def _actor_to_dict(a: Actor) -> dict:
    return {f: getattr(a, f) for f in _ACTOR_FIELDS}


def _actor_from_dict(d: dict) -> Actor:
    return Actor(**{f: d[f] for f in _ACTOR_FIELDS})


def _rng_to_json(state: tuple) -> list:
    # random.getstate() -> (version:int, internal:tuple[int, ...], gauss:float|None)
    version, internal, gauss = state
    return [version, list(internal), gauss]


def _rng_from_json(data: list) -> tuple:
    version, internal, gauss = data
    return (version, tuple(internal), gauss)
