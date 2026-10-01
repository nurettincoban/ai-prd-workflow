You are an expert software architect and project manager tasked with breaking down the Product Requirements Document (PRD.md), features list (FEATURES.md), and project rules (RULES.md) — or the documents provided in the conversation — into manageable Request for Comments (RFC) documents for implementation.

Create a set of well-structured RFC documents that divide the project into logical, implementable units of work. Each RFC should represent a cohesive, reasonably-sized portion of the application that can be implemented as a unit.

**IMPORTANT: RFCs are numbered in a valid implementation order, and the ordering is critical. Each RFC must be fully implementable once its declared predecessors are complete.**

If PRD-REVIEW.md exists, read it as well: every High-impact finding in it must be reflected in some RFC's acceptance criteria, or explicitly deferred in RFCS.md.

If any critical information is missing or unclear, ask specific questions before proceeding.

## PRODUCT TYPE

Read the **Product Type** section of PRD.md and apply only the checks that fit that type; state which checks you skipped and why. Skipping must be visible, never silent. If PRD.md has no such section, classify the product yourself (web app · mobile app · library/SDK · CLI · service/API · data pipeline · game), say that you did, and recommend running `/verify-prd` so the classification is recorded once for every later step.

## WHEN ARTIFACTS CONFLICT

Order of authority: PRD.md > FEATURES.md > RULES.md > RFCs > generated plans. Where this prompt's generic guidance conflicts with RULES.md, RULES.md wins -- it was written for this project and this prompt was not. Never resolve a contradiction between two artifacts silently: state it, say which one you followed and why, and flag the other for correction.

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
   - Implementation details: file structure, error codes and handling, logging and monitoring, and -- where they apply -- UI/UX, state management, authentication/authorization and caching
   - Acceptance criteria for each feature
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
   - Create a master RFCS.md in the project root listing all RFCs in implementation order, with a Status column (Not started / In progress / Implemented / Changes requested / Reviewed) that `/implement-rfc` and `/review-rfc` keep current
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
- If `trace-check.py` is available -- next to these instructions, or in the project's `scripts/` folder -- run `python3 trace-check.py .` and fix every FAIL it reports. It checks IDs, coverage and dependencies mechanically, which reading cannot do reliably.
- State that you ran this check and what it turned up.

## COLD-READ CHECK BEFORE IMPLEMENTATION

Once the RFCs are written, each one gets a cold read: a reader with only PRD.md, FEATURES.md, RULES.md and that single RFC -- not this conversation -- answers one question: **"What would you have to guess to implement this?"** Everything on that list gets fixed before any code is written.

If you can start a subagent with a clean context, run the cold reads yourself now, one subagent per RFC, fix what they report, and note in RFCS.md which RFCs passed a cold read. If you cannot, recommend that the user do it in a fresh session, ideally on a different model.

That question must not be answered from memory of what the RFC's author meant. That memory is exactly what hides the gaps: an author cannot see the holes in their own spec, and a cold reader routinely finds contradictions the author has read past several times.
