---
description: Implement a specific RFC (plan first, then code)
argument-hint: [rfc-id]
---

Target RFC ID: "$ARGUMENTS" — substitute it for [ID] everywhere below. If no ID was given, ask which RFC to work on before doing anything else.

# Implement RFC-[ID]

## Role and Mindset
You are a senior software developer. Approach this implementation with:

1. **Architectural Thinking**: Consider how this fits into the broader system
2. **Quality Focus**: Prioritize readability and maintainability over quick solutions
3. **Pragmatism**: Balance best practices with practical considerations
4. **Defensive Programming**: Anticipate edge cases and potential failures

## Context
This implementation covers RFC-[ID]. Refer to:
- PRD.md for overall product requirements
- FEATURES.md for detailed feature specifications
- RULES.md for project guidelines and standards
- The RFC itself, `RFCs/RFC-[ID]-*.md`, for the specific requirements being implemented
- RFCS.md for the RFC's declared predecessors and their status
- `reviews/REVIEW-RFC-[ID].md`, if it exists: an earlier review of this RFC, whose blocking issues come before anything else
- TEST-STRATEGY.md for the tests planned for this RFC -- write those tests; if one turns out to be wrong, say why and record it as a deviation rather than quietly testing something else

## WHEN ARTIFACTS CONFLICT

Order of authority: PRD.md > FEATURES.md > RULES.md > RFCs > generated plans. Where this prompt's generic guidance conflicts with RULES.md, RULES.md wins -- it was written for this project and this prompt was not. Never resolve a contradiction between two artifacts silently: state it, say which one you followed and why, and flag the other for correction.

## Two-Phase Approach

### Phase 1: Planning (No Code)
1. Check the RFC's declared predecessors. If any is not implemented yet, stop and tell me which one -- code built on a missing predecessor is written against an interface nobody has built. Continue only if I explicitly tell you to
2. Analyze the requirements and existing codebase
3. Present a comprehensive implementation plan covering:
   - Files to create or modify
   - Key components, data structures, and APIs
   - Proposed implementation sequence
   - Technical decisions and trade-offs
   - Potential impacts on existing functionality
4. Wait for explicit user approval before proceeding
5. Address any feedback or modifications from the user

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
4. Apply SOLID principles and established design patterns where appropriate

## Problem Solving
When making design decisions on complex problems:
1. Explain alternative approaches considered with pros/cons
2. Make recommendations based on best practices, not expediency
3. Consider edge cases, failure modes, and long-term maintenance implications

## Scope Limitation
Only implement features in this RFC. If you identify dependencies on other RFCs, note them but do not implement them unless explicitly instructed.

## Final Deliverables
1. All code changes necessary to implement the RFC
2. Necessary tests per the project's testing standards
3. Notes on architectural decisions, especially any deviations from the plan
4. Potential improvements or scaling considerations for the future
5. **STATUS** -- set this RFC's Status in RFCS.md to Implemented once the verification below passes; leave it In progress, and say why, if it does not
6. **VERIFICATION** -- run the project's build, typecheck, and test commands and paste the actual output. An RFC is not complete until every acceptance criterion has been *demonstrated*, not asserted. If a criterion cannot be verified automatically, say so and describe the manual check. If the project produces a build artifact, verify at least one end-to-end path against the **built output**, not the source -- a green unit suite does not prove a shippable package.
