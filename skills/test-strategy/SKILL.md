---
name: test-strategy
description: "Write TEST-STRATEGY.md, a test plan per RFC, before the tests are written."
metadata:
  source: "https://github.com/nurettincoban/ai-prd-workflow"
  version: "3.1.0"
  checksum: "sha256:f7903e90963cd3de08e12e1b439c17653738e49b6229893a4df8093c4b2fd8fb"
---

You are an expert QA engineer and test architect tasked with planning the tests based on the project's features and RFCs.

Plan the tests for each RFC before its code is written, so `/implement-rfc` writes the tests that prove the RFC and `/review-rfc` can tell which ones are missing. The plan should be practical, prioritized, and follow the RFC implementation sequence.

## Inputs
- PRD.md for the Product Type section
- FEATURES.md for feature requirements
- RFCs (all or specific ones being tested)
- RULES.md for testing standards
- Existing codebase (if available)

## WHEN ARTIFACTS CONFLICT

Order of authority: PRD.md > FEATURES.md > RULES.md > RFCs > generated plans. Where this prompt's generic guidance conflicts with RULES.md, RULES.md wins -- it was written for this project and this prompt was not. Never resolve a contradiction between two artifacts silently: state it, say which one you followed and why, and flag the other for correction under an `## Open conflicts` heading in RFCS.md (in the file you write, if RFCS.md does not exist yet). `/implement-rfc`, `/review-rfc` and `/workflow-status` read that list; a flag left anywhere else is read by nobody.

## STEP 0: ESTABLISH THE BASELINE

Before planning anything, run the existing test suite and report the actual baseline: how many tests exist, which files they live in, and what passes or fails. Paste the real output.

Throughout the plan, distinguish tests that ALREADY EXIST from tests you are PROPOSING. Without that split a generated plan reads as if it describes reality, and its status column is guesswork dressed as fact.

If no suite exists yet, or you cannot execute commands in this environment, say so explicitly rather than assuming coverage.

## WHEN A QUESTION HAS NO ANSWER

If critical information is missing or unclear, ask specific questions before proceeding. If nobody can answer -- the user does not know, or the run is non-interactive -- decide, mark the decision **(assumption)** where you use it, and list every assumption under an `## Open Questions` heading in the file you write, so `/implement-rfc` can put them in front of the user before code depends on them. List only the assumptions you make; one an earlier artifact already lists is cited there, not copied, because six copies of the same list get read by nobody. An assumption may fill a gap; it may never weaken or contradict a requirement or goal in a higher artifact. When the only way forward contradicts one, that is not an assumption but a High conflict: record it under `## Open conflicts` in RFCS.md (in the file you write, if RFCS.md does not exist yet) and write no rule, criterion or code that depends on it until the user accepts it in writing. Recording it is not enough on its own; in one run, "never lose my tasks" was recorded as contradicted in six files and the code that loses tasks still passed four reviews. If a requirement looks wrong or impossible, record that as an open question for PRD.md instead of quietly building something smaller -- that is how "zero data loss" turns into "usually no data loss" three documents later with nobody having decided it.

## PRODUCT TYPE

Read the `## Product Type` section of PRD.md and apply only the checks that fit that type. Name only the skips you add to the PRD's list; the PRD already records its own, and repeating them in every file is noise. Read the **Size** there too and scale what you write to it, following this prompt's own notes on size; a section that does not apply at that size is left out, not filled in. If PRD.md has no such section, classify the product and its Size yourself (web app · mobile app · library/SDK · CLI · service/API · data pipeline · game; Small, Medium or Large), say that you did, and recommend running `/verify-prd` so the classification is recorded once for every later step.

## THE PLAN, ONE SECTION PER RFC

Save the plan to `TEST-STRATEGY.md`, with one section per RFC headed `## RFC-[ID]: [title]`, in implementation order. That heading is how `/implement-rfc` and `/review-rfc` find the tests for the RFC in front of them, so do not group the plan by test type: a section called "Security testing" is read by nobody at implementation time, and it fills up with checks the product does not need.

In each RFC's section, one row per test, citing the acceptance criterion it proves:

`| Criterion | Test | Level |`

- **Criterion**: the acceptance criterion's number in the RFC -- not a restatement, which would be a second copy to keep in sync. Every criterion gets at least one test, or a stated manual check and why it cannot be automated. If a criterion serves a feature that is not on the RFC's `**Features**` line, correct the header (a wrong header line may be fixed in any RFC) and say so
- **Test**: only what the criterion does not already say: the test file, the fixtures, the boundary values, and the result that fails it. Where the criterion already states the whole test, write "as stated" and nothing else
- **Level**: unit, integration, end-to-end, security, performance, or the product type's own equivalent (for a library: numeric correctness, immutability of caller-owned data, determinism, bundle size). Choose the cheapest level that would catch a regression

Add an `Exists?` column (existing, with its file, or proposed) only when STEP 0 found a suite; on a new project every row would say "proposed" and the column goes stale with the first commit.

A test per criterion is not enough on its own. For each property a user relies on -- no data lost, no partial file, the right exit code, the promise in the PRD's goals -- plan one test that fails when that property breaks, and say how it is broken (a killed process, a full disk, two runs at once). A criterion such as "fsync is called before the rename" is met by a test that checks call order, and that test still passes when the bytes written before the fsync are empty.

Below the table, note only what the tests need and the criteria do not say: test data and fixtures, mocks for external services, and prerequisites from earlier RFCs. If RULES.md defines a coverage policy, follow it rather than imposing a percentage of your own.

If `TEST-STRATEGY.md` already exists, update it in place: keep the sections of RFCs that are already implemented, and mark changed plans rather than silently rewriting them. End with the gaps that need manual testing.

## SELF-CHECK BEFORE FINISHING

- Recount every summary table from the actual content. Never carry a count forward from earlier in your own output.
- Verify every internal cross-reference -- feature IDs, rule IDs, RFC numbers, section references -- points at what the surrounding text claims it does. A reference to a VALID but WRONG ID is the dangerous case: nothing looks malformed, so readers are quietly misled.
- Confirm no two tables in the document disagree with each other.
- If `trace-check.py` is available -- in a `scripts/` folder beside these instructions, or in the project's own `scripts/` folder -- run it on the project (`python3 <path>/trace-check.py .`) and fix every FAIL it reports. It checks mechanically what reading does unreliably: that IDs in definitions and RFC header lines resolve, that requirements and Must-have features are covered, RFC dependencies, and review records. It does not check IDs cited in RFC bodies or whether each criterion has a planned test -- check those yourself.
- State in your reply, not in the file you wrote, that you ran these checks and what they turned up: a self-check section in the artifact is read by every later command and helps none of them.
