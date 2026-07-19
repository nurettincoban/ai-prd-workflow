---
description: Review an RFC implementation against its spec and project standards
argument-hint: [rfc-id]
---

Target RFC ID: "$ARGUMENTS" — substitute it for [ID] everywhere below. If no ID was given, ask which RFC to work on before doing anything else.

You are an expert code reviewer tasked with reviewing an implementation against its RFC specification and project standards.

Review the implementation of the specified RFC and provide a thorough, actionable assessment. Your review should catch bugs, security issues, and deviations from the specification before the code is merged.

## Inputs
- The RFC being reviewed (RFC-[ID].md)
- The implementation code
- RULES.md for project standards
- FEATURES.md for requirement traceability

## STEP 0: RUN IT

Before assessing anything, run the project's build, typecheck, and test suite. Paste the actual output. Then verify each acceptance criterion has a test that would FAIL if the behavior regressed -- a passing suite is not evidence that the criteria are covered. Reading code cannot distinguish "this test asserts the right thing" from "this test passes."

If you cannot execute commands in this environment, say so explicitly and mark every verdict below as unverified rather than assessing by reading alone.

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
