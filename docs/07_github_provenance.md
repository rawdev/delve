# 07. GitHub Provenance — Bidirectional Commit/Event Links

## 1. Event to code

Every decision and bug-fix event includes its related commit hash. When design precedes implementation, save the decision first and create a separate implementation event after committing.

## 2. Code to event

Use this commit shape:

```text
<type>: <summary>

<body explaining why>

ak:evt_<event id>
docs: docs/xx.md

Co-Authored-By: <AI name> <noreply address>
```

Use one `ak:evt_` line per event. Put repository-relative evidence paths in `docs:`. These trailers make the GitHub side independently navigable.

## 3. AI co-authorship

When an AI materially implements a commit, include its co-author trailer. The AiAkiv event records who designed, implemented, and reviewed; Git records who contributed code.

## 4. Issues and pull requests

Bug issues include the reproduction seed. PR descriptions link related event IDs. A colleague’s GitHub review remains on GitHub and the colleague separately saves their own review summary from their own AiAkiv account.

## 5. Closed public loop

The README links four surfaces: playable game, source repository, unauthenticated static memory, and the live read-only AiAkiv sample project. Static reading answers “why”; the sample project lets users ask new questions.

## 6. Commit hygiene

Never commit names, secrets, costs, private discussion, databases, caches, or environment files. Keep `.env`, `*.db`, and `__pycache__/` ignored.

## 7. Per-commit checklist

- Does the message explain why?
- Are all relevant event IDs present?
- Is the evidence document linked?
- Is AI co-authorship accurate?
- Does the event contain this commit hash, or is a follow-up implementation event required?

## 8. Historical backfill map

Old commits could not be rewritten because rebase would invalidate hashes already embedded in immutable event prose. Git notes were rejected because GitHub does not show them prominently. This append-only mapping restores the missing direction without breaking the direction that still works.

| Commit | Event | Meaning |
|---|---|---|
| `229aaac` | `evt_7f0846bfc503419599493d07176a94d0` | Stack decision |
| `229aaac` | `evt_87b564e85ee14c4695bcec3435671e81` | Pivot replacement |
| `229aaac` | `evt_d61ded1d63a44403857b5881457f70ff` | Memory protocol and document set |
| `229aaac` | `evt_1f08127e492f4077a9914836b843f164` | Phase 0 implementation |
| `ef0c06e` | `evt_1f08127e492f4077a9914836b843f164` | Provenance-protocol correction |
| `ff178e7` | `evt_132fec673db54ee9ad4329928f7e1a00` | Running contract |
| `009ee4d` | `evt_4f8fe2e0e48246a2bc5147eda534d085` | Roadmap as single source of truth |
| `6d78fb8` | `evt_44979725cf6e497598edc5bff3fba4bd` | Dungeon algorithm decision |
| `6d78fb8` | `evt_f9b9fda8c96b47bcb1982c18f32b90df` | RNG/state/dungeon foundation |
| `84d6eca` | `evt_3efb024c216149c69a12e85fe7c43096` | v1 lockstep decision |
| `84d6eca` | `evt_6d1ab84de281468a8b3df413b514b5bd` | FOV/combat/AI/turn v1 |
| `2dbc412` | `evt_fbe97e9dc00b43dd97ae00840f83cd49` | FastAPI boundary and frontend |
