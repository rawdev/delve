# 00. Overview — What This Project Is and What Success Means

## One-sentence summary

Delve is a small but real turn-based roguelike built to demonstrate a complete, queryable development trail in AiAkiv. The game is the specimen; the history of decisions is the product.

## Success criteria

| Criterion | Target |
|---|---|
| Playable game | A five-floor run can be completed from a deployed URL |
| Public memory events | 80–120 |
| Decision events | At least 15 containing all four required elements |
| Target queries | Every DQ/IQ/BQ/PQ query in [01_demo_goals.md](01_demo_goals.md) produces a convincing graph answer |
| Participants | Two people and two or three AI systems |
| Commit provenance | Every decision and bug event links to a commit |
| Curation cost | Zero; everything is written for publication from the beginning |

## Four governing principles

1. **Design backward from queries.** Decide what visitors should be able to ask, then create genuine development evidence that can answer it.
2. **Small but real.** Keep the game minimal, but do real development. A staged history would invalidate the demonstration.
3. **Never plant bugs.** Record every bug that naturally appears, including its root cause. Do not manufacture one for a query.
4. **Assume publication at write time.** Never store real names, secrets, prices, unrelated conversation, or private information about the parent product.

## Decisions fixed by this document set

- Stack: FastAPI, a pure-Python engine, and a single framework-free HTML frontend.
- The sole preplanned architectural pivot: lockstep turn resolution to an integer energy scheduler.
- The original real-time-to-turn-based pivot was rejected because a server-authoritative turn-based game has no genuine real-time phase; staging one would be theater.

## Document map

| Document | Purpose |
|---|---|
| `AGENTS.md` / `CLAUDE.md` | Session-entry rules, invariants, and prohibitions |
| [01_demo_goals.md](01_demo_goals.md) | Target queries and query-driven design |
| [02_game_design.md](02_game_design.md) | Game specification |
| [03_architecture.md](03_architecture.md) | Layers, state, API, and determinism |
| [04_turn_system_pivot.md](04_turn_system_pivot.md) | The preplanned turn-system pivot |
| [05_roadmap.md](05_roadmap.md) | Phases and status |
| [06_memory_protocol.md](06_memory_protocol.md) | Memory-writing protocol and canonical identifiers |
| [07_github_provenance.md](07_github_provenance.md) | Bidirectional event/commit links |
| [08_participants_workflow.md](08_participants_workflow.md) | Human and AI collaboration workflow |
| [09_risks_checklist.md](09_risks_checklist.md) | Risks and release gates |
| [10_running.md](10_running.md) | Installation, controls, seeds, and testing |

## AiAkiv target

- Team `AiAkiv-Roguelike`; project `AiAkiv-roguelike`; domain `default`; group `root`.
- It is isolated from the parent `k2g` project so public Delve data cannot mix with product data.

## Provenance for the initial document set

| Event | Decision | Commit |
|---|---|---|
| `evt_cb9a017f8342488badd283b5c3db6f24` | Initial project purpose | — |
| `evt_7f0846bfc503419599493d07176a94d0` | FastAPI + pure-Python stack; TypeScript/Canvas rejected | `229aaac` |
| `evt_87b564e85ee14c4695bcec3435671e81` | Replace the staged real-time pivot with the genuine scheduler pivot | `229aaac` |
| `evt_d61ded1d63a44403857b5881457f70ff` | Memory protocol and document set | `229aaac` |
| `evt_1f08127e492f4077a9914836b843f164` | Phase 0 implementation linking the three decisions | `229aaac` |
