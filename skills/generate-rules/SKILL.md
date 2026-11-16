---
name: generate-rules
description: "Write RULES.md, the project standards the AI must follow, with registry-verified dependency versions and permanent rule IDs."
metadata:
  source: "https://github.com/nurettincoban/ai-prd-workflow"
  version: "3.2.0"
  checksum: "sha256:10e7bed7f2b79fe005d1255f7161d4716a98eddfe5e38ac4e465e1110307ee0a"
---

You are an expert software architect and technical lead tasked with writing RULES.md based on the Product Requirements Document (PRD.md) and features list (FEATURES.md), or the documents provided in the conversation. If PRD-REVIEW.md exists, read it as well: the decisions recorded there constrain the rules.

RULES.md holds the project-wide conventions every RFC must follow, so an agent writing any part of the code makes the same choices. It is read by every `/implement-rfc` and checked rule by rule by every `/review-rfc`, so each rule costs attention in every later step.

## WHEN A QUESTION HAS NO ANSWER

If critical information is missing or unclear, ask specific questions before proceeding. If nobody can answer -- the user does not know, or the run is non-interactive -- decide, mark the decision **(assumption)** where you use it, and list every assumption under an `## Open Questions` heading in the file you write, so `/implement-rfc` can put them in front of the user before code depends on them. List only the assumptions you make; one an earlier artifact already lists is cited there, not copied, because six copies of the same list get read by nobody. An assumption may fill a gap; it may never weaken or contradict a requirement or goal in a higher artifact. When the only way forward contradicts one, that is not an assumption but a High conflict: record it under `## Open conflicts` in RFCS.md (in the file you write, if RFCS.md does not exist yet) and write no rule, criterion or code that depends on it until the user accepts it in writing. Recording it is not enough on its own; in one run, "never lose my tasks" was recorded as contradicted in six files and the code that loses tasks still passed four reviews. If a requirement looks wrong or impossible, record that as an open question for PRD.md instead of quietly building something smaller -- that is how "zero data loss" turns into "usually no data loss" three documents later with nobody having decided it.

## PRODUCT TYPE

Read the `## Product Type` section of PRD.md and apply only the checks that fit that type. Name only the skips you add to the PRD's list; the PRD already records its own, and repeating them in every file is noise. Read the **Size** there too and scale what you write to it, following this prompt's own notes on size; a section that does not apply at that size is left out, not filled in. If PRD.md has no such section, classify the product and its Size yourself (web app · mobile app · library/SDK · CLI · service/API · data pipeline · game; Small, Medium or Large), say that you did, and recommend running `/verify-prd` so the classification is recorded once for every later step.

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
   - A rule applies to every RFC. How one command or feature behaves is an acceptance criterion in FEATURES.md or an RFC, not a rule, and a test case ("a test adds two tasks and removes one") is not a rule either. Rules that restate behavior become a second copy of the spec that outranks the RFCs, and the RFCs then need exceptions to it
   - Never write a rule whose only source is an assumption. A guess written as a rule gets a permanent ID, outranks the RFCs, and is enforced by every review; leave it as an open question instead
   - Never write two rules that check the same thing
   - The categories above are prompts, not quotas. With no existing code and no mandated stack, a short RULES.md is correct: for a Small product, about ten rules; leave out a category that has nothing project-specific to say
   - `/review-rfc` checks every rule, so a platitude costs review time and teaches the reviewer to skim the rules
   - Do not restate priorities or phasing here: they live in FEATURES.md and RFCS.md, and a second copy drifts

5. RULE IDS:
   - Give every rule a permanent ID with a short category prefix, written as `- **SEC-3**: rule text` (ARCH-1, API-2, SEC-3, TEST-1, ...)
   - IDs are append-only, like feature IDs. If RULES.md already exists, keep every existing ID and its meaning, give new rules the next unused number in their category, and mark retired rules [REMOVED] instead of deleting or reusing them
   - RFCs, reviews and change requests cite rules by these IDs -- a rule without an ID cannot be cited, so it cannot be checked

6. AGENT CONFIGURATION:
   - If the project uses an AI coding agent, recommend in your reply (do not write the files unless asked) wiring RULES.md into its config so the rules stay in context: reference it from CLAUDE.md (Claude Code), AGENTS.md (Codex and others), or .cursor/rules/ (Cursor)

First, provide a brief overview of the project based on the PRD and features list. Then create the RULES.md content.

## SELF-CHECK BEFORE FINISHING

- Recount every summary table from the actual content. Never carry a count forward from earlier in your own output.
- Verify every internal cross-reference -- feature IDs, rule IDs, RFC numbers, section references -- points at what the surrounding text claims it does. A reference to a VALID but WRONG ID is the dangerous case: nothing looks malformed, so readers are quietly misled.
- Confirm no two tables in the document disagree with each other.
- If `trace-check.py` is available -- in a `scripts/` folder beside these instructions, or in the project's own `scripts/` folder -- run it on the project (`python3 <path>/trace-check.py .`) and fix every FAIL it reports. It checks mechanically what reading does unreliably: that IDs in definitions and RFC header lines resolve, that requirements and Must-have features are covered, RFC dependencies, and review records. It does not check IDs cited in RFC bodies or whether each criterion has a planned test -- check those yourself.
- State in your reply, not in the file you wrote, that you ran these checks and what they turned up: a self-check section in the artifact is read by every later command and helps none of them.
