# 08. Participants and Session Workflow

## 1. Roles

| Participant | Role | Evidence |
|---|---|---|
| `rawdev` | Lead developer; decisions, implementation, retrospectives | DQ, BQ |
| One colleague / `@critic` | Playtester and reviewer | IQ2, balance |
| Claude Code / `@developer` | Primary implementation AI | IQ1 implementation |
| ChatGPT / `@critic` | Design and balance critic | IQ1 design |
| Gemini, optional | Independent review | IQ1 review |

## 2. Real colleague contribution

Cross-user evidence cannot be narrated by the owner. The colleague must contribute from their own account through a playtest, code review, or direct fix. An alternate account with a stable alias is acceptable when it represents a genuinely separate session and attribution source.

## 3. AI attribution

Each AI saves only from its own session. Do not copy another author’s conclusion into an event attributed to yourself. The server-stamped principal is the evidence.

## 4. Enemy-AI collaboration example

1. ChatGPT designs the Rat/Goblin/Golem policy and rejects alternatives.
2. Claude Code implements `engine/ai.py`, tests it, and commits with provenance.
3. An independent reviewer inspects edge cases.
4. The owner decides which findings to accept and records the outcome.

All events use the same existing AK canonical identifier **“적 AI”**.

## 5. Session workflow

At session start:

1. Check the active AK target.
2. Read the previous session from AK.
3. Read [05_roadmap.md](05_roadmap.md).

At session end:

1. Confirm every decision was saved under the protocol.
2. Confirm commits and events link both ways.
3. Update roadmap checkboxes.

One session should reach one coherent milestone. Save decisions when they occur, not as a bulk retrospective.

## 6. Memory-recall demonstration

For a real bug, begin a fresh session, retrieve the related decisions from AK, diagnose from those links, implement the fix, and record both the successful recall and the resulting commit. Do not provide the answer manually to the recalling AI.
