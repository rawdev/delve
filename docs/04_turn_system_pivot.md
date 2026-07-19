# 04. Architectural Pivot — Lockstep to an Energy Scheduler

## 0. Why this pivot

The original proposal staged a real-time game and later converted it to turn-based play. That transition would not be genuine in a server-authoritative FastAPI design. Instead, Delve uses a constraint that naturally appears during development: one enemy speed works with lockstep turns, but three unequal speeds do not.

## 1. v1 lockstep — implemented and shipped in Phase 1

One valid player input caused the player and every living enemy to act exactly once. With one enemy type and no speed mechanic, this was the smallest correct design, not a mistake. The energy scheduler was rejected at this stage as needless complexity.

Decision contract:

- **What:** one input equals one action for every actor.
- **Why:** it made the core loop playable with the fewest moving parts.
- **Rejected alternative:** an energy system had no benefit under the Phase 1 constraints.
- **Evidence:** the actual Phase 1 implementation and commit.

## 2. The real fracture in Phase 2

| Enemy | Speed | Intended behavior |
|---|---:|---|
| Rat | 150 | 1.5× the player’s rate |
| Goblin | 100 | equal to the player |
| Golem | 60 | 0.6× the player’s rate |

Lockstep cannot express those ratios: every enemy still acts once per input. A failing or constraining test makes this mismatch observable before the rewrite.

## 3. Alternatives

### A. Keep lockstep and add per-enemy counters — rejected

This is quick and minimally invasive, but it duplicates scheduling state, handles the player asymmetrically, and grows special cases for every future speed effect.

### B. Float-time priority queue — rejected

This is general and supports variable action costs, but float ordering complicates serialization and can undermine exact replay. It is more machinery than this small game needs.

### C. Integer energy — adopted

Every internal tick adds each actor’s integer speed. An actor may act while energy is at least 100 and spends 100 per action. Stable actor order breaks ties. Residual energy carries forward.

The corrected execution order is:

1. A new player starts with energy 100.
2. Apply one valid player action and subtract 100.
3. Advance internal ticks until the player reaches 100 again.
4. On each tick, every living actor gains `speed`.
5. Enemies act in stable list order while their energy is at least 100.
6. Return once the player can act again.
7. Preserve residual energy for the next input.

Integers preserve deterministic replay, represent all three speeds, and treat player and enemies symmetrically.

## 4. Actual migration cost

| Area | Change |
|---|---|
| `engine/state.py` | Add `speed` and `energy` to `Actor` |
| `engine/turn.py` | Rewrite turn advancement around integer energy |
| `engine/ai.py` | No change to `decide()`; payoff from layer separation |
| `app/schemas.py` | Add ordered `events[]` to action responses |
| `static/index.html` | Render consecutive enemy actions in order |
| `tests/test_turn.py` | Verify action-count ratios and deterministic ordering |

The turn counter remains the number of player actions, not internal ticks, preserving the meaning of `(seed, floor, turn)` across v1 and v2.

## 5. Evidence rules

1. Implement, commit, and play v1 before Phase 2.
2. Add the three speeds and observe the real limitation.
3. Compare A/B/C only then and record the decision.
4. Both decisions share the existing AK canonical identifier **“턴 시스템”**.
5. The events must have real elapsed time and distinct commits; otherwise the chain is staged.
