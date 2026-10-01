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
