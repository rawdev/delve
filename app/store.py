
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

IDLE_TTL_SECONDS = 60 * 60

FINISHED_TTL_SECONDS = 5 * 60


@dataclass
class _Session:
    state: GameState
    rng: Rng
    lock: threading.Lock = field(default_factory=threading.Lock)
    touched_at: float = field(default_factory=time.monotonic)


_sessions: dict[str, _Session] = {}
_registry_lock = threading.Lock()


def new_id() -> str:
    return uuid.uuid4().hex[:12]


def put(state: GameState, rng: Rng) -> None:
    with _registry_lock:
        _evict_locked()
        _sessions[state.game_id] = _Session(state=state, rng=rng)


@contextmanager
def session(game_id: str) -> Iterator[tuple[GameState, Rng] | None]:
    with _registry_lock:
        found = _sessions.get(game_id)

    if found is None:
        yield None
        return

    with found.lock:
        found.touched_at = time.monotonic()
        yield (found.state, found.rng)


def _evict_locked() -> None:
    now = time.monotonic()

    for game_id, s in list(_sessions.items()):
        ttl = IDLE_TTL_SECONDS if s.state.status == "playing" else FINISHED_TTL_SECONDS
        if now - s.touched_at > ttl:
            del _sessions[game_id]

    overflow = len(_sessions) - MAX_SESSIONS + 1
    if overflow > 0:
        oldest = sorted(_sessions.items(), key=lambda kv: kv[1].touched_at)[:overflow]
        for game_id, _ in oldest:
            del _sessions[game_id]


def count() -> int:
    with _registry_lock:
        return len(_sessions)


def reset() -> None:
    with _registry_lock:
        _sessions.clear()
