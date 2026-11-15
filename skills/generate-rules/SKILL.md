---
name: generate-rules
description: "Write RULES.md, the project standards the AI must follow, with registry-verified dependency versions and permanent rule IDs."
metadata:
  source: "https://github.com/nurettincoban/ai-prd-workflow"
  version: "3.1.0"
  checksum: "sha256:9fe395f041af85590e98ee2ea4740edeef50dd5f33a157abcbf90c4d121bef45"
---

You are an expert software architect and technical lead tasked with creating a comprehensive RULES.md file based on the Product Requirements Document (PRD.md) and features list (FEATURES.md), or the documents provided in the conversation. If PRD-REVIEW.md exists, read it as well: the decisions recorded there constrain the rules.

Create a clear, structured RULES.md that establishes technical and general guidelines for AI assistance during the development process. These rules will ensure consistency, quality, and alignment with project requirements.

## WHEN A QUESTION HAS NO ANSWER

If critical information is missing or unclear, ask specific questions before proceeding. If nobody can answer -- the user does not know, or the run is non-interactive -- decide, mark the decision **(assumption)** where you use it, and list every assumption under an `## Open Questions` heading in the file you write, so `/implement-rfc` can put them in front of the user before code depends on them. An assumption may fill a gap; it may never weaken or contradict a requirement in a higher artifact. If a requirement looks wrong or impossible, record that as an open question for PRD.md instead of quietly building something smaller -- that is how "zero data loss" turns into "usually no data loss" three documents later with nobody having decided it.

## PRODUCT TYPE

Read the **Product Type** section of PRD.md and apply only the checks that fit that type; state which checks you skipped and why. Skipping must be visible, never silent. If PRD.md has no such section, classify the product yourself (web app · mobile app · library/SDK · CLI · service/API · data pipeline · game), say that you did, and recommend running `/verify-prd` so the classification is recorded once for every later step.

## GROUND THE RULES IN EXISTING CODE

If a reference implementation, prototype, or existing codebase is available, READ IT and derive naming, structural, and idiom rules from it. Consistency with existing code beats theoretical best practice -- a rule that contradicts the code it governs gets ignored, and rules nobody follows are worse than no rules.

Generate the RULES.md by:

1. TECHNOLOGY STACK DEFINITION:
   - Identify core technologies mentioned or implied in the PRD/features
   - Specify versions for each technology, and VERIFY every one against the actual registry before writing it down (`npm view <pkg> version`, `pip index versions <pkg>`, or the registry's latest endpoint). If you cannot verify a version, write `latest` and mark it "unverified" -- never state a version number from memory. Your training data is older than the registry, and a hallucinated version propagates into the dependency spec and surfaces as a confusing install or build error several steps later, far from its cause
   - Define required libraries, frameworks, or tools

2. TECHNICAL PREFERENCES:
   - Naming conventions for files, components, variables, etc.
   - Folder structure and architectural patterns -- only where the PRD or existing code already fixes them. Design that the RFCs have not done yet does not belong in rules: a rule written ahead of the design ends up in conflict with the RFC that does the design, and outranks it
   - Standards for data handling, state management, and API interactions
   - Performance optimization strategies
   - Security practices and requirements

3. DEVELOPMENT STANDARDS:
   - Testing requirements and coverage expectations
   - Error handling and logging requirements
   - Accessibility and responsive-design requirements, only if the Product Type has a UI
   - Standards for completeness (no TODOs or placeholders) and how to handle ambiguity

4. EVERY RULE MUST BE CHECKABLE:
   - Write a rule only if a reviewer could point at a line of code that breaks it. "Write clean, maintainable code" fails that test; "Functions that touch the database take a transaction parameter" passes
   - `/review-rfc` checks every rule, so a platitude costs review time and teaches the reviewer to skim the rules
   - Do not restate priorities or phasing here: they live in FEATURES.md and RFCS.md, and a second copy drifts

5. RULE IDS:
   - Give every rule a permanent ID with a short category prefix, written as `- **SEC-3**: rule text` (ARCH-1, API-2, SEC-3, TEST-1, ...)
   - IDs are append-only, like feature IDs. If RULES.md already exists, keep every existing ID and its meaning, give new rules the next unused number in their category, and mark retired rules [REMOVED] instead of deleting or reusing them
   - RFCs, reviews and change requests cite rules by these IDs -- a rule without an ID cannot be cited, so it cannot be checked

6. AGENT CONFIGURATION:
   - If the project uses an AI coding agent, recommend wiring RULES.md into its config so the rules stay in context: reference it from CLAUDE.md (Claude Code), AGENTS.md (Codex and others), or .cursor/rules/ (Cursor)

First, provide a brief overview of the project based on the PRD and features list. Then create the RULES.md content. Ensure the rules are specific enough to guide development but flexible enough to allow for creative problem-solving.

## SELF-CHECK BEFORE FINISHING

- Recount every summary table from the actual content. Never carry a count forward from earlier in your own output.
- Verify every internal cross-reference -- feature IDs, rule IDs, RFC numbers, section references -- points at what the surrounding text claims it does. A reference to a VALID but WRONG ID is the dangerous case: nothing looks malformed, so readers are quietly misled.
- Confirm no two tables in the document disagree with each other.
- If `trace-check.py` is available -- in a `scripts/` folder beside these instructions, or in the project's own `scripts/` folder -- run it on the project (`python3 <path>/trace-check.py .`) and fix every FAIL it reports. It checks mechanically what reading does unreliably: that IDs in definitions and RFC header lines resolve, that requirements and Must-have features are covered, RFC dependencies, and review records. It does not check IDs cited in RFC bodies or whether each criterion has a planned test -- check those yourself.
- State that you ran this check and what it turned up.
