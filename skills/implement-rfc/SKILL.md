---
name: implement-rfc
description: "Implement one RFC: check its predecessors, present a plan for approval, write the code, then demonstrate every acceptance criterion."
argument-hint: "<rfc-id>"
metadata:
  source: "https://github.com/nurettincoban/ai-prd-workflow"
  version: "3.2.0"
  checksum: "sha256:68a6e286854f5ab7d1f60c15d292bdf13a707ac6107547277dafb100dd2b06f7"
---

Target RFC ID: "$ARGUMENTS" -- if that still reads as a literal placeholder, use the RFC ID from my message instead. Substitute it for [ID] everywhere below. If no ID was given, ask which RFC to work on before doing anything else.

# Implement RFC-[ID]

## Context
This implementation covers RFC-[ID]. Refer to:
- PRD.md for overall product requirements
- FEATURES.md for detailed feature specifications
- RULES.md for project guidelines and standards
- The RFC itself, `RFCs/RFC-[ID]-*.md`, for the specific requirements being implemented
- RFCS.md for the RFC's declared predecessors and their status, its `## Open conflicts` list, and any `## Follow-ups` filed against this RFC by earlier reviews
- `reviews/REVIEW-RFC-[ID].md`, if it exists: an earlier review of this RFC, whose blocking issues come before anything else
- `cold-reads/` and the cold-read result in RFCS.md: an RFC that has not passed its cold read still has guesses in it
- TEST-STRATEGY.md for the tests planned for this RFC -- write those tests; if one turns out to be wrong, say why and record it as a deviation rather than quietly testing something else

## WHEN ARTIFACTS CONFLICT

Order of authority: PRD.md > FEATURES.md > RULES.md > RFCs > generated plans. Where this prompt's generic guidance conflicts with RULES.md, RULES.md wins -- it was written for this project and this prompt was not. Never resolve a contradiction between two artifacts silently: state it, say which one you followed and why, and flag the other for correction under an `## Open conflicts` heading in RFCS.md (in the file you write, if RFCS.md does not exist yet). `/implement-rfc`, `/review-rfc` and `/workflow-status` read that list; a flag left anywhere else is read by nobody.

## Two-Phase Approach

### Phase 1: Planning (No Code)
1. Check the RFC's declared predecessors. Each must have Status Implemented or Reviewed in RFCS.md; Changes requested and Spec changed do not count, because the interface may still change. If any falls short, stop and tell me which one -- code built on a missing predecessor is written against an interface nobody has built. Continue only if I explicitly tell you to
2. Analyze the requirements and existing codebase
3. Present a comprehensive implementation plan covering:
   - Files to create or modify
   - Key components, data structures, and APIs
   - Proposed implementation sequence
   - Technical decisions and trade-offs
   - Potential impacts on existing functionality
   - **What this RFC rests on that nobody has confirmed**: every **(assumption)** in the RFC, every open question in PRD.md, FEATURES.md or RULES.md that it depends on, and every entry under `## Open conflicts` in RFCS.md that touches it, and any guess its cold read left open. Ask me to confirm or change each one. This is the last point where a guess costs a sentence to fix instead of a rewrite
4. Wait for explicit user approval before proceeding
5. Address any feedback or modifications from the user

If nobody can approve -- the run is non-interactive -- write the plan into `## Implementation Notes` and proceed only if no open High conflict touches this RFC; otherwise stop and report it. Record in the notes that the plan was not approved, so the reviewer and `/workflow-status` can see it.

### Phase 2: Implementation (After Approval Only)
Set this RFC's Status in RFCS.md to In progress when you start.
1. Follow the approved plan. Record every deviation from the RFC or the plan in the RFC file itself, under a final `## Implementation Notes` section: what changed, why, and whether I approved it. The reviewer works in a fresh session from the files alone -- a deviation explained only in chat is indistinguishable from a bug
2. Implement in logical segments as outlined
3. Explain your approach for complex sections
4. Self-review before finalizing

## Implementation Standards
1. Follow all conventions in RULES.md
2. Do not create workarounds. If you encounter a challenge:
   a. Explain the challenge clearly
   b. Propose a proper architectural solution
   c. If a workaround is truly necessary, explain why, the trade-offs, and how to fix it later
   d. Flag workarounds with `WORKAROUND: [explanation]` in comments
   e. Never implement a workaround without user approval
3. Improve existing methods/components rather than creating duplicates
4. Test what can go wrong, not only what the criteria list. A criterion such as "fsync is called before the rename" is met by a test that checks the call order, and that test still passes when the data written before the fsync is empty. For each property a user relies on (no data lost, no partial file, the right exit code), break the code on purpose and check that a test fails

## Scope Limitation
Only implement features in this RFC. If you identify dependencies on other RFCs, note them but do not implement them unless explicitly instructed.

## Final Deliverables
1. All code changes necessary to implement the RFC
2. Necessary tests per the project's testing standards
3. Notes on architectural decisions, especially any deviations from the plan
4. **STATUS** -- set this RFC's Status in RFCS.md to Implemented once the verification below passes; leave it In progress, and say why, if it does not. This applies to a fix round after Changes requested too: Implemented means "waiting for review", and only `/review-rfc` sets Reviewed
5. **FILES CHANGED** -- under `## Implementation Notes` in the RFC, list every file this RFC created or modified and the commit or branch that holds them. The reviewer starts in a fresh session with no diff; without this list it either audits the whole repository or only the files the RFC predicted
6. **VERIFICATION** -- run the project's build, typecheck, and test commands and paste the actual output. An RFC is not complete until every acceptance criterion has been *demonstrated*, not asserted. If a criterion cannot be verified automatically, say so and describe the manual check; a check that needs a person or another machine belongs in RFCS.md's release checklist and does not keep the RFC In progress. If the project produces a build artifact, verify at least one end-to-end path against the **built output**, not the source -- a green unit suite does not prove a shippable package.
