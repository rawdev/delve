# 05. Roadmap — Phases 0–5

This checklist plus AiAkiv memory is the single source of truth. Do not create a separate PLAN or TODO file.

## Phase 0 — Setup — complete

- [x] Write `docs/00` through `docs/10` and the session-entry rules.
- [x] Create the public repository: https://github.com/rawdev/delve.
- [x] Add ignore rules and secret-free MCP configuration.
- [x] Reserve links for play, code, static memory, and the sample project.
- [x] Verify the isolated AiAkiv target.
- [x] Confirm that unauthenticated public-read MCP does not exist; adopt static export plus a live read-only sample project.
- [x] Verify cross-account writes and `@handle` retrieval through `@critic`.
- [x] Record stack, pivot, protocol, and first-commit provenance events.

## Phase 1 — Core loop — complete

Implementation order: RNG → state → dungeon → FOV → combat → one Goblin AI → v1 lockstep turns → FastAPI boundary → text frontend → deterministic tests.

- [x] Establish seeded RNG and forbid global random calls.
- [x] Build deterministic rooms, corridors, stairs, actors, and FOV.
- [x] Implement deterministic combat and `ai.decide()`.
- [x] Implement and commit v1 lockstep turns without speed or energy.
- [x] Keep all game rules out of `app/main.py`.
- [x] Make the five-floor game playable in a browser.
- [x] Add per-game request locks, session expiry/capacity, and API contract tests.
- [x] Preserve the intentional absence of `events[]` in v1 as migration evidence.

Key evidence: `evt_44979725`, `evt_f9b9fda8`, `evt_3efb024c`, `evt_6d1ab84d`, `evt_fbe97e9d`, and `evt_edebe34a`.

## Phase 2 — System expansion — complete

### 2-a. Turn-system pivot

- [x] Add Rat 150 / Goblin 100 / Golem 60 and observe the v1 fracture.
- [x] Prototype counter-based scheduling and reject its player asymmetry.
- [x] Compare counter, float queue, and integer energy alternatives.
- [x] Adopt the integer energy scheduler and ordered `events[]` response.
- [x] Replace v1 guard tests with speed-ratio and event-order tests.
- [x] Record the v2 decision as `evt_67f3a39c`.

### 2-b. Inventory and save format

- [x] Implement Potion, Sword, Shield, Recall Scroll, pickup/use/equip, and ten bag slots.
- [x] Establish JSON save format v1 with version and RNG state.
- [x] Migrate to v2 for inventory, equipment, and floor items.
- [x] Add API/frontend support and round-trip tests.
- [x] Record `evt_5c089dca` and `evt_d3557b15` using canonical AK identifiers.

### 2-c. Cross-author enemy AI

- [x] `@critic` designs the Rat/Goblin/Golem policy table (`evt_81fb3979`).
- [x] `@developer` implements policies, dungeon placement, and tests.
- [x] Review and fix runtime defects without changing the `ai.decide()` interface.

## Phase 3 — Balance cycle — complete

1. [x] Define floor composition v1 (`evt_4f6c50df`).
2. [x] Run `@critic` playtest at seed `20260716`; observe lethal early Golem encounters (`evt_b48388fc`).
3. [x] Choose the smallest rollback: remove only the floor-one Golem (`evt_a33581a1`).
4. [x] Implement balance v2 in `83168b4` (`evt_5c7e7238`).
5. [x] Reject the first same-seed comparison because shared RNG consumption changed items and later floors (`evt_5d80dac6`).
6. [x] Design and implement independent layout/item/enemy child streams (`evt_5c9d0278`, `ede59e9`).
7. [x] Run a controlled 20-seed A/B comparison (`evt_6f9a4028`).
8. [x] Add mouse controls and action buttons after the “too uncomfortable” review; final user review became positive.

## Phase 4 — Save/load and bug-recall demonstration — unfinished

- [ ] Replace the in-memory store with SQLite.
- [ ] Add `/save` and `/load` endpoints.
- [ ] Delete saves on permadeath.
- [ ] Demonstrate memory-assisted diagnosis using only naturally occurring bugs.
- [ ] Perform one focused refactor.

## Phase 5 — Publication — unfinished

- [ ] Save a final retrospective.
- [ ] Run community/auto-tag analysis on real data.
- [ ] Export the graph to static HTML and publish it.
- [ ] Verify commit links from exported events.
- [ ] Verify member onboarding and enforced read-only access to the sample project.
- [ ] Run every target query against the graph and save the answers.
- [ ] Cross-link play, GitHub, static memory, and the live sample project.

Development intentionally concluded after Phase 3 plus the UX pass. Phases 4 and 5 remain honest, visible unfinished work.
