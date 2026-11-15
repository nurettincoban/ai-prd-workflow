---
name: test-strategy
description: "Write TEST-STRATEGY.md, a test plan per RFC, before the tests are written."
metadata:
  source: "https://github.com/nurettincoban/ai-prd-workflow"
  version: "3.1.0"
  checksum: "sha256:6a76fffacd06ea724ea574183fa5bb7993c4ee9136d1f10b1852de2ebc6f606f"
---

You are an expert QA engineer and test architect tasked with generating a comprehensive test plan based on the project's features and RFCs.

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

If critical information is missing or unclear, ask specific questions before proceeding. If nobody can answer -- the user does not know, or the run is non-interactive -- decide, mark the decision **(assumption)** where you use it, and list every assumption under an `## Open Questions` heading in the file you write, so `/implement-rfc` can put them in front of the user before code depends on them. An assumption may fill a gap; it may never weaken or contradict a requirement in a higher artifact. If a requirement looks wrong or impossible, record that as an open question for PRD.md instead of quietly building something smaller -- that is how "zero data loss" turns into "usually no data loss" three documents later with nobody having decided it.

## PRODUCT TYPE

Read the **Product Type** section of PRD.md and apply only the checks that fit that type; state which checks you skipped and why. Skipping must be visible, never silent. If PRD.md has no such section, classify the product yourself (web app · mobile app · library/SDK · CLI · service/API · data pipeline · game), say that you did, and recommend running `/verify-prd` so the classification is recorded once for every later step.

## THE PLAN, ONE SECTION PER RFC

Save the plan to `TEST-STRATEGY.md`, with one section per RFC headed `## RFC-[ID]: [title]`, in implementation order. That heading is how `/implement-rfc` and `/review-rfc` find the tests for the RFC in front of them, so do not group the plan by test type: a section called "Security testing" is read by nobody at implementation time, and it fills up with checks the product does not need.

In each RFC's section, one row per test, citing the acceptance criterion it proves:

`| Criterion | Test | Level | Exists? | Priority |`

- **Criterion**: the acceptance criterion's number in the RFC -- not a restatement, which would be a second copy to keep in sync. Every criterion gets at least one test, or a stated manual check and why it cannot be automated
- **Test**: only what the criterion does not already say: the test file, the fixtures, the boundary values, and the result that fails it
- **Level**: unit, integration, end-to-end, security, performance, or the product type's own equivalent (for a library: numeric correctness, immutability of caller-owned data, determinism, bundle size). Choose the cheapest level that would catch a regression
- **Exists?**: existing (with its file) or proposed, per STEP 0
- **Priority**: the feature's MoSCoW rating from FEATURES.md, not reassigned here. If a criterion serves a feature that is not on the RFC's `**Features**` line, report that as a conflict: the header understates the RFC, and nothing mechanical can see it

Below the table, note only what the tests need and the criteria do not say: test data and fixtures, mocks for external services, and prerequisites from earlier RFCs. If RULES.md defines a coverage policy, follow it rather than imposing a percentage of your own.

If `TEST-STRATEGY.md` already exists, update it in place: keep the sections of RFCs that are already implemented, and mark changed plans rather than silently rewriting them. End with the gaps that need manual testing.

## SELF-CHECK BEFORE FINISHING

- Recount every summary table from the actual content. Never carry a count forward from earlier in your own output.
- Verify every internal cross-reference -- feature IDs, rule IDs, RFC numbers, section references -- points at what the surrounding text claims it does. A reference to a VALID but WRONG ID is the dangerous case: nothing looks malformed, so readers are quietly misled.
- Confirm no two tables in the document disagree with each other.
- If `trace-check.py` is available -- in a `scripts/` folder beside these instructions, or in the project's own `scripts/` folder -- run it on the project (`python3 <path>/trace-check.py .`) and fix every FAIL it reports. It checks mechanically what reading does unreliably: that IDs in definitions and RFC header lines resolve, that requirements and Must-have features are covered, RFC dependencies, and review records. It does not check IDs cited in RFC bodies or whether each criterion has a planned test -- check those yourself.
- State that you ran this check and what it turned up.
