# RULES: LinkSnip URL Shortener

Source: `PRD.md` (FR-1 to FR-19, NFR-1 to NFR-9, D1-D6, OQ-1 to OQ-15), `PRD-REVIEW.md` (H1-H5, M1-M9, L1-L10, R1-R11) and `FEATURES.md` (F1-F44).

This file was written non-interactively: no person was available to answer questions. Where a rule rests on one of the PRD's open questions, it follows the assumption PRD.md records and cites the OQ. Where this file makes a choice of its own -- most importantly the whole technology stack, which no document names -- it is marked **(assumption)** and listed in the Assumptions section at the end. Any of them can be overturned by an RFC that retires the rule (see Rule IDs).

## Project Overview

LinkSnip is a self-hostable web app plus public REST API that shortens URLs (generated 7-character base62 codes or custom aliases, optional expiry) and records click analytics (totals, timeline, referrers, countries). v1.0 has no accounts: delete is protected by a per-link management token and listing by an operator admin token (OQ-1). The hard constraints that shape these rules are the redirect path -- HTTP 302 with no-store (D1), a durable click write per redirect (NFR-9, OQ-7), p95 under 100ms at 1,000 redirects per second (NFR-1, NFR-3) over 10M stored URLs (NFR-6) -- and the privacy stance that client IPs are never stored (OQ-4). It ships as one `docker compose up` (NFR-7, D2).

## Product Type

PRD.md records **Web app + service/API**. Checks applied here: authorization per resource (SEC), data model and migrations (DATA), accessibility, responsive layout and browser support (UI, TEST), page-load budget (PERF), API contracts and versioning (API), authentication and rate limiting (SEC), idempotency and retries (API, PERF), observability (LOG), data retention and privacy (PRIV), SLOs and scaling (PERF, TEST).

Skipped, visibly:
- **Binary size** -- a self-hosted web service ships no client binary (PRD Product Type).
- **Offline sync** -- every operation needs the server (PRD Product Type).
- **Sessions and login security** -- v1.0 has no accounts (PRD Out of Scope, F36); token handling is covered by SEC instead.
- **SEO for public pages** -- no rule: the only SEO item is keeping analytics pages out of indexes, which is a Should feature (F29), and a rule would silently promote it to Must. Rules do not restate priorities.
- **Mobile, library/SDK, CLI, data pipeline and game checks** -- not this product type.

## Grounding

There is no existing code, prototype or reference implementation: the project directory holds only PRD.md, PRD-REVIEW.md and FEATURES.md, and the PRD names none. Naming and structure rules below are therefore chosen, not derived **(assumption)**. Once code exists, a rule that contradicts it should be retired or the code changed in the same RFC -- not left to disagree.

## Technology Stack

No document names a language, framework or datastore (PRD-REVIEW L8 leaves the datastore to the RFCs; R8 suggests PostgreSQL). The stack below is **(assumption)**, chosen for: a single-process server that can hold a 100ms p95 redirect budget, first-party plugins for rate limiting and OpenAPI (FR-16, FR-17), server-rendered HTML for the page-load budget (OQ-13), and PostgreSQL for 10M URLs plus a partitioned click table (R8).

Every version was checked against its registry on 2026-11-15 (`npm view <pkg> version`, nodejs.org `dist/index.json`, Docker Hub tags API). None is from memory.

| Component | Choice | Version | Verified against |
|---|---|---|---|
| Runtime | Node.js (Active LTS "Lithium") | 26.13.1 | nodejs.org dist index |
| Runtime image | `node` Docker image | `26.13.1-alpine` | Docker Hub tags |
| Language | TypeScript | 7.0.2 | npm |
| Datastore | PostgreSQL Docker image | `18.7-alpine` | Docker Hub tags |
| HTTP framework | fastify | 5.12.8 | npm |
| Schemas / validation | @sinclair/typebox | 0.34.52 | npm |
| Schema type provider | @fastify/type-provider-typebox | 6.3.0 | npm |
| Rate limiting | @fastify/rate-limit | 11.2.2 | npm |
| OpenAPI generation | @fastify/swagger | 9.9.4 | npm |
| Swagger UI | @fastify/swagger-ui | 6.1.4 | npm |
| Security headers | @fastify/helmet | 13.2.0 | npm |
| HTML form bodies | @fastify/formbody | 9.0.2 | npm |
| Static files | @fastify/static | 10.1.11 | npm |
| Template plugin | @fastify/view | 12.0.1 | npm |
| Template engine | eta | 4.6.0 | npm |
| PostgreSQL client | pg | 8.23.1 | npm |
| PostgreSQL types | @types/pg | 8.23.1 | npm |
| Migrations | node-pg-migrate | 9.0.0 | npm |
| GeoLite2 reader | maxmind | 5.1.0 | npm |
| Bot detection (F15) | isbot | 5.2.3 | npm |
| Chart (analytics page) | chart.js | 4.6.1 | npm |
| Unit / integration tests | vitest | 5.1.0 | npm |
| Coverage | @vitest/coverage-v8 | 5.1.0 | npm |
| Real-database tests | @testcontainers/postgresql | 12.2.1 | npm |
| Property tests | fast-check | 4.10.2 | npm |
| Browser tests | @playwright/test | 1.65.1 | npm |
| Accessibility scan | @axe-core/playwright | 4.14.0 | npm |
| Load tests | k6 (`grafana/k6` image) | 2.4.0 | Docker Hub tags |
| Dev runner | tsx | 4.23.15 | npm |
| Node types | @types/node | 26.6.6 | npm |
| Lint | eslint | 10.15.0 | npm |
| Lint (TypeScript) | typescript-eslint | 8.72.2 | npm |
| Format | prettier | 3.10.1 | npm |

Not verified: that these versions are mutually compatible (plugin-to-fastify and typescript-eslint-to-TypeScript 7 peer ranges were not checked). The first RFC confirms it with `npm ci && npm test`; if a pair is incompatible, pick the newest compatible version from the registry and update this table -- never a remembered number. Logging uses the pino logger bundled with fastify, so pino is not a separate dependency.

## Rules

Each rule has a permanent ID. Cite rules by ID in RFCs, reviews and change requests.

### STACK -- stack and dependencies

- **STACK-1**: `package.json` sets `"engines": { "node": ">=26.13.1 <27" }`, and the app `Dockerfile` builds from `node:26.13.1-alpine`. The runtime under test and in production is the same major version.
- **STACK-2**: All source under `src/`, `test/` and `migrations/` is TypeScript; `tsconfig.json` has `"strict": true`; no `.js` source files are committed there.
- **STACK-3**: Every dependency in `package.json` is pinned to an exact version (no `^`, `~`, `*` or `latest`) and `package-lock.json` is committed; the Dockerfile installs with `npm ci`. Why: a floating version makes the 5-minute first deployment (NFR-7) depend on whatever the registry served that day.
- **STACK-4**: A dependency not in the Technology Stack table is added only by an RFC that names it, gives its registry-verified version, and adds it to the table in the same change.
- **STACK-5**: The only datastore is PostgreSQL (`postgres:18.7-alpine` in `compose.yaml`). No Redis, SQLite or other store in v1.0: rate limits are per instance (F8) and need no shared store, and a second service makes `docker compose up` slower and more fragile.
- **STACK-6**: ESLint with `typescript-eslint`'s `strict` config and Prettier run in CI and fail the build on any error; `@typescript-eslint/no-explicit-any` is an error, and `// eslint-disable` comments carry a reason on the same line.

### ARCH -- architecture and code organization

- **ARCH-1**: Source layout is: `src/routes/api/` (JSON API handlers), `src/routes/web/` (HTML page handlers), `src/routes/redirect.ts` (the redirect), `src/services/` (business logic), `src/db/` (all SQL), `src/integrations/` (Safe Browsing, GeoLite2), `src/views/` (Eta templates), `src/config.ts` (configuration), `static/` (CSS, client JS), `migrations/`, `test/unit/`, `test/integration/`, `test/e2e/`, `load/`.
- **ARCH-2**: Only files under `src/db/` import `pg` or contain SQL. Route handlers and services call `src/db/` functions.
- **ARCH-3**: Files under `src/services/` do not import `fastify` and do not receive `request` or `reply`; they take typed plain arguments and return typed results or throw `ApiError` (ERR-1).
- **ARCH-4**: Web UI handlers and API handlers call the same service functions; no validation or business rule exists only in a `src/routes/web/` file. Why: FR-14 says the API does everything the UI does, and a rule implemented twice drifts.
- **ARCH-5**: The blocklist check is an interface `UrlChecker` with `check(url: string): Promise<"clean" | "listed" | "unchecked">` in `src/integrations/blocklist/`. Services depend on the interface only; Safe Browsing is one implementation, and a no-op checker returning `"unchecked"` is used when no key is configured (F7, OQ-2).
- **ARCH-6**: `process.env` is read only in `src/config.ts`, which validates all settings against a TypeBox schema at startup. A missing required setting or an invalid value exits the process with a non-zero code and a message naming the variable; an optional setting that is absent takes the default documented in the README (F30).
- **ARCH-7**: Pages are rendered on the server with Eta; there is no client-side framework or bundler. Client JavaScript lives only in `static/js/` and only enhances a page that already works (UI-4). Why: the create page must be interactive in under 2 seconds on a mid-range phone (OQ-13, F27).
- **ARCH-8**: Every top-level path segment the app routes (`api`, `docs`, `static`, `health`, and any page path) is listed in one exported constant `RESERVED_ALIASES`, and a test enumerates the registered routes and fails if a top-level segment is missing from it. Why: an alias equal to a route would shadow it (D3, F2).
- **ARCH-9**: Code that needs the current time takes a `Clock` (`{ now(): Date }`) argument; `Date.now()` and argument-less `new Date()` appear only in `src/clock.ts`. Why: expiry (F3, F11), timelines (F17) and retention (F14) must be testable without sleeping.

### NAME -- naming

- **NAME-1**: File and folder names are kebab-case (`short-url-service.ts`); test files end in `.test.ts`, Playwright files in `.spec.ts`.
- **NAME-2**: Types, interfaces and classes are PascalCase; functions and variables camelCase; module-level constants UPPER_SNAKE_CASE.
- **NAME-3**: Database tables and columns are snake_case; tables are plural nouns (`short_urls`, `clicks`, `click_daily`); timestamp columns end in `_at` (date-only columns are named `day`).
- **NAME-4**: JSON field names in API requests and responses are camelCase; error codes are UPPER_SNAKE_CASE (API-3).
- **NAME-5**: Every environment variable starts with `LINKSNIP_` (for example `LINKSNIP_PUBLIC_HOST`, `LINKSNIP_ADMIN_TOKEN`).

### DATA -- data model and storage

- **DATA-1**: Every schema change is a node-pg-migrate migration in `migrations/`. A migration that has been merged is never edited; changes go in a new migration. Migrations run before the server starts listening (F35).
- **DATA-2**: Every time column is `timestamptz`, and every timestamp the app writes or returns is UTC; the API returns ISO 8601 strings ending in `Z`. `timestamp without time zone` is not used (FR-3, OQ-12).
- **DATA-3**: Generated codes and aliases live in one column, `short_urls.code`, with a unique index and `COLLATE "C"`, so uniqueness is case-sensitive (D3, OQ-15). The unique index -- not a prior SELECT -- is the guarantee: a unique violation (SQLSTATE `23505`) on a generated code is retried with a new code, and on an alias returns 409 (F1, F2).
- **DATA-4**: A deleted short URL keeps its row with `deleted_at` set; `short_urls` rows are never hard-deleted and a code is never reissued (F4). Lookups that serve redirects or analytics treat `deleted_at IS NOT NULL` like a missing row.
- **DATA-5**: `clicks` is range-partitioned by month on `clicked_at`, and every query on `clicks` filters on `short_url_id` and a `clicked_at` range, so it touches only the partitions it needs (F31, R8).
- **DATA-6**: Raw-click retention removes whole monthly partitions (`DROP TABLE` / `DETACH PARTITION`), never row-by-row `DELETE`, so purges do not slow redirects (F14).
- **DATA-7**: A rollup job writes per-day aggregates to `click_daily` for every completed UTC day, and the retention job refuses to drop a partition containing a day that has not been rolled up. Analytics read `click_daily` for days outside the raw window, so totals stay correct after a purge (F14, F20).
- **DATA-8**: All SQL values are passed as parameters (`$1`, `$2`, ...). No SQL string is built by concatenation or template-literal interpolation of a value.
- **DATA-9**: The `clicks` table has no column that holds an IP address or a part of one (PRIV-1).

### API -- API contracts

- **API-1**: Every JSON endpoint is under `/api/v1/` (F21, R9).
- **API-2**: Every route declares TypeBox schemas for its params, querystring, body, and every response status it can return. The OpenAPI document (F23) is generated from these schemas by @fastify/swagger, never written by hand.
- **API-3**: Every 4xx and 5xx response from an API route has the body `{ "error": { "code": "<UPPER_SNAKE_CASE>", "message": "<human-readable>" } }`, produced by one Fastify error handler; every code is declared in `src/errors.ts` **(assumption: F22 leaves the exact fields to the API RFC; that RFC may retire this rule and replace it)**.
- **API-4**: Status codes are: 201 for a created link, 200 for reads, 204 for a successful delete, 400 for invalid input including a malformed or non-JSON body, 403 for a missing or wrong management or admin token, 404 for unknown, deleted or expired codes, 409 for a taken alias, 429 for rate limiting, 500 for unexpected errors. An error never returns 2xx.
- **API-5**: Tokens travel only in the `Authorization: Bearer <token>` header, never in a path, query string or form field that ends up in a URL. Why: URLs are written to access logs, browser history and `Referer` headers.
- **API-6**: The create response contains the field `blocklistStatus` (`"clean"` or `"unchecked"`), so an unchecked link is visible to the API client, not only in a log (F7).
- **API-7**: List endpoints use cursor (keyset) pagination with a `limit` parameter (default 50, maximum 100); no endpoint returns an unbounded list (F5, NFR-6).
- **API-8**: Within `/api/v1/`, no response field is removed or renamed, no field changes type, and no status code changes meaning; such a change requires a new version prefix. Adding optional fields is allowed.
- **API-9**: No GET or HEAD request under `/api/` writes to the database. The redirect route is the only GET that writes (one click row).

### SEC -- security

- **SEC-1**: Destination URLs are validated by one function in `src/services/validation.ts` using the WHATWG `URL` parser: the protocol is exactly `http:` or `https:`, the host is non-empty, the input is at most 2,048 characters, and the host (lower-cased, with any default port removed) does not equal `LINKSNIP_PUBLIC_HOST` (FR-19, D5, F6).
- **SEC-2**: Aliases match `^[0-9A-Za-z]{3,30}$` and are rejected if `alias.toLowerCase()` is in `RESERVED_ALIASES` (FR-2, F2, ARCH-8).
- **SEC-3**: Generated codes use `crypto.randomInt` over the 62-character alphabet; `Math.random` is not used anywhere in `src/`. Why: predictable codes let anyone enumerate links.
- **SEC-4**: A management token is 32 bytes from `crypto.randomBytes`, encoded base64url, returned only in the create response, and stored only as its SHA-256 hash. Token comparison (management and admin) uses `crypto.timingSafeEqual` on equal-length buffers (F4, OQ-1).
- **SEC-5**: The list endpoint compares against `LINKSNIP_ADMIN_TOKEN`; when the variable is unset or empty, the endpoint returns 403 for every request (F5).
- **SEC-6**: Eta is configured with `autoEscape: true` set explicitly, and the raw-output tag `<%~` is never used for a value that came from a request or the database (NFR-5, F9).
- **SEC-7**: A destination is rendered as an `href` only through one template helper that re-checks the protocol is `http:` or `https:` and otherwise renders plain text (F9).
- **SEC-8**: Fastify's `trustProxy` is set from `LINKSNIP_TRUSTED_PROXIES` (a list of addresses or CIDRs) and is never `true`; code reads the client IP only from `request.ip`, never from the `X-Forwarded-For` header (OQ-6, F8).
- **SEC-9**: @fastify/rate-limit limits `/api/*` routes and every UI POST to 100 requests per minute per `request.ip`, and the redirect route to `LINKSNIP_REDIRECT_RATE_LIMIT` per minute per IP (default 6,000 **(assumption)**); `/health`, `/static/*` and the Swagger UI are not limited. 429 responses carry `Retry-After` (F8, OQ-6).
- **SEC-10**: HTML responses carry the @fastify/helmet headers with a Content-Security-Policy whose `script-src` is `'self'` -- no `'unsafe-inline'` and no third-party origin -- so templates contain no inline `<script>` bodies or `on*=` attributes, and Chart.js is served from `/static/`, not a CDN.
- **SEC-11**: The app never makes an outbound request to a user-supplied URL. The only outbound requests are to the Safe Browsing API and the MaxMind download endpoint (OQ-14, F43: avoids SSRF).
- **SEC-12**: The redirect `Location` header is set only from the stored `short_urls` destination, never from any part of the incoming request (no open redirect).
- **SEC-13**: Secrets (`LINKSNIP_ADMIN_TOKEN`, Safe Browsing key, GeoLite2 license key, database password) come only from environment variables. `.env` is in `.gitignore`; `.env.example` lists every variable with an empty or non-secret value.

### PRIV -- privacy and retention

- **PRIV-1**: No database column, log field or error message contains a client IP address. The pino logger's `redact` option removes `req.remoteAddress`, `req.ip`, `req.headers["x-forwarded-for"]`, `req.headers["x-real-ip"]`, `req.headers.authorization` and `req.headers.cookie` (OQ-4, F14).
- **PRIV-2**: The client IP is passed only to the country lookup in `src/integrations/geo/`, which returns an ISO 3166-1 alpha-2 code or `null`; `null` is stored as `NULL` and shown as "Unknown" (FR-12, OQ-5, F13).
- **PRIV-3**: Raw-click retention is set by `LINKSNIP_CLICK_RETENTION_MONTHS` (default 13) and enforced by a job that runs at least daily; `click_daily` aggregates are never purged by it (OQ-4, F14).
- **PRIV-4**: Management tokens, the admin token and API keys are never written to logs, including at debug level (SEC-4, PRIV-1).

### PERF -- performance and scaling

- **PERF-1**: The redirect handler performs exactly one database read (an indexed lookup by `code`) and one insert into `clicks`, plus an in-process GeoLite2 lookup and an in-process bot check. It makes no network call other than to PostgreSQL (NFR-1, F10, F12).
- **PERF-2**: The redirect handler awaits the click insert before sending the 302 (OQ-7, NFR-9). If the insert throws, the handler logs `click_write_failed` and still sends the 302 (F12, ERR-3). Changing to a buffered write requires an RFC that also relaxes NFR-9 to a stated loss window (OQ-7).
- **PERF-3**: The app creates one `pg.Pool` per process at startup, sized by `LINKSNIP_DB_POOL_SIZE` (default 20 **(assumption)**); no code creates a `pg.Client` per request.
- **PERF-4**: The GeoLite2 database is opened once at startup with `maxmind.open()` and reused; it is never read from disk per request (F13).
- **PERF-5**: Every outbound HTTP call (Safe Browsing) passes `AbortSignal.timeout(2000)` **(assumption: 2 s)** and is not retried within the request; a timeout or error yields `"unchecked"` and the link is created (fail open, F7, R5).
- **PERF-6**: The create page loads no Chart.js, and its total client JavaScript is at most 10 KB gzipped **(assumption)**; Chart.js is loaded only on the analytics page (OQ-13, F27).

### ERR -- error handling

- **ERR-1**: Expected failures are thrown as `ApiError` (or a subclass) carrying an error code from `src/errors.ts` and an HTTP status; anything else is reported as 500 with code `INTERNAL_ERROR` and a generic message. Stack traces and SQL never appear in a response body.
- **ERR-2**: No catch block is empty. Every catch rethrows, converts to an `ApiError`, or logs with an `event` name and the identifiers needed to investigate (code, route), never the IP (PRIV-1).
- **ERR-3**: Analytics never break redirects: a failure in the click insert, the GeoLite2 lookup or the bot check is logged and the redirect still returns 302 to the stored destination (F12).
- **ERR-4**: A blocklist failure is logged as `blocklist_check_failed` and the create response reports `blocklistStatus: "unchecked"`; the UI shows that the URL was not checked (F7, F25).
- **ERR-5**: If the database is unreachable or a migration fails at startup, the process exits non-zero. At runtime `/health` runs `SELECT 1` and returns 200 on success and 503 on failure (F33).
- **ERR-6**: On `SIGTERM` the server stops accepting connections, finishes in-flight requests (including their click inserts), closes the pool, and exits. Why: a container restart must not drop answered clicks (NFR-9).

### LOG -- logging and observability

- **LOG-1**: Logging goes only through Fastify's pino logger (`app.log`, `request.log`); `console.*` does not appear in `src/`.
- **LOG-2**: Logs are single-line JSON, and every log call made by app code includes a snake_case `event` field (`click_write_failed`, `blocklist_check_failed`, `rate_limited`, `retention_partition_dropped`, ...), so operators can count failures from logs alone (NFR-2).
- **LOG-3**: Every request log line includes route, status code and response time in milliseconds, so redirect and API latency (NFR-1, NFR-8) can be computed from logs.

### TEST -- testing

- **TEST-1**: Unit and integration tests use Vitest. Integration tests in `test/integration/` run against a real PostgreSQL 18.7 container started by @testcontainers/postgresql; `pg` is never mocked. Why: unique-index collisions (DATA-3), partitioning (DATA-5) and `timestamptz` behavior are what the tests need to prove.
- **TEST-2**: Every acceptance criterion in FEATURES.md for a Must feature with observable HTTP behavior has at least one test whose name begins with the feature ID, e.g. `"F4: delete with a wrong token returns 403 and the link still redirects"`.
- **TEST-3**: Vitest coverage thresholds are set in config to at least 80% lines and branches for `src/services/` and `src/db/` **(assumption)**, and CI fails below them.
- **TEST-4**: Tests make no network calls outside the test containers: `UrlChecker` and the geo lookup are replaced by in-memory fakes implementing the same interfaces (ARCH-5, PRIV-2).
- **TEST-5**: A contract test loads the generated OpenAPI document and fails if a registered `/api/v1/` route or one of its declared response statuses is missing from it (F23, API-2).
- **TEST-6**: Security behaviors have explicit tests: `javascript:`, `data:` and `file:` destinations and self-links are rejected (SEC-1); a `<script>` referrer and destination render as text on the analytics page (SEC-6); a forged `X-Forwarded-For` from an untrusted address does not change the rate-limit key (SEC-8); reserved aliases are rejected in any letter case (SEC-2).
- **TEST-7**: Playwright tests cover the Shorten and View Analytics journeys in Chromium, Firefox and WebKit; each page is scanned with @axe-core/playwright using the `wcag2a`, `wcag2aa`, `wcag21a` and `wcag21aa` tags and must report zero violations (F27, OQ-13).
- **TEST-8**: A Playwright test at a 360px-wide viewport asserts `document.documentElement.scrollWidth <= 360` on every page (F27).
- **TEST-9**: `load/` contains k6 scripts whose thresholds encode redirect p95 < 100ms and average < 50ms at 1,000 requests per second, and API p95 < 200ms, with a seed script for 10M short URLs. They are run on a 2 vCPU / 4 GB host before each release, and the summary is committed to `load/results/` (F32, OQ-8).
- **TEST-10**: `load/` contains a durability test that kills the app container with `SIGKILL` during load and fails if the number of 302 responses received exceeds the number of `clicks` rows (NFR-9, R6).

### UI -- web UI, accessibility and responsive design

- **UI-1**: Pages meet WCAG 2.1 AA (OQ-13). Every form control has a `<label>` associated by `for`/`id`; each error message is text linked to its field with `aria-describedby`; no state is shown by color alone.
- **UI-2**: The click timeline chart is accompanied on the same page by a `<table>` with the same data (F26).
- **UI-3**: CSS is mobile-first: base styles target 360px width, wider layouts are added with `min-width` media queries, and no element has a fixed width over 360px (F27).
- **UI-4**: Every form is a plain HTML `<form method="post">` handled by the server and works with JavaScript disabled; JavaScript only adds conveniences such as copy-to-clipboard (ARCH-7).
- **UI-5**: When a form submission fails, the page is re-rendered with the user's submitted values and a message specific to the failure (invalid URL, blocklisted, alias taken, alias reserved, rate limited) (F25).
- **UI-6**: Every displayed date or time is in UTC and labelled "UTC" (OQ-12, F17).
- **UI-7**: The page that shows a management token states it will not be shown again and is served with `Cache-Control: no-store` (F4, F25).

### OPS -- deployment and operations

- **OPS-1**: `compose.yaml` at the repo root defines the app and `postgres:18.7-alpine`; the app `depends_on` the database with `condition: service_healthy`; the app's healthcheck calls `/health`. Docs and scripts say `docker compose`, never `docker-compose` (D2, NFR-7, F30, F33).
- **OPS-2**: PostgreSQL data lives in a named volume, and the README documents backing it up and restoring it (F35).
- **OPS-3**: The app image is a multi-stage build whose final stage contains no devDependencies and runs as the non-root `node` user.
- **OPS-4**: Every variable read in `src/config.ts` appears in `.env.example` and in the README configuration table, and a test fails if the three lists differ (F30).
- **OPS-5**: The GeoLite2 database is downloaded at startup only when `LINKSNIP_GEOLITE2_LICENSE_KEY` is set, and is never committed or baked into the image (MaxMind's license terms, OQ-5); without it the app starts and records countries as Unknown (F13).

### COMP -- completeness and ambiguity

- **COMP-1**: No `TODO`, `FIXME`, `XXX`, placeholder text, stubbed function or `throw new Error("not implemented")` is merged under `src/`, `static/` or `migrations/`.
- **COMP-2**: Code that implements an assumption from PRD.md's Open Questions or FEATURES.md's Assumptions carries a comment citing it (e.g. `// OQ-6: redirects are exempt from the 100/min limit`). Where no document settles a behavior, the implementer stops and records it in the RFC as an open question rather than inventing it. Why: a cited assumption can be found and changed when the user answers; an invented one cannot.
- **COMP-3**: The README states: NFR-2 (99.9%) is a design target, not a guarantee for operators (OQ-8); what click data is stored and for how long (OQ-4); and that Safe Browsing's free API is non-commercial only (OQ-2).

## Rule Counts

| Category | Rules |
|---|---|
| STACK | 6 |
| ARCH | 9 |
| NAME | 5 |
| DATA | 9 |
| API | 9 |
| SEC | 13 |
| PRIV | 4 |
| PERF | 6 |
| ERR | 6 |
| LOG | 3 |
| TEST | 10 |
| UI | 7 |
| OPS | 5 |
| COMP | 3 |
| **Total** | **95** |

## Rule IDs

IDs are permanent and append-only, like feature IDs. A new rule takes the next unused number in its category. A retired rule stays in place marked [REMOVED] with the reason; its ID is never reused, because RFCs and reviews cite it.

## Agent Configuration

If an AI coding agent works on this project, keep these rules in its context: add a line such as "Follow RULES.md; cite rule IDs when a change touches one" to `CLAUDE.md` (Claude Code), `AGENTS.md` (Codex and others), or a file in `.cursor/rules/` (Cursor). This run did not create those files.

## Assumptions

PRD.md's open questions are assumptions already; rules that rely on them cite the OQ. This file adds:

- The technology stack: Node.js 26 LTS, TypeScript, Fastify, PostgreSQL 18, server-rendered Eta templates, Vitest, Playwright, k6. No document names a stack; PRD-REVIEW R8 suggested PostgreSQL.
- There is no existing code to ground naming and structure in, so NAME and ARCH are chosen conventions.
- The error body shape in API-3 (F22 leaves it to the API RFC).
- The redirect abuse limit defaults to 6,000 per minute per IP (SEC-9; OQ-6 says only "much higher").
- The database pool defaults to 20 connections (PERF-3).
- The Safe Browsing timeout is 2 seconds (PERF-5).
- The create page ships at most 10 KB of gzipped JavaScript (PERF-6), as the concrete form of OQ-13's 2-second budget.
- Coverage thresholds are 80% lines and branches for services and data access (TEST-3).
- Deletion returns 204 (API-4); FEATURES.md F4 says only "success".

## Self-check

- Rule counts recounted from the rule lists above: STACK 6, ARCH 9, NAME 5, DATA 9, API 9, SEC 13, PRIV 4, PERF 6, ERR 6, LOG 3, TEST 10, UI 7, OPS 5, COMP 3; total 95. IDs in each category run from 1 with no gaps or duplicates.
- Cross-references checked against their sources: feature IDs against FEATURES.md (e.g. F7 blocklist, F8 rate limiting, F13 geolocation, F14 retention, F22 error body, F23 OpenAPI, F27 UI quality bars, F29 noindex, F33 health, F35 migrations, F36 accounts, F43 reachability); requirement and decision IDs against PRD.md (FR-19 validation, NFR-9 durability, D1 302, D2 compose, D3 namespace); rule-to-rule references (ARCH-8 from SEC-2, ERR-1 from ARCH-3, ERR-3 from PERF-2, UI-4 from ARCH-7, PRIV-1 from DATA-9 and ERR-2) point at the rules that say what the citing text claims.
- The Technology Stack table and the rules agree on versions (Node 26.13.1, PostgreSQL 18.7) and tools.
- `trace-check.py` was run on the project (`python3 trace-check.py .`): 28 requirements, 44 features, 95 rules, 0 RFCs; 0 failures, 0 warnings. Rule IDs were also checked mechanically: every ID cited in the text is defined, and each category numbers 1..n with no gaps.
