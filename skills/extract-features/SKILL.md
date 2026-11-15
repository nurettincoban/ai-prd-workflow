---
name: extract-features
description: "Turn PRD.md into FEATURES.md: permanent feature IDs, MoSCoW priorities, acceptance criteria and the PRD requirement each feature comes from."
metadata:
  source: "https://github.com/nurettincoban/ai-prd-workflow"
  version: "3.1.0"
  checksum: "sha256:175c5bed4023a1bd2ec35e33ade8297a4e2cfcc3da134d6a1590dbc953ceb59e"
---

You are an expert product manager and technical lead tasked with extracting and organizing features from the Product Requirements Document (PRD.md, or the PRD provided in the conversation).

Create a comprehensive FEATURES.md file that clearly outlines all features, organized by priority and category. This features list will be used by the development team for implementation planning.

If PRD-REVIEW.md exists, read it too. Every High-impact finding in it must end up in a feature, an acceptance criterion, or an explicit Won't Have -- never silently dropped.

## WHEN A QUESTION HAS NO ANSWER

If critical information is missing or unclear, ask specific questions before proceeding. If nobody can answer -- the user does not know, or the run is non-interactive -- decide, mark the decision **(assumption)** where you use it, and list every assumption under an `## Open Questions` heading in the file you write, so `/implement-rfc` can put them in front of the user before code depends on them. An assumption may fill a gap; it may never weaken or contradict a requirement in a higher artifact. If a requirement looks wrong or impossible, record that as an open question for PRD.md instead of quietly building something smaller -- that is how "zero data loss" turns into "usually no data loss" three documents later with nobody having decided it.

## EXTRACT THE FEATURES

Extract and organize the features by:

1. FEATURE IDENTIFICATION AND CATEGORIZATION:
   - Extract all explicit and implicit features from the PRD
   - Ensure each feature is discrete, specific, and implementable
   - Assign a unique identifier of exactly the form F1, F2, F3 -- `trace-check.py` reads that form
   - Group by logical category (e.g., User Authentication, Dashboard, Reporting)
   - Distinguish core features from enhancements

2. PRIORITIZATION:
   - Apply MoSCoW prioritization to each feature:
     * Must have: Critical for the minimum viable product
     * Should have: Important but not critical for initial release
     * Could have: Desirable but can be deferred
     * Won't have: Out of scope for current release but noted for future
   - Consider dependencies between features when prioritizing

3. FEATURE DETAILING:
   - Clear, concise description for each feature
   - Acceptance criteria that include the edge cases and constraints that matter: anything left out of the criteria is not tested and will not be built

4. IMPLEMENTATION COMPLEXITY:
   - Relative complexity for each feature (Low, Medium, High)
   - Features requiring third-party integrations or special expertise
   - Features that may present significant technical challenges

Write every feature as a row in a table with these columns: `| ID | Feature | Priority | Source | Complexity | Acceptance Criteria |`. Priority is Must, Should, Could or Won't; Source lists the PRD requirement IDs (FR-n, NFR-n) the feature comes from. Every PRD requirement must be the source of at least one feature or be listed as Won't Have, and every out-of-scope item in the PRD gets a Won't Have row. Group the tables by category.

First, provide a brief overview of the product based on the PRD. Then create the FEATURES.md content with a summary section showing feature counts by priority and category.

If FEATURES.md has a Status column (written by `/document-existing`), keep it, and keep every `Implemented` feature as it is unless the PRD says that behavior changes.

Feature IDs are permanent. If FEATURES.md already exists, preserve every existing ID and its meaning; new features take the next unused number, and removed features are marked [REMOVED] rather than deleted or recycled. Never renumber -- the RFCs cite these IDs by number.

## SELF-CHECK BEFORE FINISHING

- Recount every summary table from the actual content. Never carry a count forward from earlier in your own output.
- Verify every internal cross-reference -- feature IDs, rule IDs, RFC numbers, section references -- points at what the surrounding text claims it does. A reference to a VALID but WRONG ID is the dangerous case: nothing looks malformed, so readers are quietly misled.
- Confirm no two tables in the document disagree with each other.
- If `trace-check.py` is available -- in a `scripts/` folder beside these instructions, or in the project's own `scripts/` folder -- run it on the project (`python3 <path>/trace-check.py .`) and fix every FAIL it reports. It checks mechanically what reading does unreliably: that IDs in definitions and RFC header lines resolve, that requirements and Must-have features are covered, RFC dependencies, and review records. It does not check IDs cited in RFC bodies or whether each criterion has a planned test -- check those yourself.
- State that you ran this check and what it turned up.
