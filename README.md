# Delve

A turn-based web roguelike whose entire development history is preserved in shared AI memory.

- **Play**: deployment link coming in Phase 5
- **Code**: this repository
- **Read why it was built this way**: public static history coming in Phase 5
- **Ask the graph directly**: AiAkiv users receive a read-only Delve sample project

## What is this?

Git history shows **what** changed. Memory shows **why** it changed: which alternatives were considered and why they were rejected.

While building the game for real, we store every design decision, bug fix, and balance adjustment in AiAkiv. Two people and three AI systems (Claude Code, ChatGPT, and Gemini) contribute to the same memory graph.

**The protagonist is not the game; it is the development trail.** The game does not need to be elaborate. The trail needs to be genuine.

## Two ways to explore the trail

**Read without signing up** — browse a static view of events, decisions, and causal links. Each implementation event links to its Git commit.

**Ask with AiAkiv** — query the graph directly through a live read-only sample project. It follows development as it happens, while visitors cannot modify it.

- “How has the combat system design changed?”
- “How was the enemy AI implemented?” (design, implementation, and review were performed by different AIs)
- “What was the most recent bug, and what caused it?”
- “Why did the inventory and save format change together?”

Keyword search cannot answer the last two questions: the text describing a bug and the earlier decision that caused it may share no words at all.

## The game

Delve is a turn-based roguelike with five procedurally generated floors, permadeath, three enemy types plus a boss, and an inventory. Moving one tile sends one HTTP request; the server advances the turn and returns the new state as JSON.

- **Backend:** FastAPI and a pure-Python game engine. The engine imports no web framework.
- **Frontend:** one framework-free HTML file with a text grid (`@` is the player and `#` is a wall).
- **Zero art assets:** roguelikes were born without graphics.

## Run locally

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000.

The only runtime dependencies are FastAPI and Uvicorn. There is no Node.js, bundler, or database server. Move with the arrow keys or `hjkl`; moving into an enemy attacks it.

The same seed always produces the same dungeon. When reporting a bug, include the seed. See [docs/10_running.md](docs/10_running.md) for the full running guide.

## Design documents

| Document | Contents |
|---|---|
| [docs/00_overview.md](docs/00_overview.md) | Purpose, success criteria, and principles |
| [docs/01_demo_goals.md](docs/01_demo_goals.md) | Target interrogation queries and query-driven design |
| [docs/02_game_design.md](docs/02_game_design.md) | Game specification |
| [docs/03_architecture.md](docs/03_architecture.md) | Architecture |
| [docs/04_turn_system_pivot.md](docs/04_turn_system_pivot.md) | The single preplanned architectural pivot |
| [docs/05_roadmap.md](docs/05_roadmap.md) | Phases 0–5 |
| [docs/06_memory_protocol.md](docs/06_memory_protocol.md) | Memory-writing protocol |
| [docs/07_github_provenance.md](docs/07_github_provenance.md) | Bidirectional commit/event provenance |
| [docs/08_participants_workflow.md](docs/08_participants_workflow.md) | Participants and session workflow |
| [docs/09_risks_checklist.md](docs/09_risks_checklist.md) | Risks and checklists |
| [docs/10_running.md](docs/10_running.md) | Local development and test guide |

## Status

Development concluded after Phase 3 plus the UX pass. The project includes the v2 energy scheduler, three enemy behaviors, inventory and save-format v2, deterministic RNG stream isolation, balance v1→v2 rollback evidence, and mouse-plus-keyboard controls. Phase 4 save/load endpoints and Phase 5 public-history publishing remain intentionally unfinished and are documented as such.

The single source of truth for progress is the checkbox list in [docs/05_roadmap.md](docs/05_roadmap.md), together with AiAkiv memory. There is no separate PLAN or TODO file: duplicating status would weaken the project’s central claim that memory can replace a conventional planning file.
