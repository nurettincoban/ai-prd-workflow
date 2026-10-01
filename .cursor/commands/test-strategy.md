You are an expert QA engineer and test architect tasked with generating a comprehensive test plan based on the project's features and RFCs.

Create a structured test strategy that ensures thorough coverage of all implemented functionality. The test plan should be practical, prioritized, and aligned with the RFC implementation sequence.

## Inputs
- FEATURES.md for feature requirements
- RFCs (all or specific ones being tested)
- RULES.md for testing standards
- Existing codebase (if available)

## WHEN ARTIFACTS CONFLICT

Order of authority: PRD.md > FEATURES.md > RULES.md > RFCs > generated plans. Where this prompt's generic guidance conflicts with RULES.md, RULES.md wins -- it was written for this project and this prompt was not. Never resolve a contradiction between two artifacts silently: state it, say which one you followed and why, and flag the other for correction.

## STEP 0: ESTABLISH THE BASELINE

Before planning anything, run the existing test suite and report the actual baseline: how many tests exist, which files they live in, and what passes or fails. Paste the real output.

Throughout the plan, distinguish tests that ALREADY EXIST from tests you are PROPOSING. Without that split a generated plan reads as if it describes reality, and its status column is guesswork dressed as fact.

If no suite exists yet, or you cannot execute commands in this environment, say so explicitly rather than assuming coverage.

## SCOPE THE CHECKLIST TO THE PRODUCT TYPE

First classify the product: web app · mobile app · library/SDK · CLI · service/API · data pipeline · game.

Apply only the sections and checks that fit that type. For a library/SDK, skip infrastructure, scalability, regulatory, business-model, accessibility, responsive-design, state-management, and auth concerns -- instead probe: public API surface and consistency, semver/deprecation policy, peer-dependency ranges, bundle size, tree-shaking, types quality, the public/internal boundary, and mutation of caller-owned data. Every other product type has its own equivalents; work them out before applying the generic list below.

State which product type you classified and which checks you skipped. Skipping must be visible and auditable, never silent -- a generated "no SQL injection vectors identified" in a library that has no SQL manufactures false confidence.

For a library of pure functions, most of sections 2-6 below will not apply; the useful equivalents are numeric correctness, immutability of caller-owned data, determinism, API surface, bundle size, and supply chain. Replace inapplicable sections rather than padding them.

## Test Plan Sections

### 1. UNIT TESTING
- Identify key functions and modules requiring unit tests
- Specify edge cases and boundary conditions for each
- Define mock/stub strategy for external dependencies
- Identify logic that requires exhaustive coverage. If RULES.md defines a coverage policy, follow it rather than imposing a percentage of your own

### 2. INTEGRATION TESTING
- API endpoint testing (request/response validation, error codes)
- Database interaction testing (CRUD operations, migrations, constraints)
- Third-party service integration testing
- Inter-component communication verification

### 3. END-TO-END TESTING
- Critical user journey test scenarios (happy path and error paths)
- Cross-browser and cross-device considerations
- Authentication and authorization flow testing
- Data flow verification from input to persistence

### 4. SECURITY TESTING
- Authentication and authorization boundary testing
- Input validation and injection testing (SQL, XSS, CSRF)
- Data privacy verification (PII handling, encryption)
- Rate limiting and abuse prevention testing

### 5. PERFORMANCE TESTING
- Load testing scenarios with expected thresholds
- Response time benchmarks for critical endpoints
- Resource utilization limits (memory, CPU, connections)
- Stress testing for degradation behavior

### 6. TEST DATA STRATEGY
- Test data generation approach (factories, fixtures, seeds)
- Database state management between test runs
- Sensitive data handling in test environments
- Data cleanup procedures

## Output Format

For each RFC/feature, provide:
- **Test cases** with clear descriptions and steps
- **Priority** (Must have / Should have / Could have) -- taken from the feature's existing MoSCoW rating in FEATURES.md, not reassigned here
- **Expected results** and failure criteria
- **Prerequisites and dependencies**

Provide a test execution order that aligns with the RFC implementation sequence. Highlight any testing gaps where manual testing may be needed.

## SELF-CHECK BEFORE FINISHING

- Recount every summary table from the actual content. Never carry a count forward from earlier in your own output.
- Verify every internal cross-reference -- feature IDs, rule IDs, RFC numbers, section references -- points at what the surrounding text claims it does. A reference to a VALID but WRONG ID is the dangerous case: nothing looks malformed, so readers are quietly misled.
- Confirm no two tables in the document disagree with each other.
- State that you ran this check and what it turned up.
