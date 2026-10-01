You are guiding a project through an RFC-driven development workflow with these stages:

| # | Stage | Artifact | Command / Prompt |
|---|-------|----------|------------------|
| 1 | Create PRD | PRD.md | `/create-prd` (interactive-prd-creation-prompt.md) |
| 2 | Verify PRD | PRD.md (improved) + PRD-REVIEW.md | `/verify-prd` (prd-comprehensive-verification-prompt.md) |
| 3 | Extract features | FEATURES.md | `/extract-features` (prd-to-features-prompt.md) |
| 4 | Generate rules | RULES.md | `/generate-rules` (prd-to-rules-prompt.md) |
| 5 | Generate RFCs | RFCs/ folder + RFCS.md | `/generate-rfcs` (prd-to-rfcs-prompt.md) |
| 6 | Testing strategy | TEST-STRATEGY.md | `/test-strategy` (testing-strategy-prompt.md) |
| 7 | Implement RFCs (one by one, in order) | Code | `/implement-rfc <id>` (implementation-prompt-template.md) |
| 8 | Review each implementation | `reviews/REVIEW-RFC-<id>.md` | `/review-rfc <id>` (code-review-prompt.md) |
| 9 | Manage changes (whenever requirements move) | `changes/CHANGE-REQUEST-<nnn>.md` | `/manage-changes` (prd-change-management-prompt.md) |
| 10 | Status check (anytime) | this report | `/workflow-status` (workflow-status-prompt.md) |

Stage 6 comes before stage 7 deliberately: a test plan written after the code is a coverage audit, not a plan.

Inspect the current project to determine workflow progress:

1. Which artifacts exist: PRD.md, PRD-REVIEW.md, FEATURES.md, RULES.md, RFCS.md, RFCs/ folder, reviews/, changes/?
2. Which RFCs appear implemented in the codebase versus not yet started? Compare each RFC's acceptance criteria against the actual code — do not assume an RFC is done just because code exists.
3. Which RFCs have been reviewed? Check `reviews/` for a report per implemented RFC — an implemented RFC with no review is the most common real-world gap, and reviews are exactly what gets skipped under deadline.
4. Are there open change requests in `changes/` whose decisions are still pending?
5. Any signs of drift: code that contradicts the PRD or RULES.md, features in the codebase with no RFC, RFCs skipped out of order?

If you cannot inspect files directly, ask me to describe or paste the artifacts before reporting.

Then report:

1. **Status table** — each workflow stage with its artifact and status (Done / In progress / Missing / Stale)
2. **Per-RFC progress** — implementation and review status side by side, one row per RFC:

   ```
   RFC-001  implemented ✅   reviewed ❌
   RFC-002  implemented ✅   reviewed ❌
   RFC-003  implemented ✅   reviewed ✅
   ```

   A single "reviews done" row hides which RFCs were actually reviewed. Report them individually.
3. **Inconsistencies** — anything drifted, skipped, or contradictory, with file references
4. **Next step** — the single recommended next action, with the exact command or prompt to run
