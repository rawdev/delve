# 06. Memory Protocol — Consistency Determines Graph Quality

## 0. When to save

Write only after an explicit `ak`, `mweft`, or `memoryweft` request. Save at the moment a decision, implementation result, real bug, review, balance observation, or retrospective conclusion appears. Never batch events later: batching destroys chronology and author attribution.

## 1. Decision-event contract

Every decision event contains:

1. **What** was decided.
2. **Why** it was chosen.
3. **Alternatives and rejection reasons.**
4. **Related commit hash**, plus a repository-relative document path when relevant.

If the decision precedes the commit, save the decision immediately. After implementation, create a separate implementation event containing the hash; existing event prose cannot be retroactively filled in.

## 2. Bug-event contract

Every real bug event contains:

1. **Symptom**, including a reproduction seed when available.
2. **Root cause**, linked to the earlier event or decision that caused it.
3. **Fix.**
4. **Fix commit hash.**

Never plant a bug. If a useful causal bug does not naturally occur, the correct answer is that none occurred.

## 3. One canonical name per entity

The identifiers below are the only intentional Korean text retained in this English repository. They already anchor the historical AiAkiv graph, so translating them would silently create disconnected entities. Use the exact identifier in AK writes; use the English display name everywhere else.

| Canonical AK identifier | English display name | Type | Code | Query |
|---|---|---|---|---|
| `턴 시스템` | Turn system | System | `engine/turn.py` | DQ1 |
| `던전 생성` | Dungeon generation | System | `engine/dungeon.py` | DQ2 |
| `적 AI` | Enemy AI | System | `engine/ai.py` | IQ1 |
| `세이브 포맷` | Save format | Schema | `engine/serialize.py` | BQ3, IQ2 |
| `인벤토리` | Inventory | System | `engine/items.py` | BQ3 |
| `전역 시드` | Global seed | Concept | `engine/rng.py` | bug queries |
| `전투` | Combat | System | `engine/combat.py` | DQ1 |
| `시야` | Field of view | System | `engine/fov.py` | — |
| `Delve` | Delve | Project | whole project | — |
| `AiAkiv` | AiAkiv | Product | — | — |

Do not substitute synonyms, translated forms, repository directory names, or implementation labels in AK entities. Update this table before introducing a new canonical entity.

## 4. Tags

Use two to four existing topic paths spanning different facets such as phase, component, and event type. Do not create tags from IDs, hashes, dates, or one-off wording. Tags aid retrieval; canonical entities carry the durable graph identity.

## 5. Never publish or store

- Real names; use aliases for colleagues.
- API keys, tokens, secrets, credentials, or private URLs.
- Cost or billing figures.
- Unrelated conversation or information about the parent K2G project.
- Any material that cannot safely appear in a public demonstration.

## 6. Long content

Never truncate source material to fit a save. Split content above the service limit and chain chunks with `prev_event_id`.

## 7. Verify the target

Before the first save of a session, verify team `AiAkiv-Roguelike`, project `AiAkiv-roguelike`, domain `default`, and group `root`. Never allow Delve events to land in the parent `k2g` project.

## 8. Per-save checklist

- Was saving explicitly requested with `ak` or an accepted synonym?
- Is the actual author making the save?
- Does a decision include all four elements?
- Does a bug include symptom, root-cause link, fix, and commit?
- Are canonical AK identifiers exact?
- Are there at least two useful existing tags?
- Is the target correct and the content safe to publish?
- If this continues an earlier event, is `prev_event_id` set?
