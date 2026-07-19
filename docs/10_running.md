# 10. Running Delve — Development and Play

## 1. Requirements

- Python 3.12 or newer
- Any modern browser
- No Node.js, bundler, or database server

Runtime dependencies are only FastAPI and Uvicorn. Test-only dependencies live in `requirements-dev.txt`.

## 2. Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

On macOS/Linux, activate with `source .venv/bin/activate`.

## 3. Run

```bash
uvicorn app.main:app --reload
```

Open http://127.0.0.1:8000. API documentation is available at `/docs`.

## 4. Controls and symbols

Click a tile to move one step toward it or attack an occupant. Use arrow keys or `hjkl` for cardinal movement and `yubn` for diagonals. `.` waits, `g` picks up, `i` opens the bag, `>` descends, and `r` starts a new game.

| Symbol | Meaning |
|---|---|
| `@` | Player |
| `#` / `.` / `>` | Wall / floor / stairs |
| `r` | Rat; fast |
| `g` | Goblin; flees at low HP |
| `G` | Golem; slow and heavy |
| `W` | Delve Warden; floor-five boss |
| `!` `/` `[` `?` | Potion / Sword / Shield / Recall Scroll |

## 5. Reproduction seeds

Create a specific run through the API:

```bash
curl -X POST http://127.0.0.1:8000/api/game \
  -H "Content-Type: application/json" \
  -d '{"seed": 20260716}'
```

The response always exposes the seed. A bug report should include seed, floor, turn, action sequence, expected behavior, and observed behavior.

## 6. API examples

```bash
# New game
curl -X POST http://127.0.0.1:8000/api/game -H "Content-Type: application/json" -d '{}'

# Move one cell
curl -X POST http://127.0.0.1:8000/api/game/<id>/action \
  -H "Content-Type: application/json" -d '{"type":"move","dir":"north"}'

# Current view
curl http://127.0.0.1:8000/api/game/<id>
```

An invalid action returns 409 and consumes neither a turn nor energy. Unknown games return 404. Invalid request shapes return 422.

## 7. Tests

```bash
pytest
```

The suite covers deterministic dungeon generation, reachability, turn-speed ratios, enemy policies, items, save-format round trips, HTTP contracts, FOV information hiding, and request serialization.

## 8. Railway deployment

`Procfile` contains:

```text
web: python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Railway supplies `$PORT`; binding `0.0.0.0` is required for external access. `python -m uvicorn` does not depend on a console script being on `PATH`. `.python-version` pins Python 3.12.

## 9. AiAkiv connection

Developers verify the folder-bound target before saving. Never commit credentials. Use the canonical identifier compatibility table in [06_memory_protocol.md](06_memory_protocol.md).

## 10. Troubleshooting

| Symptom | Cause or action |
|---|---|
| Game vanished after restart | Expected: active sessions are in memory; Phase 4 persistence is unfinished |
| `ModuleNotFoundError: fastapi` | Activate the virtual environment and install runtime dependencies |
| Same seed creates a different dungeon | Determinism bug; look for randomness bypassing `engine/rng.py` and report the seed |
| Enemy acts at the wrong rate | Start with `tests/test_turn.py` and inspect the integer scheduler |
