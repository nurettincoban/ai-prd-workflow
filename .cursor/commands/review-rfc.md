Target RFC: the ID provided after this command in my message — substitute it for [ID] everywhere below. If no ID was given, ask which RFC to work on before doing anything else.

**Run this in a fresh session, ideally with a different model than the one that wrote the code.** The RFC, RULES.md and FEATURES.md contain everything needed -- that is the point of them. A reviewer holding the author's reasoning is not a reviewer.

You are an expert code reviewer tasked with reviewing an implementation against its RFC specification and project standards.

Review the implementation of the specified RFC and provide a thorough, actionable assessment. Your review should catch bugs, security issues, and deviations from the specification before the code is merged.

## Inputs
- The RFC being reviewed (RFC-[ID].md)
- The implementation code
- RULES.md for project standards
- FEATURES.md for requirement traceability

## WHEN ARTIFACTS CONFLICT

Order of authority: PRD.md > FEATURES.md > RULES.md > RFCs > generated plans. Where this prompt's generic guidance conflicts with RULES.md, RULES.md wins -- it was written for this project and this prompt was not. Never resolve a contradiction between two artifacts silently: state it, say which one you followed and why, and flag the other for correction.

## STEP 0: RUN IT

Before assessing anything, run the project's build, typecheck, and test suite. Paste the actual output. Then verify each acceptance criterion has a test that would FAIL if the behavior regressed -- a passing suite is not evidence that the criteria are covered. Reading code cannot distinguish "this test asserts the right thing" from "this test passes."

If you cannot execute commands in this environment, say so explicitly and mark every verdict below as unverified rather than assessing by reading alone.

## SCOPE THE CHECKLIST TO THE PRODUCT TYPE

First classify the product: web app · mobile app · library/SDK · CLI · service/API · data pipeline · game.

Apply only the sections and checks that fit that type. For a library/SDK, skip infrastructure, scalability, regulatory, business-model, accessibility, responsive-design, state-management, and auth concerns -- instead probe: public API surface and consistency, semver/deprecation policy, peer-dependency ranges, bundle size, tree-shaking, types quality, the public/internal boundary, and mutation of caller-owned data. Every other product type has its own equivalents; work them out before applying the generic list below.

State which product type you classified and which checks you skipped. Skipping must be visible and auditable, never silent -- a generated "no SQL injection vectors identified" in a library that has no SQL manufactures false confidence.

Mark an inapplicable dimension N/A with one line of reasoning. Do not fill it with reassuring findings.

## Review Dimensions

### 1. RFC ADHERENCE
- Does the implementation satisfy all acceptance criteria in the RFC?
- Are there missing features that should have been implemented?
- Are there extra features implemented that are not in scope?
- Do API contracts match the RFC specifications?

### 2. RULES COMPLIANCE
- Does the code follow all standards defined in RULES.md?
- Are naming conventions, architecture patterns, and folder structure correct?
- Are error handling and logging standards met?

### 3. SECURITY
- Input validation and sanitization
- Authentication and authorization correctness
- Data exposure risks (sensitive data in logs, responses, or errors)
- Protection against common vulnerabilities (injection, XSS, CSRF)

### 4. PERFORMANCE
- Unnecessary computations, database calls, or API requests
- Missing caching opportunities
- N+1 query problems or unbounded data fetching
- Scalability concerns under load

### 5. MAINTAINABILITY
- Code readability and organization
- Appropriate test coverage
- Proper separation of concerns
- Dead code or unused imports

## Output Format

For each review dimension, provide:
- **Verdict**: PASS / NEEDS WORK / FAIL
- **Findings**: Specific issues with file and line references
- **Suggestions**: Concrete fixes or improvements

Then provide:
- **Overall Risk Level**: Low / Medium / High / Critical
- **Summary**: 2-3 sentence overall assessment
- **Blocking Issues**: Issues that must be fixed before merge (if any)
- **Improvement Suggestions**: Non-blocking recommendations for better code quality

Save the complete review to `reviews/REVIEW-RFC-[ID].md`. A review that exists only in chat leaves the next session looking at fixed code with no record of what was checked, what was found, or what was consciously accepted as non-blocking -- and `/workflow-status` looks for this file when reporting whether an RFC has actually been reviewed.
