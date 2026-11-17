You are guiding a project through an RFC-driven development workflow with these stages:

| # | Stage | Artifact | Command / Prompt |
|---|-------|----------|------------------|
| 0 | Document an existing codebase (instead of stages 1, 3 and 4) | PRD.md, FEATURES.md, RULES.md | `/document-existing` (document-existing-prompt.md) |
| 1 | Create PRD | PRD.md | `/create-prd` (interactive-prd-creation-prompt.md) |
| 2 | Verify PRD | PRD.md (improved) + PRD-REVIEW.md | `/verify-prd` (prd-comprehensive-verification-prompt.md) |
| 3 | Extract features | FEATURES.md | `/extract-features` (prd-to-features-prompt.md) |
| 4 | Generate rules | RULES.md | `/generate-rules` (prd-to-rules-prompt.md) |
| 5 | Generate RFCs | RFCs/ folder + RFCS.md | `/generate-rfcs` (prd-to-rfcs-prompt.md) |
| 6 | Testing strategy | TEST-STRATEGY.md | `/test-strategy` (testing-strategy-prompt.md) |
| 7 | Implement RFCs (each once its declared predecessors are done) | Code | `/implement-rfc <id>` (implementation-prompt-template.md) |
| 8 | Review each implementation | `reviews/REVIEW-RFC-<id>.md` | `/review-rfc <id>` (code-review-prompt.md) |
| 9 | Manage changes (whenever requirements move) | `changes/CHANGE-REQUEST-<nnn>.md` | `/manage-changes` (prd-change-management-prompt.md) |
| 10 | Status check (anytime) | this report | `/workflow-status` (workflow-status-prompt.md) |

Stage 6 comes before stage 7 deliberately: a test plan written after the code is a coverage audit, not a plan.

Inspect the current project to determine workflow progress. If `trace-check.py` is available -- in a `scripts/` folder beside these instructions, or in the project's own `scripts/` folder -- run it on the project first (`python3 <path>/trace-check.py .`): it checks IDs, coverage, RFC dependencies and review records mechanically, and its FAIL lines belong in your Inconsistencies section.

1. Which artifacts exist: PRD.md, PRD-REVIEW.md, FEATURES.md, RULES.md, RFCS.md, RFCs/ folder, TEST-STRATEGY.md, reviews/, changes/?
2. Which RFCs are implemented? Start from the Status column in RFCS.md, which `/implement-rfc`, `/review-rfc` and `/manage-changes` keep current, then verify it: spot-check the acceptance criteria of every RFC it marks Implemented or Reviewed against the actual code, and report any status the code does not support. Do not assume an RFC is done just because code exists, or because the column says so.
3. Which RFCs have been reviewed? Check `reviews/` for a report per implemented RFC. An RFC counts as reviewed only if its Status is Reviewed and the last `## Round` of its review has no blocking issues; an RFC back at Implemented after Changes requested has an old review on file and fixes nobody has reviewed yet — an implemented RFC with no review is the most common real-world gap, and reviews are exactly what gets skipped under deadline.
4. What is still unconfirmed? Count the open questions and **(assumption)** markers in PRD.md, FEATURES.md, RULES.md and the RFCs, the entries under `## Open conflicts` in RFCS.md, and the open `## Follow-ups` there. Name the ones an RFC that is In progress or Implemented depends on: that is code built on a guess nobody confirmed.
5. Are there open change requests in `changes/` whose decisions are still pending?
6. Any signs of drift: code that contradicts the PRD or RULES.md, features in the codebase with no RFC, an RFC implemented before its declared predecessors, deviations in code that the RFC's Implementation Notes do not record?
7. Read the RFCs against each other, not only against the PRD. For each RFC, list what it uses that it does not build -- tables, endpoints, modules, jobs -- and check that the RFC building it is in its **Depends on** line: an undeclared predecessor passes `trace-check.py` and fails at implementation. Also look for an RFC that contradicts itself (its approach against its own criteria), and for a feature an RFC claims but whose criteria never test, such as a UI that only the Features line mentions.
8. Read RULES.md for versions stated from memory: a runtime or framework release past its end of life is drift nobody wrote down.

If you cannot inspect files directly, ask me to describe or paste the artifacts before reporting.

Then report:

1. **Status table** — each workflow stage with its artifact and status (Done / In progress / Missing / Stale / Not needed -- `changes/` with no change requests is Not needed, not Missing)
2. **Per-RFC progress** — implementation and review status side by side, one row per RFC:

   ```
   RFC-001  Reviewed          implemented ✅   reviewed ✅
   RFC-002  Changes requested implemented ✅   reviewed ❌ (blocking issues open)
   RFC-003  In progress       implemented ❌   reviewed ❌
   ```

   A single "reviews done" row hides which RFCs were actually reviewed. Report them individually.
3. **Inconsistencies** — anything drifted, skipped, or contradictory, with file references
4. **Next step** — the single recommended next action, with the exact command or prompt to run
