# 02. Game Design — Delve

## 1. Core loop

Explore a procedurally generated floor, fight enemies, collect items, descend, and escape after floor five. One valid player input advances the deterministic turn system. Death is permanent.

## 2. Map and dungeon generation

| Property | Value |
|---|---|
| Map | 64×32 tiles, no camera scrolling |
| Floors | Five; the Warden is on floor five |
| Rooms | Six to ten, generally increasing with depth |
| Room size | 5–12 tiles in each dimension |
| Algorithm | Random rooms, overlap rejection, L-shaped corridors; BSP was rejected as overengineering |
| Tiles | `#` wall, `.` floor, `>` stairs |
| FOV | Radius 8 recursive shadowcasting; current `visible` and remembered `explored` are separate |

Balance v2 removed the floor-one Golem after seed `20260716` showed that an early encounter without preparation was lethal. Golem stats and floors two through five remained unchanged so the rollback altered one variable only. The authoritative values are `engine/dungeon.py::FLOOR_PARAMS`.

## 3. Actors

Actors have identity, position, HP, attack, defense, speed, energy, and AI state. Speed is integer energy gained per scheduler tick.

| Enemy | Glyph | HP | ATK | DEF | Speed | XP | Policy |
|---|---:|---:|---:|---:|---:|---:|---|
| Rat | `r` | 4 | 2 | 0 | 150 | 3 | Always chases within sight; never flees |
| Goblin | `g` | 10 | 4 | 1 | 100 | 8 | Standard chase; flees at or below 30% HP |
| Golem | `G` | 26 | 8 | 4 | 60 | 20 | Slow and heavy; never flees |

The floor-five Warden (`W`) has HP 60, ATK 10, DEF 5, and speed 100; below 50% HP it awakens to speed 150.

The player starts with HP 20, ATK 5, DEF 2, speed 100, and sight radius 8. Required XP is `10 * level`; level-up grants HP +5 and ATK +1, plus DEF +1 every second level.

## 4. Combat

Damage is `max(1, attacker ATK - defender DEF)`. Attacks always hit; there are no critical hits or combat RNG. Tactical depth comes from turn order, not opaque probability.

## 5. Items and inventory

| Item | Glyph | Effect |
|---|---:|---|
| Potion | `!` | Restore 10 HP without exceeding max HP |
| Sword | `/` | +3 ATK while equipped |
| Shield | `[` | +2 DEF while equipped |
| Recall Scroll | `?` | Teleport to a safe tile near the floor entrance |

The bag holds ten items, with one weapon slot and one armor slot. Inventory state forced save format v1→v2, providing the evidence for BQ3.

## 6. Controls

Click a tile to move one step toward it or attack. Arrow keys and `hjkl` also move; `yubn` moves diagonally. `.` waits, `g` picks up, `i` opens the bag, and `>` descends. Buttons expose the same actions without requiring players to memorize keys.

## 7. Rendering

The frontend is a single text-grid HTML file. It starts with zero art assets by design: the project demonstrates a development trail, not an asset pipeline.

## 8. Explicit non-goals

- Status effects, magic, ranged combat, multiplayer, rankings, and accounts
- Sound, animation, or a tile-art pipeline
- More than five floors or more than the defined roster
- Repeated balancing for entertainment; one genuine v1→v2 cycle is sufficient evidence
