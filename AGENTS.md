# AGENTS.md — Session Entry Rules

> **This file and [CLAUDE.md](CLAUDE.md) must stay identical.** Each tool reads only
> its own entry file. If one changes without the other, agents may write using stale
> conventions. [docs/06_memory_protocol.md](docs/06_memory_protocol.md) is authoritative.

**Delve** is a turn-based web roguelike, but the development trail—not the game—is
the protagonist. The repository preserves real decisions, alternatives, bugs, and
implementation provenance in AiAkiv.

See [docs/00_overview.md](docs/00_overview.md) for the full context.

## At the start of every session

1. Check the active AK target; it must be `AiAkiv-roguelike`, never the parent `k2g` project.
2. Ask AK what happened in the previous session.
3. Read [docs/05_roadmap.md](docs/05_roadmap.md).

The roadmap checkboxes plus AiAkiv memory are the single source of truth. Do not
create a separate PLAN or TODO file.

## At the end of every session

1. Check the save checklist in [docs/06_memory_protocol.md](docs/06_memory_protocol.md).
2. Confirm each implementation event contains its commit hash and each commit points back.
3. Update roadmap checkboxes.

## Three absolute prohibitions

### 1. Do not skip directly to turn system v2

Phase 1 had to implement, commit, and ship playable v1 lockstep turns. Only after
the three unequal enemy speeds exposed the real limitation could Phase 2 adopt the
energy scheduler. Skipping this would destroy DQ1's genuine decision chain.

### 2. Never plant a bug

Record every naturally occurring bug with symptom, reproduction seed, linked root
cause, fix, and commit. Manufacturing a bug would invalidate the demonstration.

### 3. Never drift canonical AK identifiers

The only intentional Korean text retained in this English repository is the
historical AK identifier column below. Existing graph events already use these
exact names; translating them would silently create disconnected entities.

| Canonical AK identifier | English display name | Code |
|---|---|---|
| `턴 시스템` | Turn system | `engine/turn.py` |
| `던전 생성` | Dungeon generation | `engine/dungeon.py` |
| `적 AI` | Enemy AI | `engine/ai.py` |
| `세이브 포맷` | Save format | `engine/serialize.py` |
| `인벤토리` | Inventory | `engine/items.py` |
| `전역 시드` | Global seed | `engine/rng.py` |
| `전투` | Combat | `engine/combat.py` |
| `시야` | Field of view | `engine/fov.py` |
| `Delve` | Delve project | whole repository |

Use English display names in prose and UI. Use the exact canonical value only when
writing AK entities. See [docs/06_memory_protocol.md](docs/06_memory_protocol.md).

## Memory protocol summary

Save only after an explicit `ak`, `mweft`, or `memoryweft` request, and save when
the event occurs rather than batching later.

A decision records: what, why, alternatives and rejection reasons, and commit hash
(plus a document path when relevant).

A bug records: symptom, linked root cause, fix, and commit hash.

If design precedes implementation, save the design immediately and create a
separate implementation event after committing. Never store real names, secrets,
costs, unrelated conversation, or parent-project information.

## Commit convention

```text
<type>: <summary>

<body explaining why>

ak:evt_<event id>
docs: docs/xx.md

Co-Authored-By: <AI name> <noreply address>
```

See [docs/07_github_provenance.md](docs/07_github_provenance.md).

## Architecture invariants

1. `engine/` imports neither FastAPI nor Pydantic.
2. `app/main.py` contains no game rules.
3. Every random choice flows through `engine/rng.py`; never call the global
   `random` module directly.

## Scope boundary

Do not add status effects, magic, ranged combat, multiplayer, accounts, rankings,
an asset pipeline, more than five floors, or more enemy types. The game only needs
to be real enough to generate an honest development trail.

## Run

```bash
uvicorn app.main:app --reload
pytest
```

Open http://127.0.0.1:8000.
