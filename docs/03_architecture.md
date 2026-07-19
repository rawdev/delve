# 03. Architecture — FastAPI and a Pure-Python Engine

## 1. Stack decision

Adopted: FastAPI, a pure-Python game engine, and one framework-free HTML client. Turn-based play lets the Python server remain authoritative: one action is one HTTP request and one deterministic state transition.

Rejected alternatives:

| Alternative | Why rejected |
|---|---|
| TypeScript + Canvas on GitHub Pages | Deployment is easy, but all game logic moves to JavaScript and the claimed Python game disappears. Its proposed real-time pivot would be staged rather than genuine. |
| Tower defense | Real-time simulation pushes the core to the browser for the same reason. |
| Full Python server plus full TypeScript client | Doubles the scope without improving the evidence. |
| BSP dungeon generation | Random rooms and L-shaped corridors are sufficient. |

## 2. Layer invariants

1. `engine/` imports neither FastAPI nor Pydantic; it uses Python and the standard library only.
2. `app/main.py` contains no game rules. It parses requests, calls the engine, and serializes responses.
3. Every random choice flows through `engine/rng.py`; direct global `random` calls are forbidden.

These boundaries let engine tests run without HTTP and kept `ai.decide(state, enemy) -> (dx, dy)` unchanged during the scheduler rewrite.

## 3. State model

`GameState` owns the current map, actors, inventory, floor items, progress, log, and status. `Actor` carries integer `speed` and `energy`. `Rng` is separate but saved with state. The save representation includes both the seed and consumed RNG state.

## 4. HTTP contract

| Method | Path | Request | Response |
|---|---|---|---|
| POST | `/api/game` | `{seed?: int}` | `GameView` |
| GET | `/api/game/{id}` | — | `GameView` |
| POST | `/api/game/{id}/action` | `{type, dir?, item_id?}` | `{view, events[]}` |
| POST | `/api/game/{id}/save` | — | Phase 4, unfinished |
| POST | `/api/game/{id}/load` | `{save_id}` | Phase 4, unfinished |

`events[]` became necessary in v2 because one player input can contain multiple ordered enemy actions. The view and events are filtered by FOV so movement in darkness is not leaked.

## 5. Session store

Phases 1–3 use an in-process dictionary. Each game has a lock because synchronous FastAPI handlers run in a thread pool and concurrent mutation would lose turns or split RNG consumption. Sessions expire and the registry is capped. Server restart still loses active games; SQLite persistence was intentionally deferred to unfinished Phase 4.

## 6. Determinism

- The seed is always returned so bug reports can reproduce a run.
- Dungeon layout, items, and enemies use stable child streams derived from `(root seed, namespace, floor)`.
- Derivation does not consume the parent stream, preventing one balance change from moving items or later floors.
- Combat and scheduling use no randomness or floating point.
- Saves contain both `seed` and `rng_state`.

## 7. Deployment

Railway runs one Uvicorn process. The intended public surface links four destinations: play, GitHub, a static unauthenticated memory view, and the live read-only AiAkiv sample project. The last two publishing surfaces remained Phase 5 work.

## 8. Tests

Engine tests use pure Python. Key contracts cover same-seed dungeon identity, speed ratios of 150/100/60, deterministic event order, save round-trips including RNG state, API FOV filtering, and per-game concurrency serialization.
