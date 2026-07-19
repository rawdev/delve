# 01. Demo Goals — Interrogation Queries and Query-driven Design

## What “design backward from queries” means

The demonstration is judged by the questions a visitor can answer, not by a screenshot of a graph. Each target query therefore defines the real events, shared entities, attribution, and provenance that development must produce. The events must arise naturally; the query never licenses staging history or planting bugs.

## A. Design evolution

### DQ1. “How has the combat/turn-system design changed?”

Show a causal chain rather than one isolated decision: v1 lockstep resolution was correct while there was one enemy speed, then Rat/Goblin/Golem speeds made it insufficient, alternatives were compared, and the integer energy scheduler became v2. Both decisions must share the canonical AK identifier **“턴 시스템”**.

### DQ2. “Show the history of dungeon balance.”

Show temporal evolution: initial floor parameters, colleague playtest, observed difficulty with a reproducible seed, the smallest rollback, and a same-seed retest. These must be separate events sharing **“던전 생성”**; compressing them into one retrospective event destroys the timeline.

## B. Implementation and attribution

### IQ1. “How was enemy AI implemented?”

Show cross-AI attribution: one AI designs the policy contract, another implements it, and another reviews it. All three events share **“적 AI”**, and each event is saved by the actual author rather than by a narrator impersonating them.

### IQ2. “What did the colleague identify or fix around save/load?”

Show cross-user retrieval through the `@handle` prefix. The contribution must be saved from the colleague’s own account and may be a code review finding, playtest observation, or fix. Relevant events share **“세이브 포맷”**.

## C. Bugs — leave the query open and use only real failures

### BQ1. “What was the latest bug and its cause?”

The query assumes no particular bug. Every real bug must be stored with symptom, root-cause link, fix, and commit. Whatever was most recently fixed becomes the answer.

### BQ2. “Did an old design decision cause any recently fixed bug?”

This tests a causal jump that keyword search cannot reliably make. If such a bug occurs, link it to the earlier decision. If none occurs, say so honestly; never create one.

### BQ3. “Why did inventory and save format change together?”

Inventory necessarily changes serialized state. The inventory implementation and format migration must be separate events connected through **“세이브 포맷”**.

## D. Provenance

### PQ. “Show the commit that implemented this decision or fix.”

Every decision and bug-fix event must contain a commit hash, while the commit message points back to the event. This creates bidirectional provenance.

## Summary matrix

| Query | Required evidence | Phase | Canonical AK identifier | Author |
|---|---|---|---|---|
| DQ1 | v1 decision → real constraint → v2 decision | 1→2 | `턴 시스템` | owner |
| DQ2 | v1 → test → rollback → v2/retest | 3 | `던전 생성` | owner + colleague |
| IQ1 | design, implementation, review by different AIs | 2 | `적 AI` | ChatGPT/Claude/Gemini |
| IQ2 | colleague review, feedback, or fix | 2–4 | `세이브 포맷` | colleague account |
| BQ1 | every real bug stored using the bug contract | all | bug-specific | anyone |
| BQ2 | a real bug linked to an older decision, if one occurs | expected 4 | cause link | owner |
| BQ3 | inventory and format-migration events | 2 | `세이브 포맷` | owner |
| PQ | event hash and commit back-reference | all | — | everyone |
