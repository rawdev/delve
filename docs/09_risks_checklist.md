# 09. Risks and Checklists

## 1. Risks

### R1. No unauthenticated public-read MCP — realized

The product has no feature that exposes the live graph to anonymous visitors. Adopted model:

| Audience | Access |
|---|---|
| Anonymous visitor | Static HTML export for reading the development trail |
| AiAkiv user | Membership in a live, read-only Delve sample project |

This also solves the empty-account onboarding problem: new users can interrogate a meaningful sample immediately. Remaining cost is the unfinished Phase 5 static exporter and four-way public linking.

### R2. No colleague

Without a separately attributed contributor, IQ2 fails. Secure a colleague or a genuine alternate-account session before relying on cross-user claims.

### R3. Cross-client saves miss the project

If ChatGPT or another client writes elsewhere, IQ1 attribution disappears. Verify the active target and make one test save from every participating account during setup.

### R4. Skipping the real pivot

Implementing v2 directly would erase DQ1. Phase 1 therefore had to ship playable v1 lockstep before unequal speeds created the real constraint.

### R5. Batch-saving history

Bulk retrospectives collapse chronology and attribution. Save each decision, review, and result at the moment it occurs.

### R6. Canonical identifier drift

Synonyms create disconnected graph nodes without an error. Always use the compatibility table in [06_memory_protocol.md](06_memory_protocol.md).

### R7. Scope growth

Trying to make the game broadly entertaining can turn a short evidence project into a long game project. Return to the explicit non-goals in [02_game_design.md](02_game_design.md).

### R8. No “good” causal bug

Accept this outcome. BQ2 is allowed to return no example. Planting a bug would invalidate the entire demonstration.

### R9. Schedule pressure

Compress session density, not the honesty of the timeline. Distinct events and commits matter more than calendar length.

## 2. Phase gate checklist

- [x] Is the repository public and free of secrets?
- [x] Is the AiAkiv target isolated from the parent project?
- [x] Can every participating account save and be retrieved by attribution?
- [x] Are canonical identifiers documented?
- [x] Was v1 genuinely implemented before v2?
- [x] Are decisions and commits linked both ways?
- [x] Are real bugs recorded with root causes rather than planted?

## 3. Publication checklist — unfinished Phase 5

- [ ] Scan the repository and memory for names, secrets, costs, and unrelated material.
- [ ] Export only the intended Delve graph to static HTML.
- [ ] Verify anonymous access to the static trail.
- [ ] Verify read-only enforcement for sample-project members.
- [ ] Verify the target queries against the live graph.
- [ ] Verify every displayed commit link.
- [ ] Cross-link play, source, static memory, and interactive sample.

## 4. Onboarding loop

An anonymous visitor reads the static “why,” follows a prompt to ask their own question, signs up, and receives the live read-only Delve sample. The same sample supports landing-page evidence, devlogs, and the final product tour without inventing separate demo data.
