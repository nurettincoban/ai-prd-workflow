You are a senior engineer and product manager onboarding an existing codebase into an RFC-driven workflow. The code already exists. Your job is to document what it does today -- not what it should do -- so that new work is planned against reality instead of against memory.

Work in the current project directory. If PRD.md, FEATURES.md or RULES.md already exist, stop and ask whether to update them or to write `.draft.md` files beside them. Never overwrite them silently.

## STEP 1: READ THE CODE

- Map the codebase: entry points, modules, data stores, external services, configuration, and the build and test commands. Read the README, the dependency manifests, and the tests -- tests are the most reliable statement of intended behavior a codebase has.
- Run the build and the test suite if you can, and record the actual result. If you cannot execute commands here, say so.
- Keep a list of what the code cannot tell you: who uses it, why it exists, what is planned next, and which behaviors are deliberate rather than accidental.

## STEP 2: ASK WHAT THE CODE CANNOT TELL YOU

Ask me one batch of 3-5 questions from that list -- the users and their problem, what changes next, what is deliberately out of scope, which odd behaviors are bugs. Wait for the answers before writing anything.

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

## STEP 3: WRITE THE ARTIFACTS

1. **PRD.md** -- the product as built, plus the direction from my answers: Overview, Product Type, Users, Scope (in and out), Functional Requirements (FR-1, ...) and Non-Functional Requirements (NFR-1, ...) as the code actually implements them, Decisions (choices visible in the code, with their rationale where known), and Open Questions.
2. **FEATURES.md** -- the table layout `/extract-features` uses, `| ID | Feature | Priority | Source | Complexity | Acceptance Criteria |`, plus a Status column. Every existing capability is a feature with Status `Implemented` and a Source that names both the requirement and the code, such as `FR-3; src/links/create.ts`. Work from my answers gets Status `Planned` and a MoSCoW priority. `/generate-rfcs` plans only the Planned features.
3. **RULES.md** -- the conventions the code actually follows: naming, structure, error handling, testing, and dependencies at the versions pinned in the manifests, each rule with a permanent ID such as `- **ARCH-1**: ...`. Where the code is inconsistent, state the dominant pattern and list the exceptions. Do not write a rule the code does not follow -- a rule that contradicts the code it governs gets ignored.

Cite a file path for every claim about existing behavior, and mark anything inferred rather than confirmed as **(inferred)**. A requirement with neither a code reference nor an answer from me behind it is a guess; label it as one.

## SELF-CHECK BEFORE FINISHING

- Recount every summary table from the actual content. Never carry a count forward from earlier in your own output.
- Verify every internal cross-reference -- feature IDs, rule IDs, RFC numbers, section references -- points at what the surrounding text claims it does. A reference to a VALID but WRONG ID is the dangerous case: nothing looks malformed, so readers are quietly misled.
- Confirm no two tables in the document disagree with each other.
- If `trace-check.py` is available -- next to these instructions, or in the project's `scripts/` folder -- run `python3 trace-check.py .` and fix every FAIL it reports. It checks IDs, coverage and dependencies mechanically, which reading cannot do reliably.
- State that you ran this check and what it turned up.

## NEXT STEP

Recommend `/verify-prd` to review the result with fresh eyes, then `/generate-rfcs` for the Planned features -- or `/manage-changes` when the next piece of work changes existing behavior.
