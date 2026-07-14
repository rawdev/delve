"""세션 저장소 — 인메모리. 게임별 Lock으로 직렬화하고, 수명·용량을 제한한다.

Phase 1~3: 프로세스 메모리 dict. **서버가 재시작되면 진행 중인 게임이 전부 날아간다.**
이건 알려진 한계이고, Phase 4의 세이브 구현(SQLite)이 해결한다.

여기서 파생되는 버그가 나오면 근본 원인은 "Phase 1의 인메모리 상태 결정"으로 링크된다.
(예상이지 계획이 아니다 — 버그를 심지 않는다.)

## 왜 Lock이 필요한가

`app/main.py`의 엔드포인트는 `async def`가 아니라 `def`다. FastAPI는 이런 핸들러를
**스레드풀에서** 돌린다 — 즉 같은 `game_id`에 대한 두 요청이 **실제로 병렬 실행된다.**

`turn.process_turn()`은 `GameState`와 `Rng`를 제자리에서 변경한다. 잠금 없이 병렬로
들어오면:

- `state.turn += 1`이 겹쳐 턴이 유실된다 (read-modify-write는 원자적이지 않다).
- **`Rng`가 두 요청에 나뉘어 소비된다** → 같은 시드로 재생해도 같은 상태가 안 나온다.
  **이게 치명적이다.** 결정론이 깨지면 버그 재현이 안 되고, 재현이 안 되면 버그
  이벤트를 규약대로 저장할 수 없다 (docs/03_architecture.md §6, BQ1·BQ2).

그래서 **게임별 Lock**으로 한 게임의 요청을 직렬화한다. 게임 사이에는 잠금이 없으므로
서로 다른 게임은 여전히 병렬로 처리된다.

`InvalidAction`은 상태를 변경하기 **전에** 올라오므로(engine/actions.py) Lock 안에서
예외가 나도 롤백이 필요 없다. 상태는 손대지 않은 그대로다.

## 왜 수명·용량 제한이 필요한가

`POST /api/game`으로 만든 상태가 제거되지 않으면 공개 배포 시 메모리가 무한히 는다.
로그인이 없어 누구나 게임을 만들 수 있으므로 이건 이론적 위험이 아니다.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from engine.rng import Rng
from engine.state import GameState

MAX_SESSIONS = 500
"""이 수를 넘으면 가장 오래 안 쓴 세션부터 버린다."""

IDLE_TTL_SECONDS = 60 * 60
"""진행 중인 게임을 이만큼 안 건드리면 버린다 (1시간)."""

FINISHED_TTL_SECONDS = 5 * 60
"""끝난 게임(dead/won)은 더 빨리 버린다. 다시 볼 이유가 거의 없다."""


@dataclass
class _Session:
    state: GameState
    rng: Rng
    lock: threading.Lock = field(default_factory=threading.Lock)
    touched_at: float = field(default_factory=time.monotonic)


_sessions: dict[str, _Session] = {}
_registry_lock = threading.Lock()
"""`_sessions` dict 자체를 보호한다. 게임 내용이 아니라 목록만 지킨다 — 이 락을 쥔 채로
게임 처리를 하면 모든 게임이 한 줄로 서게 되므로, 짧게 잡고 바로 놓는다."""


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def put(state: GameState, rng: Rng) -> None:
    with _registry_lock:
        _evict_locked()
        _sessions[state.game_id] = _Session(state=state, rng=rng)


@contextmanager
def session(game_id: str) -> Iterator[tuple[GameState, Rng] | None]:
    """게임을 Lock으로 잡고 `(state, rng)`를 넘긴다. 없으면 `None`.

        with store.session(gid) as found:
            if found is None: ...404...
            state, rng = found

    Lock을 쥔 채로 yield하므로, 블록 안에서는 이 게임에 다른 요청이 끼어들 수 없다.
    **읽기(GET)도 이 경로를 쓴다** — 잠금 없이 읽으면 다른 요청이 절반쯤 바꿔놓은
    상태를 볼 수 있기 때문이다 (액터는 움직였는데 FOV는 아직 옛것인 화면).
    """
    with _registry_lock:
        found = _sessions.get(game_id)

    if found is None:
        yield None
        return

    with found.lock:
        found.touched_at = time.monotonic()
        yield (found.state, found.rng)


def _evict_locked() -> None:
    """`_registry_lock`을 쥔 상태에서만 부른다.

    쫓아낸 세션을 다른 스레드가 이미 잡고 있어도 안전하다 — 그쪽은 `_Session` 객체를
    직접 참조하므로 하던 일을 끝낸다. 다만 그 뒤로는 조회되지 않는다. 의도한 동작이다.
    """
    now = time.monotonic()

    for game_id, s in list(_sessions.items()):
        ttl = IDLE_TTL_SECONDS if s.state.status == "playing" else FINISHED_TTL_SECONDS
        if now - s.touched_at > ttl:
            del _sessions[game_id]

    overflow = len(_sessions) - MAX_SESSIONS + 1  # 새로 넣을 자리 1칸 포함
    if overflow > 0:
        oldest = sorted(_sessions.items(), key=lambda kv: kv[1].touched_at)[:overflow]
        for game_id, _ in oldest:
            del _sessions[game_id]


def count() -> int:
    """살아 있는 세션 수. 테스트와 운영 확인용."""
    with _registry_lock:
        return len(_sessions)


def reset() -> None:
    """테스트 격리용. 프로덕션 경로에서는 부르지 않는다."""
    with _registry_lock:
        _sessions.clear()
