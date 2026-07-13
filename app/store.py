"""세션 저장소.

Phase 1~3: 프로세스 메모리 dict. **서버가 재시작되면 진행 중인 게임이 전부 날아간다.**
이건 알려진 한계이고, Phase 4의 세이브 구현(SQLite)이 해결한다.

여기서 파생되는 버그가 나오면 근본 원인은 "Phase 1의 인메모리 상태 결정"으로 링크된다.
(예상이지 계획이 아니다 — 버그를 심지 않는다.)
"""

from __future__ import annotations

import uuid

from engine.rng import Rng
from engine.state import GameState

_games: dict[str, tuple[GameState, Rng]] = {}


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def put(state: GameState, rng: Rng) -> None:
    _games[state.game_id] = (state, rng)


def get(game_id: str) -> tuple[GameState, Rng] | None:
    return _games.get(game_id)
