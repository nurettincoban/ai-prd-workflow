---
name: generate-rfcs
description: "Break the PRD into sequenced implementation RFCs under RFCs/ with an RFCS.md index, then cold-read each RFC for gaps."
metadata:
  source: "https://github.com/nurettincoban/ai-prd-workflow"
  version: "3.1.0"
  checksum: "sha256:536d6262e27d9e86ca60b657051254d1d6aed4fee9baf0ae37528397678abd46"
---

You are an expert software architect and project manager tasked with breaking down the Product Requirements Document (PRD.md), features list (FEATURES.md), and project rules (RULES.md) — or the documents provided in the conversation — into manageable Request for Comments (RFC) documents for implementation.

Create a set of well-structured RFC documents that divide the project into logical, implementable units of work. Each RFC should represent a cohesive, reasonably-sized portion of the application that can be implemented as a unit.

**IMPORTANT: RFCs are numbered in a valid implementation order, and the ordering is critical. Each RFC must be fully implementable once its declared predecessors are complete.**

If PRD-REVIEW.md exists, read it as well: every High-impact finding in it must be reflected in some RFC's acceptance criteria, or explicitly deferred in RFCS.md.

## WHEN A QUESTION HAS NO ANSWER

If critical information is missing or unclear, ask specific questions before proceeding. If nobody can answer -- the user does not know, or the run is non-interactive -- decide, mark the decision **(assumption)** where you use it, and list every assumption under an `## Open Questions` heading in the file you write, so `/implement-rfc` can put them in front of the user before code depends on them. An assumption may fill a gap; it may never weaken or contradict a requirement in a higher artifact. If a requirement looks wrong or impossible, record that as an open question for PRD.md instead of quietly building something smaller -- that is how "zero data loss" turns into "usually no data loss" three documents later with nobody having decided it.

## PRODUCT TYPE

Read the **Product Type** section of PRD.md and apply only the checks that fit that type; state which checks you skipped and why. Skipping must be visible, never silent. If PRD.md has no such section, classify the product yourself (web app · mobile app · library/SDK · CLI · service/API · data pipeline · game), say that you did, and recommend running `/verify-prd` so the classification is recorded once for every later step.

## WHEN ARTIFACTS CONFLICT

Order of authority: PRD.md > FEATURES.md > RULES.md > RFCs > generated plans. Where this prompt's generic guidance conflicts with RULES.md, RULES.md wins -- it was written for this project and this prompt was not. Never resolve a contradiction between two artifacts silently: state it, say which one you followed and why, and flag the other for correction under an `## Open conflicts` heading in RFCS.md (in the file you write, if RFCS.md does not exist yet). `/implement-rfc`, `/review-rfc` and `/workflow-status` read that list; a flag left anywhere else is read by nobody.

## WHEN RFCS ALREADY EXIST

If RFCs/ already has RFCs, extend the plan instead of regenerating it. Never renumber, rewrite or delete an RFC whose Status in RFCS.md is past Not started: its code, its `## Implementation Notes` and its file in `reviews/` all refer to it by number, and a regenerated RFC-001 that means something else silently attaches an old review to new work. New work takes the next unused number. Keep every existing Status value. A Not started RFC may be revised; say what changed.

## GENERATE THE RFCS

Generate the RFC files under an RFCs folder by:

1. IMPLEMENTATION ORDER ANALYSIS:
   - Analyze the entire project to determine the optimal implementation sequence
   - Identify foundation components that must be built first
   - Create a directed graph of feature dependencies (described textually)
   - Determine critical path items that block other development
   - Assign sequential numbers (001, 002, 003, etc.) reflecting a valid topological order of that graph
   - **CRITICAL**: Each RFC must be fully implementable once its DECLARED PREDECESSORS are complete -- not necessarily all lower-numbered RFCs. State each RFC's true predecessors, so a team can parallelize independent branches while a solo implementer simply follows the numbers in order.

2. FEATURE GROUPING:
   - Group related features that should be implemented together in a single RFC
   - Ensure each RFC represents a logical, cohesive unit of functionality
   - Balance RFC size -- not too small (trivial) or too large (unmanageable)
   - Consider dependencies between features when grouping
   - Identify shared components that multiple features depend on
   - Features with Status `Implemented` (written by `/document-existing`) already exist: do not plan them, but reference them where a new RFC builds on them

3. RFC STRUCTURE:
   Name each file `RFCs/RFC-001-Short-Title.md` and put these four lines right under its title, exactly as shown, so tools and later commands can trace it:
   ```
   **Features**: F3, F7
   **Depends on**: RFC-001, RFC-002   (or: none)
   **Rules**: ARCH-1, SEC-2
   **Complexity**: Low | Medium | High
   ```
   Then include:
   - Summary of what the RFC covers
   - Technical approach: component architecture and data flow (described textually), key algorithms as pseudocode
   - API contracts or interfaces exposed, and data models or schema changes
   - Implementation details -- what other RFCs and users depend on, not how to write each function: file structure, error codes and handling, logging and monitoring, and -- where they apply -- UI/UX, state management, authentication/authorization and caching
   - Acceptance criteria for each feature: observable behavior a test can check. Do not add criteria that restate RULES.md ("files follow ARCH-1", "tests are named after features") -- the reviewer already checks every rule, and a criterion nobody can test becomes a manual row in every plan. If an RFC needs more than about 15 criteria, split it: `/implement-rfc` has to demonstrate each one
   - Only the sections that apply to this product type and this RFC: no "Database Schema Changes" or "State Management" section in an RFC, or a product, that has neither
   - Every file, behavior and constraint mentioned anywhere in the RFC MUST also appear in the acceptance criteria. In practice the acceptance criteria are the spec and everything else is commentary: anything named in prose but absent from the criteria is effectively optional and will not get built. Cross-check the file-structure section against the criteria before finishing

4. IMPLEMENTATION CONSIDERATIONS:
   - Technical challenges and potential edge cases
   - The rules from RULES.md that apply, by ID
   - Testing approach for the functionality
   - Performance budgets, and security, accessibility and compatibility requirements (browsers, devices, platforms) where they apply
   - Regulatory or compliance considerations
   - Third-party dependencies or libraries needed
   - Error handling strategies and fallback mechanisms

5. IMPLEMENTATION HANDOFF:
   - Note in RFCS.md that each RFC is implemented by running `/implement-rfc <id>`
   - Do not generate per-RFC implementation prompt files. They duplicate that command and drift from it as soon as it is improved

6. RFCS.MD CREATION:
   - Create a master RFCS.md in the project root listing all RFCs in implementation order, each by its full ID as in the file name (`RFC-001`, never `RFC-1`), with a Status column (Not started / In progress / Implemented / Changes requested / Spec changed / Reviewed) that `/implement-rfc`, `/review-rfc` and `/manage-changes` keep current
   - End RFCS.md with an `## Open conflicts` section: every conflict between artifacts you found and how each RFC resolved it, and every High-impact open question in PRD.md that an RFC depends on. `/implement-rfc` puts these in front of the user before writing code; a conflict recorded anywhere else is read by nobody
   - Every Must Have feature belongs to an RFC. Should and Could Have features either belong to one or are listed in RFCS.md as deferred, with the reason
   - Include a dependency table showing relationships between RFCs
   - Provide a clear implementation roadmap
   - For each RFC, indicate predecessors and successors

First, provide a brief overview of your breakdown approach and the sequential implementation order. Then create the RFC documents.

Each RFC should be specific enough to guide implementation but flexible enough to allow for engineering decisions. The goal is to provide AI implementers with complete, unambiguous specifications that enable high-quality code without additional clarification.

## SELF-CHECK BEFORE FINISHING

- Recount every summary table from the actual content. Never carry a count forward from earlier in your own output.
- Verify every internal cross-reference -- feature IDs, rule IDs, RFC numbers, section references -- points at what the surrounding text claims it does. A reference to a VALID but WRONG ID is the dangerous case: nothing looks malformed, so readers are quietly misled.
- Confirm no two tables in the document disagree with each other.
- If `trace-check.py` is available -- in a `scripts/` folder beside these instructions, or in the project's own `scripts/` folder -- run it on the project (`python3 <path>/trace-check.py .`) and fix every FAIL it reports. It checks mechanically what reading does unreliably: that IDs in definitions and RFC header lines resolve, that requirements and Must-have features are covered, RFC dependencies, and review records. It does not check IDs cited in RFC bodies or whether each criterion has a planned test -- check those yourself.
- State that you ran this check and what it turned up.

## COLD-READ CHECK BEFORE IMPLEMENTATION

Once the RFCs are written, each one gets a cold read: a reader with only PRD.md, FEATURES.md, RULES.md, that RFC and every RFC it depends on, directly or through another RFC -- not this conversation -- answers one question: **"What would you have to guess to implement this?"** The predecessors are included because the implementer will have them: a reader without them spends most of its report on interfaces a predecessor already pins down, and the real gaps get lost in that list.

Fix the guesses that change observable behavior or an interface another RFC uses. List the rest in the RFC as the implementer's choice instead of specifying them: a cold reader always finds more to pin down, and an RFC that pins down everything stops being a spec and becomes code written in prose.

If you can start a subagent with a clean context, run the cold reads yourself now, one subagent per RFC, fix what they report, and cold-read the changed RFCs again before you note in RFCS.md that they passed -- a fix is new text that nobody has read cold. If you cannot, recommend that the user do it in a fresh session, ideally on a different model.

That question must not be answered from memory of what the RFC's author meant. That memory is exactly what hides the gaps: an author cannot see the holes in their own spec, and a cold reader routinely finds contradictions the author has read past several times.
