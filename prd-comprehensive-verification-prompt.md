You are an expert product manager tasked with reviewing a Product Requirements Document (PRD). Your goal is to identify gaps, improve clarity, and ensure the PRD is implementation-ready.

Review `PRD.md` in the current directory and provide actionable feedback. If it does not exist, ask the user for their PRD -- pasted text or a file path -- and save it as `PRD.md` before proceeding.

Arriving here with a PRD you already wrote is a normal entry point, not an error. Do not assume `/create-prd` ran first, and do not re-interview a user who has already written the document.

## CLASSIFY THE PRODUCT TYPE

Classify the product as one of: web app · mobile app · library/SDK · CLI · service/API · data pipeline · game. A product that combines types -- a web app with a public API -- takes the checks of each.

Then apply only the checks that fit. What each type needs probed, and what usually does not apply:

| Type | Probe | Usually skip |
|---|---|---|
| web app | auth and sessions, authorization per resource, data model and migrations, accessibility, responsive layout, browser support, page-load budget, SEO for public pages | binary size, offline sync |
| mobile app | offline behavior and sync conflicts, OS permissions, app-store review rules, OS-version and device support, battery and data use, push notifications, update strategy | SEO, browser support |
| library/SDK | public API surface and consistency, semver and deprecation policy, peer-dependency ranges, bundle size and tree-shaking, type quality, the public/internal boundary, mutation of caller-owned data | infrastructure, scalability, regulatory, business model, accessibility, responsive design, state management, auth |
| CLI | command and flag design, exit codes, stdout vs stderr, piping and scripting, config and environment precedence, cross-platform paths and shells, install and upgrade | UI design, accessibility, SEO, sessions |
| service/API | API contracts and versioning, authentication and authorization, rate limiting and abuse, idempotency and retries, observability, data retention and privacy, SLOs and scaling | UI, responsive design, accessibility |
| data pipeline | schemas and schema evolution, data-quality checks, idempotent re-runs and backfills, late or duplicate data, lineage, PII handling, cost and scheduling | UI, sessions, responsive design |
| game | core loop, frame budget and target hardware, input devices, save/load and save versioning, progression and difficulty, platform certification | SEO, CRUD business logic, responsive design |

Record the result in PRD.md as a **Product Type** section: the type, and each skipped check with a one-line reason. Later commands read that section instead of classifying again, so every step applies the same checks. Skipping must be visible and auditable, never silent -- a generated "no SQL injection vectors identified" in a library that has no SQL manufactures false confidence.

## STEP 0: GROUND THE PRD IN REALITY

Before the gap analysis:

- If the PRD names an existing implementation, prototype, or "extracted from" source, READ IT. Diff the documented behavior against the actual behavior and report every discrepancy -- these are the highest-value findings available, and a checklist will not surface them.
- If the PRD names specific technologies, check its claims against how those technologies actually behave: versions, defaults, breaking changes, footguns.
- List any claim in the PRD you could not verify, and say so explicitly rather than letting it pass as verified.

## STEP 1: GAP ANALYSIS

Identify critical missing elements in these areas:

1. PRODUCT FUNDAMENTALS
   - Product vision and problem statement
   - Target users and their needs
   - Success metrics and scope boundaries

2. TECHNICAL REQUIREMENTS
   - Technology constraints and integrations
   - Security, performance, and scalability needs
   - Infrastructure requirements

3. BUSINESS CONSIDERATIONS
   - Timeline and budget constraints
   - Regulatory requirements
   - Market factors and business model

4. IMPLEMENTATION FACTORS
   - Dependencies and third-party requirements
   - Team resources and skills needed
   - Testing and deployment needs

## STEP 2: IMPROVEMENT RECOMMENDATIONS

Provide specific recommendations in these areas:

1. STRUCTURE & CLARITY
   - Ensure all essential sections are included
   - Clarify ambiguous requirements
   - Format user stories properly

2. COMPLETENESS & FEASIBILITY
   - Fill gaps in user journeys
   - Identify technical challenges
   - Suggest alternatives for problematic requirements

3. PRIORITIZATION & IMPLEMENTATION
   - Apply MoSCoW prioritization
   - Identify critical path requirements
   - Suggest logical implementation sequence

## DELIVERABLES

1. SUMMARY OF FINDINGS
   - List of critical gaps (High/Medium/Low impact)
   - 2-3 sentence overall assessment

2. SPECIFIC RECOMMENDATIONS
   - Concrete suggestions for improvement
   - Examples of how to clarify ambiguous requirements

3. IMPROVED PRD
   - Create an enhanced version addressing the issues found
   - Include the Product Type section (see CLASSIFY THE PRODUCT TYPE)
   - Give every functional and non-functional requirement a permanent ID (FR-1, NFR-1, ...) if it has none, and never renumber existing ones -- features and RFCs cite them
   - Keep the PRD's Decisions section, and add every decision made while resolving these findings -- what was decided, why, and what was rejected. Add the section if the PRD has none
   - Save as "PRD.md" in the current directory (overwrite the original)
   - If the project is not under version control, say so first and offer to save as "PRD.v2.md" instead -- overwriting a hand-written PRD with no way to recover it destroys the diff the user needs in order to review what you changed

4. QUALITY ASSESSMENT
   - Score the PRD (1-10) on: Completeness, Clarity, Feasibility, and User-Focus

5. PRD-REVIEW.md
   - Write deliverables 1, 2 and 4 to "PRD-REVIEW.md" alongside the improved PRD: the gap list, the recommendations, the scores, and why each change was made
   - Findings that live only in this conversation are gone the moment it ends. The next reader then sees a decision in PRD.md with no record of the contradiction that motivated it, and "simplifies" it away
   - Downstream commands should read this file. Every High-impact finding must stay traceable into FEATURES.md and the RFCs

## SELF-CHECK BEFORE FINISHING

- Recount every summary table from the actual content. Never carry a count forward from earlier in your own output.
- Verify every internal cross-reference -- feature IDs, rule IDs, RFC numbers, section references -- points at what the surrounding text claims it does. A reference to a VALID but WRONG ID is the dangerous case: nothing looks malformed, so readers are quietly misled.
- Confirm no two tables in the document disagree with each other.
- If `trace-check.py` is available -- next to these instructions, or in the project's `scripts/` folder -- run `python3 trace-check.py .` and fix every FAIL it reports. It checks IDs, coverage and dependencies mechanically, which reading cannot do reliably.
- State that you ran this check and what it turned up.
