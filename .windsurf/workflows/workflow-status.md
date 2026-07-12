---
description: Report which workflow artifacts exist and recommend the next step
---

You are guiding a project through an RFC-driven development workflow with these stages:

| # | Stage | Artifact | Command / Prompt |
|---|-------|----------|------------------|
| 1 | Create PRD | PRD.md | `/create-prd` (interactive-prd-creation-prompt.md) |
| 2 | Verify PRD | PRD.md (improved) | `/verify-prd` (prd-comprehensive-verification-prompt.md) |
| 3 | Extract features | FEATURES.md | `/extract-features` (prd-to-features-prompt.md) |
| 4 | Generate rules | RULES.md | `/generate-rules` (prd-to-rules-prompt.md) |
| 5 | Generate RFCs | RFCs/ folder + RFCS.md | `/generate-rfcs` (prd-to-rfcs-prompt.md) |
| 6 | Implement RFCs (one by one, in order) | Code | `/implement-rfc <id>` (implementation-prompt-template.md) |
| 7 | Review each implementation | Review report | `/review-rfc <id>` (code-review-prompt.md) |
| 8 | Testing strategy | Test plan | `/test-strategy` (testing-strategy-prompt.md) |

Inspect the current project to determine workflow progress:

1. Which artifacts exist: PRD.md, FEATURES.md, RULES.md, RFCS.md, RFCs/ folder?
2. Which RFCs appear implemented in the codebase versus not yet started? Compare each RFC's acceptance criteria against the actual code — do not assume an RFC is done just because code exists.
3. Any signs of drift: code that contradicts the PRD or RULES.md, features in the codebase with no RFC, RFCs skipped out of order?

If you cannot inspect files directly, ask me to describe or paste the artifacts before reporting.

Then report:

1. **Status table** — each workflow stage with its artifact and status (Done / In progress / Missing / Stale)
2. **Inconsistencies** — anything drifted, skipped, or contradictory, with file references
3. **Next step** — the single recommended next action, with the exact command or prompt to run
