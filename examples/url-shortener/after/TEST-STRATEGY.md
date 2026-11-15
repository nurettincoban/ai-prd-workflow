# TEST-STRATEGY: LinkSnip URL Shortener

Source: `PRD.md` (FR-1 to FR-19, NFR-1 to NFR-9, OQ-1 to OQ-15), `FEATURES.md` (F1-F44), `RULES.md` (95 rules, especially TEST-1 to TEST-10), `RFCS.md` and `RFCs/RFC-001` to `RFC-012`.

This plan was written non-interactively: no person was available to answer questions. Where it makes a choice that no document settles, the choice is marked **(assumption)** and listed under Assumptions at the end.

**How to use it**: `/implement-rfc RFC-00N` writes the tests in the `## RFC-00N` section below, and `/review-rfc RFC-00N` checks that each row exists and passes. Each row cites the RFC acceptance criterion (AC) it proves. Test names begin with the feature ID (TEST-2), e.g. `"F4: delete with a wrong token returns 403 and the link still redirects"`.

## Baseline (STEP 0)

There is no code and no test suite yet. The project directory contains only the planning documents. The commands run to establish this, and their real output:

```
$ find . -path ./.git -prune -o \( -name package.json -o -name '*.test.*' -o -name '*.spec.*' -o -name 'vitest.config.*' \) -print
(no output)

$ npm test
npm error code ENOENT
npm error syscall open
npm error path /home/claude/gauntlet-run/after/package.json
npm error errno -2
npm error enoent Could not read package.json: Error: ENOENT: no such file or directory, open '/home/claude/gauntlet-run/after/package.json'

$ git ls-files
FEATURES.md
PRD-REVIEW.md
PRD.md
RFCS.md
RFCs/RFC-001-Foundation-and-Storage.md
... (RFC-002 to RFC-012)
RULES.md
```

**Baseline: 0 tests, 0 test files, nothing passes or fails.** Every row below is therefore **proposed**. The Exists? column says "Proposed" and names the file the test belongs in. Most file names come from the RFCs' File Structure sections. Where an RFC names no file, the file is proposed here and marked *(new)*.

## Product Type

PRD.md records **Web app + service/API**. This plan applies the checks of both types, as RULES.md and RFCS.md do:

| Check | Where it is tested |
|---|---|
| Authorization per resource | RFC-008 (management token, admin token) |
| Data model and migrations | RFC-001, RFC-006 (real PostgreSQL via Testcontainers, TEST-1) |
| Accessibility, responsive layout, browser support | RFC-009 (axe, 360 px, Chromium/Firefox/WebKit; TEST-7, TEST-8) |
| Page-load budget | RFC-009 (JS budget, throttled `loadEventEnd`; PERF-6) |
| SEO for public pages | RFC-009 AC 18 (noindex only, F29) |
| API contracts and versioning | RFC-001 (error body), RFC-011 (OpenAPI contract, compatibility snapshot) |
| Authentication of destructive operations, rate limiting and abuse | RFC-008, RFC-010 |
| Idempotency and retries | RFC-002 AC 3 (code retry), RFC-005 AC 4 (no blocklist retry), RFC-008 AC 3 (repeat delete is 404) |
| Observability | Log-event assertions in each RFC (LOG-2, LOG-3) |
| Data retention and privacy | RFC-003 AC 14, RFC-006 (IP absence end to end, partition drops) |
| SLOs and scaling | RFC-004, RFC-011 (k6 against a 10M-URL seed; TEST-9, TEST-10) |

Skipped, visibly:
- **Binary size**: no client binary ships (PRD Product Type). The Docker image size is recorded by RFC-012 AC 1 instead, because it drives the 5-minute deployment.
- **Offline sync**: every operation needs the server.
- **Session and login security, CSRF**: v1.0 has no accounts (F36) and no cookies or ambient credentials. RFC-009 records the no-CSRF decision as an assumption. If cookies are ever added, CSRF tests become required.
- **Mobile app, library/SDK, CLI, data pipeline and game checks**: not this product type.
- **Generic security scanning (DAST, fuzzing)**: not planned. The concrete abuse cases (TEST-6: schemes, self-links, XSS, forged `X-Forwarded-For`, reserved aliases) are tested directly in the RFCs that own them.

## Test levels and shared infrastructure

Levels follow RULES.md. The cheapest level that would catch a regression is used.

| Level | Tool | Used for |
|---|---|---|
| unit | Vitest | Pure functions (validation, code generator, range resolution, bot detector, config parsing) and static checks over the source tree ("grep tests") |
| integration | Vitest + `@testcontainers/postgresql` (PostgreSQL 18.7), Fastify `inject` | HTTP behavior, SQL, partitions, jobs. `pg` is never mocked (TEST-1) |
| contract | Vitest + Ajv against `/docs/json` | OpenAPI vs routes vs real responses (TEST-5), compatibility snapshot (API-8) |
| security | Vitest or Playwright, labelled separately | TEST-6 cases, token and IP leakage, outbound-request spies |
| end-to-end | Playwright (Chromium, Firefox, WebKit) + `@axe-core/playwright` | The Shorten and View Analytics journeys, accessibility, layout, page load (TEST-7, TEST-8) |
| performance | k6 (`grafana/k6:2.4.0`) + `load/server-latency.ts` | Redirect and API latency, throughput, durability under SIGKILL (TEST-9, TEST-10) |
| deployment | bash + Docker Compose | Image checks, fresh-install smoke test |
| manual | person, during `/review-rfc` or release | What cannot be automated; each such row says why |

**Coverage policy**: RULES TEST-3 applies: at least 80% lines and branches for `src/services/` and `src/db/`, enforced in Vitest config and CI. This plan sets no other percentage.

**Network policy**: tests make no network calls outside the test containers (TEST-4). `UrlChecker` and `GeoLookup` are in-memory fakes. Safe Browsing is exercised through an injected `fetch`, and MaxMind through a local test server.

Shared fixtures, built in RFC-001 and reused by every later RFC:
- `test/integration/helpers/database.ts`: one PostgreSQL 18.7 container per test file, migrated once, with each test in its own schema or truncated tables.
- **Fake `Clock`** (ARCH-9): tests set "now" explicitly. No test sleeps to make time pass, except RFC-010 AC 3, which waits 600 ms on a 500 ms injected window.
- **Instrumented pool**: a `pg.Pool` wrapper that records every SQL statement and can delay or fail chosen statements. RFC-003 AC 5, 11 and 12, RFC-006 AC 5 and 8 and RFC-007 AC 14 use it.
- **Log capture**: the app built with RFC-001's real logger config and a stream that collects every line. Used by every "no IP / no token in any log line" test.
- **Outbound-request spies** on `globalThis.fetch`, `node:http.request`, `node:https.request` and `node:net.connect` (RFC-002 AC 20, RFC-003 AC 5).
- **Fakes**: `FakeUrlChecker` (`"clean"`, `"listed"`, `"unchecked"`, or throws), `FakeGeoLookup` (returns a set code, `null`, or throws, and records the IP it was called with), and an injectable code generator.
- **Test IP**: `203.0.113.9` (TEST-NET-3). It is sent via `inject({ remoteAddress })` and then searched for in every column and log line.

## RFC-001: Project Foundation and Storage

Features: F22, F31, F33, F35. Prerequisites: none.

| Criterion | Test | Level | Exists? | Priority |
|---|---|---|---|---|
| AC 1: exact pins, `type: module`, engines, scripts, lockfile | Read `package.json`. Fail on any `^`, `~`, `*` or `latest`, on a missing `"type":"module"` or engines range, on a missing script among `build start dev migrate lint typecheck test`, or on a missing `package-lock.json`. | unit | Proposed: `test/unit/tooling.test.ts` *(new)* | n/a (rules STACK-1, STACK-3) |
| AC 2: strict TS, no `.js` sources | Fail if `tsconfig.json` lacks `"strict": true`, or if any `*.js` file is under `src/`, `test/` or `migrations/`. | unit | Proposed: `test/unit/tooling.test.ts` *(new)* | n/a (rule STACK-2) |
| AC 3: lint fails on errors | Run ESLint on a fixture file outside `src/` that uses `any` and has bad formatting. Fail unless the exit code is non-zero and both rules are reported. | unit | Proposed: `test/unit/tooling.test.ts` *(new)* | n/a (rule STACK-6) |
| AC 4: CI runs lint, typecheck, tests with an 80% coverage gate | Parse `.github/workflows/ci.yml` and `vitest.config.ts`. Fail if a step is missing, or if the thresholds for `src/services/**` and `src/db/**` are below 80 lines/80 branches. That CI really goes red is checked once by hand: push a branch with a failing test and see the run fail (manual, because a workflow cannot fail itself from inside a test). | unit + manual | Proposed: `test/unit/tooling.test.ts` *(new)* | n/a (rule TEST-3) |
| AC 5: `.gitignore` / `.dockerignore` | Fail if `.env`, `node_modules/`, `dist/` or `coverage/` is missing from either file, or `.git/` from `.dockerignore`. | unit | Proposed: `test/unit/tooling.test.ts` *(new)* | n/a (rule SEC-13) |
| AC 6: forbidden calls outside their homes | Scan `src/`. Fail on `Date.now(`, an argument-less `new Date()` outside `src/clock.ts`, `console.`, `Math.random`, or `process.env` outside `src/config.ts`. A fixture tree with one violation of each must make the scanner report all five, which proves the scanner is not vacuous. | unit | Proposed: `test/unit/clock-usage.test.ts` | n/a (rules ARCH-6, ARCH-9, LOG-1, SEC-3) |
| AC 7: defaults for optional variables | `loadConfig` with only the required variables. Fail if any optional value differs from the RFC's configuration table. | unit | Proposed: `test/unit/config.test.ts` | Must (F30) |
| AC 8: invalid config fails loudly; unknown keys warn | Unit tests: a missing `LINKSNIP_DATABASE_URL` or `LINKSNIP_PUBLIC_HOST`, `LINKSNIP_DB_POOL_SIZE=abc` and `LINKSNIP_PUBLIC_SCHEME=ftp` each throw a `ConfigError` whose message names the variable. `LINKSNIP_FOO=1` logs `config_unknown_variable` and loads. `LINKSNIP_DB_PASSWORD` and `LINKSNIP_HTTP_PORT` produce no log line. Child process: `node dist/src/server.js` with a missing host exits non-zero and prints the variable name on stderr. | unit + integration | Proposed: `test/unit/config.test.ts`, `test/integration/startup.test.ts` | Must (F30) |
| AC 9: public host normalization | `LNK.Example.com:443` with `https` gives `lnk.example.com`. Also checked: `:80` with `http` is stripped, and `:8443` is kept (boundary). | unit | Proposed: `test/unit/config.test.ts` | Must (F6) |
| AC 10: the three config lists agree | Compare the keys of `ConfigSchema`, `.env.example` and the README `## Configuration` table. Fail on any difference, naming the list the key is missing from. Run it against a fixture with one extra key to see it fail. | unit | Proposed: `test/unit/config-lists.test.ts` | Must (F30) |
| AC 11: migrations before listen, idempotent, failure exits | Start the server on an empty database. Fail if `listen` happens before the migrations table is populated, or if a second start runs any migration. Start it with a fixture migrations dir whose migration throws: fail unless `migration_failed` is logged, `listen` is never called, and the stubbed `process.exit` gets a non-zero code. | integration | Proposed: `test/integration/migrations.test.ts` | Should (F35) |
| AC 12: schema exactly as designed | After migration: `code` has `COLLATE "C"` and a unique constraint; `abc1234` and `ABC1234` both insert, and a second `abc1234` fails with `23505`. Every time column is `timestamptz`. The `clicks` columns from `information_schema` equal exactly `id, short_url_id, clicked_at, referrer, referrer_host, user_agent, country, is_bot`. Any extra column, including an IP column, fails the test. | integration | Proposed: `test/integration/migrations.test.ts` | Must (F31) |
| AC 13: partition creation and boundaries | Clock at 2026-11-15. `ensureClickPartitions` creates `clicks_y2026m11`, `m12` and `y2027m01`, and a second run creates nothing. A click at 2026-12-31T23:59:59.999Z lands in `m12` and one at 2027-01-01T00:00:00Z in `y2027m01` (checked with `tableoid::regclass`). | integration | Proposed: `test/integration/partitions.test.ts` | Must (F31) |
| AC 14: partition pruning | `EXPLAIN` of the literal-valued November query. Fail if any partition other than `clicks_y2026m11` appears in the plan. | integration | Proposed: `test/integration/partitions.test.ts` | Must (F31) |
| AC 15: scheduler, advisory lock, job failure | Partitions exist before `listen`. Two concurrent `withAdvisoryLock("x")` calls: exactly one runs, and the other logs `job_skipped_locked` and returns without waiting (it resolves in under 100 ms while the first holds the lock). A throwing job logs `job_failed` and runs again on the next tick (fake timers). | integration | Proposed: `test/integration/partitions.test.ts` | Must (F31) |
| AC 16: SQL only in `src/db/`, values bound | Grep `src/`: fail if `from "pg"` or an SQL keyword string appears outside `src/db/`. Fail on template-literal interpolation inside SQL strings, except in the partition-DDL builder, which gets its own unit test that it rejects non-integer bounds and names that do not match `^clicks_y\d{4}m\d{2}$`. | unit | Proposed: `test/unit/sql-placement.test.ts` *(new)* | n/a (rules ARCH-2, DATA-8) |
| AC 17: one pool per process | With `LINKSNIP_DB_POOL_SIZE=7`, the app's pool has `options.max === 7`. A spy on the `pg.Pool` constructor counts exactly 1 call across 20 requests. | integration | Proposed: `test/integration/startup.test.ts` | n/a (rule PERF-3) |
| AC 18: malformed bodies give 400, not 415 or 500 | On a test route: `{not json` with `application/json` gives 400 `INVALID_BODY`; `text/plain` gives 400 `INVALID_BODY` (fails on 415); a schema-invalid body gives 400 `VALIDATION_FAILED` and the message names the field. | integration | Proposed: `test/integration/errors.test.ts` | Must (F22) |
| AC 19: 500 hides internals | A handler throws `new Error("SELECT secret FROM x")`. Expect 500 and exactly `{"error":{"code":"INTERNAL_ERROR","message":"Internal server error."}}`. Fail if the body contains `SELECT`, `at ` (a stack frame) or the original message. `unhandled_error` is logged. | integration | Proposed: `test/integration/errors.test.ts` | Must (F22) |
| AC 20: API 404 and error shape | `GET /api/v1/does-not-exist` gives 404 `NOT_FOUND`. A table-driven test over every error status the RFC produces asserts the keys are exactly `error.code` and `error.message` and the content type is `application/json`. | integration | Proposed: `test/integration/errors.test.ts` | Must (F22) |
| AC 21: HTML error pages | An unknown non-API path gives 404 HTML from `not-found.eta`. A throwing web route gives 500 HTML from `error.eta`. Neither body contains a stack frame or the error message. | integration | Proposed: `test/integration/errors.test.ts` | Must (F22) |
| AC 22: `/health` 200 and 503 within 1.5 s | Database up: 200 `{"status":"ok"}`, and its `request_completed` line is at `debug`. Container paused: 503 `{"status":"unavailable"}`, and the test fails if the response takes 1.5 s or longer. | integration | Proposed: `test/integration/health.test.ts` | Must (F33) |
| AC 22a: health watchdog exits | Database paused, fake timers: after 5 failed pings nothing happens. After the 6th, `health_watchdog_exit` is logged and shutdown starts with exit code 1. A success in between resets the count. | integration | Proposed: `test/integration/health-watchdog.test.ts` | Must (F33) |
| AC 22b: oversize body and other Fastify 4xx | A body of 16 KiB + 1 byte gives 400 `INVALID_BODY`, and exactly 16 KiB is accepted (boundary). Other Fastify 4xx errors (unsupported media type, bad URL encoding) give 400 `VALIDATION_FAILED` with the error body, never 500. | integration | Proposed: `test/integration/errors.test.ts` | Must (F22) |
| AC 23: reserved aliases cover every route | `RESERVED_ALIASES` includes `api`, `docs`, `static`, `health`. Enumerate the built app's routes and fail if a top-level static segment is missing from the list. A test-only route `/zzz` must make the check fail. | integration | Proposed: `test/integration/reserved-routes.test.ts` | Must (F2) |
| AC 24: helmet, CSP and Eta autoEscape | Every response from `/` and `/api/v1/...` has helmet headers. The CSP `script-src` is exactly `'self'`, and the test fails on `'unsafe-inline'` anywhere. The Eta config object has `autoEscape === true` set explicitly. | security | Proposed: `test/integration/errors.test.ts` | Must (F9) |
| AC 25: log redaction and request line | Unit: log an object with every PRIV-1 path set and expect `[Redacted]` at each path. Integration: a request with `Authorization`, `Cookie`, `X-Forwarded-For` and `X-Real-IP` from `203.0.113.9`. Fail if any captured line contains any of those values or the IP. Each request yields exactly one `request_completed` line with `method`, `route`, `statusCode` and `responseTimeMs`. | security | Proposed: `test/unit/logger.test.ts`, `test/integration/errors.test.ts` | Must (F14) |
| AC 25a: HSTS only on https | With scheme `http`: no `Strict-Transport-Security` header and no `upgrade-insecure-requests` in the CSP. With `https`: both are present. | integration | Proposed: `test/integration/errors.test.ts` | n/a (rule SEC-10; RFC-001 assumption) |
| AC 26: graceful shutdown | Start a request to a slow test route (500 ms), then send `SIGTERM` to a child-process server. Fail unless the request completes with 200, the pool `end` is called, and the exit code is 0. | integration | Proposed: `test/integration/shutdown.test.ts` | Must (F12) |
| AC 27: production image | CI step: `docker build`, then `docker run --rm --entrypoint id` prints a non-root uid for `node`. `docker run ... ls node_modules/vitest` must fail, which shows no devDependencies are in the image. | deployment | Proposed: `ci.yml` job `image-check` *(new)* | Must (F30) |
| AC 28: compose up, health ordering, persistent volume | CI step on a fresh checkout with no `.env`: `docker compose up -d`. Wait for `app` healthy. Fail if `app` started before `db` was healthy (container start timestamps) or if the volume `linksnip-db` is missing. Create a row, run `down` then `up`, and fail if the row is gone. RFC-012's `scripts/deploy-smoke.sh` replaces this check later. | deployment | Proposed: `ci.yml` job `compose-check` *(new)* | Must (F30) |
| AC 29: no placeholders; assumptions cited | Automated half: grep `src/`, `static/` and `migrations/` and fail on `TODO`, `FIXME`, `XXX` or `not implemented`. Manual half: the reviewer confirms that each RFC-001 assumption (e.g. `LINKSNIP_PUBLIC_SCHEME`) has a comment citing it. Whether a comment cites the right assumption is a judgment a grep cannot make. | unit + manual | Proposed: `test/unit/no-placeholders.test.ts` *(new)* | n/a (rules COMP-1, COMP-2) |
| AC 30: tests named with feature IDs | Manual, during `/review-rfc`: run `npx vitest list` and check that tests proving F22, F31, F33 or F35 behavior start with that ID. Which tests "apply" to a feature is a judgment call, so this is not automated. | manual | Proposed: review checklist | n/a (rule TEST-2) |

Test data and prerequisites:
- PostgreSQL 18.7 container helper (TEST-1), fake `Clock`, log capture, and a fixture migrations dir with a throwing migration.
- Pausing the database: `container.pause()` from Testcontainers (AC 22, 22a).
- AC 27 and 28 need Docker in CI. The GitHub-hosted runner has it.
- Every later RFC reuses the helpers created here. Build them in RFC-001 rather than per test file.

## RFC-002: Link Creation

Features: F1, F2, F3, F6. Prerequisites: RFC-001 (error handler, database helper, `RESERVED_ALIASES`).

| Criterion | Test | Level | Exists? | Priority |
|---|---|---|---|---|
| AC 1: create with a generated code | `POST /api/v1/urls {"url":"https://example.com/a"}` with the no-op checker. Expect 201; `code` matches `^[0-9A-Za-z]{7}$`; `shortUrl` = scheme + host + `/` + code; `createdAt` ends in `Z`; `expiresAt: null`; a 43-character base64url `managementToken`; `blocklistStatus: "unchecked"`. Any missing or extra field fails. | integration | Proposed: `test/integration/create-url.test.ts` | Must (F1) |
| AC 2: case-sensitive codes | Create aliases `Abc1234` and `abc1234` with different destinations. Both give 201, and two rows exist with their own destinations. | integration | Proposed: `test/integration/create-url.test.ts` | Must (F1) |
| AC 3: retry on collision, give up after 5 | Inject a generator that first returns an existing code: the response carries the second code and the existing row is unchanged. A generator that always collides gives 500 `INTERNAL_ERROR` after exactly 5 attempts (counted) and logs `code_generation_failed`. Boundary: 4 collisions then a free code gives 201. | integration | Proposed: `test/integration/create-url.test.ts` | Must (F1) |
| AC 4: generated code never a reserved word | `reservedAliases = ["zzzzzzz"]` and a generator yielding `ZZZZZZZ` then `abc1234`. Expect `abc1234`, and no `ZZZZZZZ` row. | integration | Proposed: `test/integration/create-url.test.ts` | Must (F1) |
| AC 5: generator format and source | A fast-check property over 10,000 samples checks the format. A spy on `crypto.randomInt` must be called 7 times per code. | unit | Proposed: `test/unit/code-generator.test.ts` | Must (F1) |
| AC 6: token stored only as a hash, never logged | `management_token_hash` = SHA-256(token). Search every `text` column of the row and every captured log line for the token. Fail on any hit. | security | Proposed: `test/unit/tokens.test.ts`, `test/integration/create-url.test.ts` | Must (F4) |
| AC 7: 201 is `no-store` | Expect `Cache-Control: no-store` on 201. | integration | Proposed: `test/integration/create-url.test.ts` | Must (F4) |
| AC 8: alias accepted; aliases case-sensitive | `Promo2026` gives 201 with that code; `promo2026` then also gives 201 as a separate link. | integration | Proposed: `test/integration/create-url.test.ts` | Must (F2) |
| AC 9: alias length and charset | Table: lengths 2 and 31 are rejected; 3 and 30 are accepted (boundaries); `pro-mo`, `promo!` and `prömo` are rejected. Each rejection is 400 `INVALID_ALIAS`. | unit + integration | Proposed: `test/unit/validation.test.ts`, `test/integration/create-url.test.ts` | Must (F2) |
| AC 10: reserved aliases in any case | `api`, `API`, `Docs`, `static` and `HEALTH` give 400 `ALIAS_RESERVED`, and the message contains "reserved". | security | Proposed: `test/integration/create-url.test.ts` | Must (F2) |
| AC 11: taken alias gives 409, existing row untouched | Snapshot the existing row (all columns), then create the same alias with another destination. Expect 409 `ALIAS_TAKEN`. Fail if any column of the snapshot changed. Also try an alias equal to an existing *generated* code (D3). | integration | Proposed: `test/integration/create-url.test.ts` | Must (F2) |
| AC 12: offset converted to UTC | `2026-12-31T23:59:59+02:00` is stored and returned as `2026-12-31T21:59:59Z`. | integration | Proposed: `test/integration/create-url.test.ts` | Must (F3) |
| AC 13: expiry grammar and range | Fake clock. Rejected with 400 `INVALID_EXPIRATION`: now, now − 1 ms, no offset, date only, no seconds, `2026-02-31`, `2026-02-29`, second `60`, garbage. Accepted: now + 1 ms (boundary), `2028-02-29T10:00:00Z`, lower-case `t`/`z`, and `.123456Z` (stored as `.123`). | unit + integration | Proposed: `test/unit/validation.test.ts`, `test/integration/create-url.test.ts` | Must (F3) |
| AC 13a: empty or null optional fields mean absent | `alias: ""`, `alias: null`, `expiresAt: ""` and `expiresAt: null` each give 201 with a generated code and `expiresAt: null`. | integration | Proposed: `test/integration/create-url.test.ts` | Must (F2, F3) |
| AC 14: no edit routes | Enumerate the route table. Fail on any `PUT` or `PATCH` route, or on any route other than `POST /api/v1/urls` whose handler calls `insertShortUrl` or an update in `src/db/short-urls.ts`. | integration | Proposed: `test/integration/create-url.test.ts` | Must (F3) |
| AC 15: dangerous schemes rejected | `javascript:alert(1)`, `data:text/html,x`, `file:///etc/passwd` and `ftp://example.com/` give 400 `INVALID_URL`. Also checked: `JavaScript:` with mixed case. | security | Proposed: `test/unit/validation.test.ts`, `test/integration/create-url.test.ts` | Must (F6) |
| AC 16: malformed URLs rejected | Each of the 8 listed inputs gives 400 `INVALID_URL`, including leading space, trailing newline and backslash forms. | unit | Proposed: `test/unit/validation.test.ts` | Must (F6) |
| AC 17: 2,048-character limit | A URL of exactly 2,048 characters gives 201; 2,049 gives 400 `INVALID_URL`. | unit + integration | Proposed: `test/unit/validation.test.ts`, `test/integration/create-url.test.ts` | Must (F6) |
| AC 18: self-links rejected | With `LINKSNIP_PUBLIC_HOST=lnk.example.com`: `https://LNK.example.com/x` and `http://lnk.example.com:80/x` give 400 `SELF_LINK`; `https://other.example.com/x` gives 201. Also checked: `https://lnk.example.com:8443/x`. The RFC does not say whether a non-default port is a self-link. The test records the current behavior and flags it for review (assumption). | security | Proposed: `test/unit/validation.test.ts` | Must (F6) |
| AC 19: no coercion, no stripping, no 500 | `{"url":123}`, a missing `url`, and an unknown field `alais` each give 400 `VALIDATION_FAILED`. A test asserting 201 or 500 fails. A non-JSON body gives 400 `INVALID_BODY`. | integration | Proposed: `test/integration/create-url.test.ts` | Must (F6, F22) |
| AC 20: no outbound request on create | Spies on `fetch`, `http.request` and `https.request`. Zero calls during `POST /api/v1/urls` with destination `http://127.0.0.1:1/` (which a reachability probe would hit). | security | Proposed: `test/integration/create-url.test.ts` | Must (F6) |
| AC 21: checker interface and fail-open | Fake checker: `"listed"` gives 400 `BLOCKLISTED_URL` and zero rows; `"clean"` gives `blocklistStatus: "clean"`; a throwing checker gives 201 `"unchecked"` and one `blocklist_check_failed` line. | integration | Proposed: `test/integration/create-url.test.ts` | Must (F7) |
| AC 22: service layering | Grep: `short-url-service.ts` does not import `fastify`; `INSERT INTO short_urls` appears only in `src/db/short-urls.ts`; `insertShortUrl` is imported only by `short-url-service.ts`. | unit | Proposed: `test/unit/sql-placement.test.ts` *(new, from RFC-001)* | Must (F21) |
| AC 23: TypeBox schemas for body and every status | From the route options: a body schema exists and response schemas exist for 201, 400, 409 and 500. RFC-011 AC 3 later checks the same thing for every route. | unit | Proposed: `test/integration/create-url.test.ts` | Must (F23) |
| AC 24: files exist; feature-ID names | Manual, during `/review-rfc`: each file in the File Structure section exists, and `npx vitest list` shows the tests above named `F1:`, `F2:`, `F3:`, `F6:`. | manual | Proposed: review checklist | n/a (rule TEST-2) |

Test data and prerequisites:
- An injectable `generateCode` and `reservedAliases` (AC 3, 4), and `FakeUrlChecker` (AC 21).
- A string fixture for exact-length URLs: `https://e.com/` padded with `a` to 2,048 and 2,049 characters.
- Fake `Clock` set to 2026-11-15T12:00:00Z for the expiry table.

## RFC-003: Redirect and Click Recording

Features: F10, F11, F12, F13 (Must), F15 (Should). Prerequisites: RFC-001 (partitions, instrumented pool), RFC-002 (creating links in tests).

| Criterion | Test | Level | Exists? | Priority |
|---|---|---|---|---|
| AC 1: 302, `Location`, `no-store` | `GET /{code}` gives 302 with `Location` equal to the stored destination and `Cache-Control: private, no-store`. Fail on 301, 307 or 308. | integration | Proposed: `test/integration/redirect.test.ts` | Must (F10) |
| AC 2: query string ignored; extra path is 404 | `/{code}?utm=x` and `/{code}?url=https://evil.example` give `Location` unchanged (SEC-12, open redirect). `/{code}/x` gives 404. | security | Proposed: `test/integration/redirect.test.ts` | Must (F10) |
| AC 3: repeat clicks both counted | Two GETs with the same UA and cookies both give 302, and the `clicks` count goes up by 2. | integration | Proposed: `test/integration/redirect.test.ts` | Must (F10) |
| AC 4: HEAD mirrors GET, no click | `HEAD` gives the same status and headers as `GET`, and the click count is unchanged. Also checked for an unknown code (404). See the FR-8 conflict under Artifact conflicts. | integration | Proposed: `test/integration/redirect.test.ts` | Must (F10) |
| AC 5: exactly one read, one insert, no other network | The instrumented pool records exactly 1 `short_urls` SELECT and 1 `clicks` INSERT per 302. Outbound spies (`fetch`, `http`, `https`, `net.connect` excluding pool sockets) record zero calls. | integration | Proposed: `test/integration/redirect.test.ts` | Must (F10) |
| AC 6: identical 404s | Unknown, deleted, expired (`expires_at` = now and now − 1 s) and malformed (`/ab`) codes give 404. Compare bodies and headers minus `Date`: fail on any difference. Each has `Cache-Control: no-store`. | integration | Proposed: `test/integration/redirect.test.ts` | Must (F11) |
| AC 6a: lookup failure gives 503 | Stop the database container. Expect 503 with `Retry-After: 5` and `no-store`, a `redirect_lookup_failed` line, and zero insert attempts (instrumented pool). | integration | Proposed: `test/integration/redirect.test.ts` | Must (F11) |
| AC 7: expiry boundary | Fake clock at `expires_at` − 1 ms gives 302; exactly `expires_at` gives 404. | integration | Proposed: `test/integration/redirect.test.ts` | Must (F11) |
| AC 8: 404 records no click | Click count unchanged after each AC 6 case. | integration | Proposed: `test/integration/redirect.test.ts` | Must (F11) |
| AC 9: malformed codes never reach the database | `/ab`, `/a-b` and a 31-character code give 404, and the instrumented pool records zero statements. | integration | Proposed: `test/integration/redirect.test.ts` | Must (F11) |
| AC 10: click row contents | One row per 302. `clicked_at` = the fake clock's now. Referrer, `referrer_host` (lower-cased), UA, country and `is_bot` match the request. With no `Referer` and no UA, they are stored as `''`. `referrer_host` extraction is also unit-tested (`HTTPS://News.Example.COM/a` gives `news.example.com`; a non-URL gives `''`). | integration + unit | Proposed: `test/integration/click-recording.test.ts`, `test/unit/referrer-host.test.ts` | Must (F12) |
| AC 11: insert awaited before the 302 | Pause the insert with the instrumented pool's gate. Assert no response arrives within 200 ms; release the gate; the 302 arrives. | integration | Proposed: `test/integration/click-recording.test.ts` | Must (F12) |
| AC 12: insert failure or timeout never blocks the redirect | Drop the current month's partition: the response is still 302, and there is one `click_write_failed` line with the code. A 2.5 s delay injected on the insert: the 302 arrives at about 2 s (between 1.9 and 2.5 s), and `click_write_timeout` is logged. | integration | Proposed: `test/integration/click-recording.test.ts` | Must (F12) |
| AC 13: long referrer and UA truncated | A 2,049-character referrer is stored as 2,048 characters; a 1,025-character UA as 1,024. The status is 302, not 4xx. | integration | Proposed: `test/integration/click-recording.test.ts` | Must (F12) |
| AC 14: IP never stored or logged | `inject({ remoteAddress: "203.0.113.9" })` with fake geo. Fail if `203.0.113.9` appears in any column of the click row or any captured log line, including the error paths of AC 12 and 16. | security | Proposed: `test/integration/click-recording.test.ts` | Must (F14) |
| AC 15: country stored | Fake geo `"DE"` gives `country = 'DE'`; `null` gives SQL `NULL`. | integration | Proposed: `test/integration/click-recording.test.ts` | Must (F13) |
| AC 16: geo or bot failure never blocks the redirect | Throwing geo gives `country NULL` and `geo_lookup_failed`; a throwing bot detector gives `is_bot = false` and `bot_check_failed`. Both still give 302. | integration | Proposed: `test/integration/click-recording.test.ts` | Must (F13) |
| AC 17: no key means no download | Start without a license key, with the downloader URL pointed at a local server that records hits. Expect zero hits and every country `NULL`. | integration | Proposed: `test/integration/geolite2-download.test.ts` | Must (F13) |
| AC 18: download, auth, failure, refresh, account ID | Local test server. With no file: the download begins after `listen`, the basic-auth header is `<account>:<key>`, and the reader is swapped. A corrupt archive and an HTTP 500 each log `geoip_download_failed` without the key or account ID and keep the old reader. Fake clock: a file 6 days old is not downloaded; at 7 days the `geolite2-refresh` job downloads. A key without an account ID makes startup exit naming `LINKSNIP_GEOLITE2_ACCOUNT_ID`. Tar extraction (`GeoLite2-Country.mmdb` found in a nested path, path traversal refused) is unit-tested. | integration + unit | Proposed: `test/integration/geolite2-download.test.ts`, `test/unit/tar-extract.test.ts` | Must (F13) |
| AC 19: real MaxMind reader | MaxMind's published test database: a known test IPv4 and its `::ffff:` form give the same country, and `10.0.0.1` gives `null`. | unit | Proposed: `test/unit/maxmind-geo.test.ts` *(new)* | Must (F13) |
| AC 20: no GeoLite2 database committed | Fail if `*.mmdb` is missing from `.gitignore` or `.dockerignore`, or if `git ls-files` lists any `.mmdb` other than the MaxMind test fixture path. The CI image-check job (RFC-001) fails if the image contains `*.mmdb`. | unit + deployment | Proposed: `test/unit/tooling.test.ts` *(new, from RFC-001)* | Must (F13) |
| AC 21: bot detection | `facebookexternalhit/1.1`, `Twitterbot/1.0`, `Slackbot-LinkExpanding 1.0` and an empty UA give `is_bot = true`; a current desktop Chrome UA gives `false`. | unit + integration | Proposed: `test/unit/bot-detector.test.ts`, `test/integration/click-recording.test.ts` | Should (F15) |
| AC 22: operator bot list replaces the default | A patterns file with `^MyCrawler`: `MyCrawler/2` and `mycrawler/2` are bots, `facebookexternalhit/1.1` is not, and an empty UA still is. An unreadable file, an invalid regex, and a comments-only file each make startup exit naming `LINKSNIP_BOT_PATTERNS_FILE`. | unit + integration | Proposed: `test/unit/bot-detector.test.ts`, `test/integration/startup.test.ts` | Should (F15) |
| AC 23: new variables in all three lists | The RFC-001 OPS-4 test passes with the new variables added. | unit | Proposed: `test/unit/config-lists.test.ts` | Must (F30) |
| AC 24: files, names, assumption comments | Manual review: files exist; tests are named `F10:` to `F15:`; comments cite the HEAD, dropped-query-string, empty-UA and weekly-refresh assumptions. | manual | Proposed: review checklist | n/a (rules TEST-2, COMP-2) |

Test data and prerequisites:
- MaxMind's published GeoLite2 **test** database, committed as a fixture (RFCS.md conflict item 7). If its license is unclear, generate an `.mmdb` fixture instead, as RFC-003 says.
- A local HTTP server serving a valid tar.gz, a corrupt archive and a 500 (AC 18).
- A fixed list of bot and browser UA strings in `test/fixtures/user-agents.ts` *(new)*.
- Instrumented pool with gate and delay (AC 5, 9, 11, 12).

## RFC-004: Redirect Load and Durability Tests

Features: F32 (redirect and durability half). Prerequisites: RFC-003. This RFC *is* tests. Its rows are the k6 and shell harness, and each row also says what makes the harness itself wrong.

| Criterion | Test | Level | Exists? | Priority |
|---|---|---|---|---|
| AC 1: seed 10M URLs and 10,000 active codes | Run `load/seed.sh --count 10000000`. Afterwards `count(*) = 10000000` exactly, and `active-codes.txt` has 10,000 distinct lines, each an existing code. A second run without `--force` on a populated table exits non-zero and changes nothing. With `--force` it reseeds. `git check-ignore load/data/active-codes.txt` succeeds, and `package.json` dependencies are unchanged. A fast variant runs `--count 1000` in CI against the test container. | performance | Proposed: `load/seed.sh`, `load/seed.sql`; CI smoke `--count 1000` *(new)* | Must (F32) |
| AC 2: 1,000 redirects/s for 10 minutes, zero failures | `load/redirect.js` with a 60 s warm-up scenario and a 10-minute steady scenario. The k6 thresholds `http_req_failed == 0` (302 counts as success, with `redirects: 0`) and `dropped_iterations == 0` apply to the steady scenario only. Client p95 and average are reported. | performance | Proposed: `load/redirect.js`, `load/run-redirect.sh` | Must (F32) |
| AC 3: server-side p95 < 100 ms, average < 50 ms | `load/server-latency.ts` reads the steady-window `request_completed` lines for the redirect route and exits non-zero unless p95 < 100 and average < 50. It is unit-tested on synthetic logs: a log with p95 = 99 passes, one with 100 fails, and lines from other routes or outside the window are ignored. | performance + unit | Proposed: `load/server-latency.ts`, `test/unit/server-latency.test.ts` *(new)* | Must (F32) |
| AC 4: zero click loss across SIGKILL, three runs | `load/durability.sh` runs three times with a random kill between 15 and 45 s. In each run, fail if the 302s k6 received exceed the increase in `clicks` rows for the target code. The log is also scanned: any `click_write_failed` or `click_write_timeout` line during the run is reported, because it explains a loss rather than excusing it. | performance | Proposed: `load/durability.sh`, `load/durability.js` | Must (F12) |
| AC 5: `load/README.md` documents host and runs | Manual review: the reference host (2 vCPU, 4 GB, fsync-honouring SSD, separate k6 machine), seeding, each scenario and the results location are all described. This is documentation content, so a person judges whether it is usable. | manual | Proposed: review checklist | Must (F32) |
| AC 6: run labelling and verdict run | Manual: `RESULT.md` carries one of the three labels, and a verdict run on the reference host exists before release (RFC-011 AC 10). It cannot be automated because it needs the reference hardware and a separate machine. | manual | Proposed: release checklist | Must (F32) |
| AC 7: on failure, stop for OQ-7 | Manual: if a gating threshold fails on the reference host, the reviewer checks that `git diff` shows no change to the write path or schema, that the numbers are in `RESULT.md` and Implementation Notes, and that a decision on OQ-7 was requested. This is a process rule, not product behavior. | manual | Proposed: review checklist | Must (F32) |
| AC 8: load compose overrides; no forbidden tuning | A grep test fails if `synchronous_commit`, `fsync` or `full_page_writes` appears in `compose.yaml` or `load/compose.load.yaml`, or if `LINKSNIP_REDIRECT_RATE_LIMIT=1000000` is missing from the load file. The rule that tuning recorded in `RESULT.md` must also be in `compose.yaml` is checked by hand at review. | unit + manual | Proposed: `test/unit/load-config.test.ts` *(new)* | Must (F32) |

Test data and prerequisites:
- The reference host and a separate k6 machine (assumption from RFC-004). These are not available in CI. AC 2, 3 and 4 are run by hand on that host, and their scripts decide pass or fail mechanically.
- The 10M seed takes a while to build. Keep its volume between runs; `--force` is the only way to reseed.
- The steady-window boundaries come from k6's scenario start and end timestamps, which `run-redirect.sh` writes beside the log.
- This RFC runs early on purpose. A failure here stops the plan before RFC-005 to RFC-012 build on the click write path (OQ-7).

## RFC-005: Safe Browsing Blocklist

Features: F7. Prerequisites: RFC-002 (`UrlChecker` interface, create endpoint).

| Criterion | Test | Level | Exists? | Priority |
|---|---|---|---|---|
| AC 1: checker choice from config | `buildDeps` with a key gives `instanceof SafeBrowsingChecker`. With unset, `""` and `"   "` it gives `NoopChecker`, and `blocklist_disabled` is logged exactly once (not per request). | unit | Proposed: `test/unit/safe-browsing-checker.test.ts` | Must (F7) |
| AC 2: listed URL rejected | Injected `fetch` returns `{"matches":[{...}]}`. Expect 400 `BLOCKLISTED_URL` and zero rows. | integration | Proposed: `test/integration/create-url-blocklist.test.ts` | Must (F7) |
| AC 3: clean URL | `{}` gives 201 `blocklistStatus: "clean"`. Also checked: `{"matches":[]}` is clean (boundary of "non-empty"). | integration | Proposed: `test/integration/create-url-blocklist.test.ts` | Must (F7) |
| AC 4: fail open, no retry | Table: HTTP 400, 403, 429, 500, a thrown network error, and the injected signal aborted. Each gives `"unchecked"`, exactly one `blocklist_check_failed` line containing the hostname, and exactly one `fetch` call. Through the API, each gives 201 `"unchecked"`. A separate test asserts the default `makeSignal()` is `AbortSignal.timeout(2000)` (spy on `AbortSignal.timeout`). | unit + integration | Proposed: `test/unit/safe-browsing-checker.test.ts`, `test/integration/create-url-blocklist.test.ts` | Must (F7) |
| AC 5: request body | The captured body has the four threat types, `ANY_PLATFORM`, `threatEntries[0].url` equal to the create response's `destination` (`https://EXAMPLE.com` is sent as `https://example.com/`), and `clientVersion` equal to `package.json`'s version. | unit | Proposed: `test/unit/safe-browsing-checker.test.ts` | Must (F7) |
| AC 6: API key confined to one header | Fail if the key appears in any log line, error message, response body, or captured `fetch` URL. Every URL must equal `https://safebrowsing.googleapis.com/v4/threatMatches:find` exactly. The key appears only in `X-Goog-Api-Key`. Also checked on the AC 4 failure paths. | security | Proposed: `test/unit/safe-browsing-checker.test.ts` | Must (F7) |
| AC 7: never requests the destination | Every captured `fetch` host is `safebrowsing.googleapis.com`, including for destinations `http://127.0.0.1/` and `http://169.254.169.254/` (SSRF probes). | security | Proposed: `test/unit/safe-browsing-checker.test.ts` | Must (F7) |
| AC 8: variable in all three lists | The OPS-4 test passes. | unit | Proposed: `test/unit/config-lists.test.ts` | Must (F30) |
| AC 9: README section content | Phrase check on README `### Malware and phishing check`: "non-commercial", "Web Risk", the disabled and failing behavior, and "only at creation". RFC-012 AC 5 later checks the same section. | unit | Proposed: `test/unit/readme-sections.test.ts` (created here, extended by RFC-012) | Must (F7) |
| AC 10: names and the fail-open comment | Manual review: tests are named `F7:`; the fail-open code has a comment citing R5 or the FEATURES.md Assumptions. | manual | Proposed: review checklist | n/a (rules TEST-2, COMP-2) |

Test data and prerequisites:
- An injected `fetch` stub returning canned Safe Browsing responses, and an injected signal factory the test can abort (no real 2 s wait).
- No test calls Google (TEST-4). The real-provider check is a manual gap (see Manual testing gaps).

## RFC-006: Click Rollup and Retention

Features: F14. Prerequisites: RFC-001 (partitions, advisory locks, scheduler), RFC-003 (clicks to roll up).

| Criterion | Test | Level | Exists? | Priority |
|---|---|---|---|---|
| AC 1: migration creates `click_daily` and state | After migration: the `click_daily` unique key is `NULLS NOT DISTINCT` (two rows with the same null `country` conflict); the `(short_url_id, day)` index exists; `click_rollup_state` holds exactly one row and a second insert fails. | integration | Proposed: `test/integration/click-rollup.test.ts` | Must (F14) |
| AC 2: grace period and grouping | Clicks on 11-13 and 11-14. At 2026-11-15T00:10Z only 11-13 is rolled up. At 00:16Z, 11-14 is too. Rows are grouped by `short_url_id, referrer_host, country, is_bot`; the watermark is `2026-11-14`; no row for 11-15. Boundary: exactly 00:15Z is also tested, and the result is recorded against the RFC's "15 minutes after" wording. | integration | Proposed: `test/integration/click-rollup.test.ts` | Must (F14) |
| AC 3: re-run is idempotent | Reset the watermark and re-run. The `click_daily` contents are identical (compared row by row). | integration | Proposed: `test/integration/click-rollup.test.ts` | Must (F14) |
| AC 4: crash between days resumes | The `afterDayCommitted` hook throws after day N. The watermark is N; the next run starts at N+1; totals equal ground truth. | integration | Proposed: `test/integration/click-rollup.test.ts` | Must (F14) |
| AC 4a: missing raw partition is skipped | Drop the partition for the day after the watermark. `rollup_skipped_no_raw` is logged and the `click_daily` row count is unchanged. | integration | Proposed: `test/integration/click-rollup.test.ts` | Must (F14) |
| AC 5: whole-partition drops only | 13 months, clock 2026-11-15. Every partition with upper bound ≤ 2025-10-01 is dropped; the 2025-10 partition (upper bound 2025-11-01) is kept (boundary). Each drop is `DETACH` + `DROP` in one transaction with `lock_timeout` 2s, logging `retention_partition_dropped`. The statement recorder must contain no match for `/DELETE\s+FROM\s+clicks/i`. | integration | Proposed: `test/integration/click-retention.test.ts` | Must (F14) |
| AC 5a: lock timeout and orphan sweep | A second connection holds `ACCESS SHARE` in an open transaction on `clicks`. The drop gives up in about 2 s (between 1.8 and 3 s), logs `retention_lock_timeout`, and the partition is still attached. A pre-detached `clicks_y2025m01` is dropped by the sweep. | integration | Proposed: `test/integration/click-retention.test.ts` | Must (F14) |
| AC 6: never drop un-rolled-up days | Hold the `click-rollup` advisory lock from another connection. A past-window partition containing a day after the watermark is kept, and `retention_blocked_not_rolled_up` is logged at `warn`. Without the lock, rollup runs first and then the drop happens. | integration | Proposed: `test/integration/click-retention.test.ts` | Must (F14) |
| AC 7: totals survive the purge | Compute per-link totals and per-day counts from raw clicks, run rollup and retention, and recompute from `click_daily`. Fail on any difference. | integration | Proposed: `test/integration/click-retention.test.ts` | Must (F14) |
| AC 8: aggregate purge is opt-in and validated | Unset: the recorder shows no `DELETE FROM click_daily`. With 24 and clock 2026-11-15: rows with `day < 2024-11-15` are gone, `2024-11-15` is kept (boundary), and `aggregate_retention_purged` is logged. Startup exits naming the variable for 12 (below 13), 1201, and `1.5`. | integration + unit | Proposed: `test/integration/click-retention.test.ts`, `test/unit/config.test.ts` | Must (F14) |
| AC 9: job registration | Unit test of the job list that `startServer` registers: `click-rollup` every 900,000 ms with `runAtStart: true`; `click-retention` every 86,400,000 ms with `runAtStart: true`; each lock key equals its job name. | unit | Proposed: `test/unit/jobs.test.ts` *(new)* | Must (F14) |
| AC 10: IP absent end to end | Full app; redirects with `remoteAddress 203.0.113.9`. The fake geo asserts it received `203.0.113.9`, which proves the IP reached the app. Then run rollup, and fail if the string appears in any column of `short_urls`, `clicks` or `click_daily` (dump each table as text) or in any log line. | security | Proposed: `test/integration/privacy.test.ts` | Must (F14) |
| AC 11: privacy note in README | Phrase check: every statement in RFC-006's Privacy note section appears under `## Privacy and data retention`. | unit | Proposed: `test/unit/readme-sections.test.ts` | Must (F14) |
| AC 12: variables in all three lists | The OPS-4 test passes. | unit | Proposed: `test/unit/config-lists.test.ts` | Must (F30) |
| AC 13: names and assumption comments | Manual review: tests are named `F14:`; comments cite the 13-to-14-month granularity and the PRIV-3 reading. | manual | Proposed: review checklist | n/a (rules TEST-2, COMP-2) |

Test data and prerequisites:
- Clicks inserted directly via `src/db/` helpers with chosen `clicked_at` values spanning 2024-10 to 2026-11, so partitions on both sides of every cutoff exist.
- The statement-recording pool from RFC-001. A second raw `pg.Client` is used for lock contention (AC 5a, 6).
- See the PRIV-3 / F14 conflict under Artifact conflicts: AC 8 tests FEATURES.md's reading.

## RFC-007: Analytics API

Features: F16, F17, F18, F19, F20 (Must); F15 exclusion (Should). Prerequisites: RFC-003 (clicks), RFC-006 (`click_daily`, watermark).

| Criterion | Test | Level | Exists? | Priority |
|---|---|---|---|---|
| AC 1: zero clicks, public | A link with no clicks, no `Authorization` header: 200 `totalClicks: 0`. | integration | Proposed: `test/integration/analytics.test.ts` | Must (F16) |
| AC 2: identical 404s | Unknown, deleted and expired codes give 404 `NOT_FOUND`; the bodies are byte-identical. | integration | Proposed: `test/integration/analytics.test.ts` | Must (F16) |
| AC 3: bots excluded everywhere | 3 human and 2 bot clicks with distinct referrers and countries. The total is 3; no bot referrer or country appears; timeline sums to 3; `excludesBots: true`. | integration | Proposed: `test/integration/analytics.test.ts` | Should (F15) |
| AC 4: daily buckets with zeros | 2026-11-01..07 gives exactly 7 entries in order, and empty days are `clicks: 0`. | integration | Proposed: `test/integration/analytics.test.ts` | Must (F17) |
| AC 5: Monday weeks, range-clipped | 2026-11-05..12 gives buckets `2026-11-02` and `2026-11-09`. A click on 2026-11-03 (outside the range) is not counted. | integration | Proposed: `test/integration/analytics.test.ts` | Must (F17) |
| AC 6: month buckets on UTC boundaries | A click at 11-30T23:59:59Z counts in November; 12-01T00:00:00Z counts in December. | integration | Proposed: `test/integration/analytics.test.ts` | Must (F17) |
| AC 7: interval defaults, caps, bounds | `resolveRange` unit table: 92 days gives `day`, 93 `week`, 731 `week`, 732 `month`; `day` over 400 days passes and over 401 days gives `RANGE_TOO_LARGE`; `year` gives `INVALID_RANGE`; `from=1999-12-31` and `to` = today + 367 give `INVALID_RANGE`, while `2000-01-01` and today + 366 pass (boundaries). An integration case checks `timeZone: "UTC"`. | unit + integration | Proposed: `test/unit/resolve-range.test.ts`, `test/integration/analytics.test.ts` | Must (F17) |
| AC 7a: default `from` clamped to `to` | A link created 11-10, `?to=2026-11-05`: 200 with `from: "2026-11-05"` and all zeros. | unit | Proposed: `test/unit/resolve-range.test.ts` | Must (F20) |
| AC 8: top referrers | 12 hosts with tied counts plus direct clicks. At most 10 entries; ordered by clicks descending, then host ascending, with `null` last among ties. Direct clicks appear as `host: null`. | integration | Proposed: `test/integration/analytics.test.ts` | Must (F18) |
| AC 9: countries sum to total | Clicks with `DE`, `US` and `NULL`. ISO codes, `null` for Unknown, and the sum equals `totalClicks`. | integration | Proposed: `test/integration/analytics.test.ts` | Must (F19) |
| AC 10: one range, consistent sums | A property-style loop over about 20 random ranges on a fixed dataset: timeline sum = total; country sum = total; referrer sum ≤ total, and = total when there are ≤ 10 hosts. | integration | Proposed: `test/integration/analytics.test.ts` | Must (F20) |
| AC 11: invalid ranges | `from > to`, `2026-13-01`, `2026-02-30` and `abc` each give 400 `INVALID_RANGE`. `from == to` gives 200 (boundary). | unit + integration | Proposed: `test/unit/resolve-range.test.ts` | Must (F20) |
| AC 12: defaults from creation date and clock | No parameters: `from` = the link's UTC creation date, and `to` = the fake clock's date. Created at 23:30Z, the date is that UTC day. | unit | Proposed: `test/unit/resolve-range.test.ts` | Must (F20) |
| AC 13: aggregates and raw agree across purge | A range covering rolled-up days and today. Ground truth is computed from raw clicks. The body is equal before rollup, after rollup, and after dropping the oldest raw partition. | integration | Proposed: `test/integration/analytics.test.ts` | Must (F20) |
| AC 14: one read-only snapshot | Statement recorder: `BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY`, the watermark read, the four aggregate statements on the same client, then `COMMIT`. Fail on any `INSERT`, `UPDATE` or `DELETE`. | integration | Proposed: `test/integration/analytics.test.ts` | Must (F20) |
| AC 15: `totalClicksFor` matches | Live links: equals the endpoint's full-life total. Expired and deleted links: equals a direct `count(*) WHERE NOT is_bot`. The recorded raw query has both `clicked_at >=` and `<` bounds. | integration | Proposed: `test/integration/analytics.test.ts` | Must (F5) |
| AC 16: schemas, camelCase, `no-store` | Route options declare 200, 400, 404, 429 and 500. A recursive key check on a response finds no `snake_case` keys. 200, 400 and 404 responses all carry `Cache-Control: no-store`. | integration | Proposed: `test/integration/analytics.test.ts` | Must (F23) |
| AC 17: names and assumption comments | Manual review: files exist; tests are named `F16:` to `F20:`; comments cite the interval defaults, the 400-bucket cap, the top-10 tie-break and bot exclusion. | manual | Proposed: review checklist | n/a (rules TEST-2, COMP-2) |

Test data and prerequisites:
- A fixed click dataset, `test/fixtures/analytics-dataset.ts` *(new)*: one link with clicks spread across 2026-10..11, 12 referrer hosts, three countries plus null, and a few bots. AC 4 to 13 share it, so their expected values are written once.
- RFC-006's rollup and retention functions, called directly to move data from raw to aggregate (AC 13).

## RFC-008: Delete and List

Features: F4, F5. Prerequisites: RFC-002 (token issued at create), RFC-003 (redirect for "still redirects"), RFC-007 (`totalClicksFor`, analytics 404).

| Criterion | Test | Level | Exists? | Priority |
|---|---|---|---|---|
| AC 1: delete with the token | `DELETE` with `Bearer <token>` gives 204 with an empty body. Afterwards the redirect and analytics both give 404. | integration | Proposed: `test/integration/delete-url.test.ts` | Must (F4) |
| AC 2: missing, malformed or wrong token gives 403 | No header, `Bearer`, `Bearer x`, and another link's token each give 403 `FORBIDDEN` with identical bodies. The link still gives 302 afterwards. | security | Proposed: `test/integration/delete-url.test.ts` | Must (F4) |
| AC 3: 404 cases change nothing | Unknown, already deleted, expired (with its correct token) and `a-b` each give 404 `NOT_FOUND` with identical bodies. A row snapshot is unchanged. | integration | Proposed: `test/integration/delete-url.test.ts` | Must (F4) |
| AC 4: soft delete, code never reissued | After delete, the row exists with `deleted_at` set and the clicks count is unchanged. Creating the same alias gives 409 `ALIAS_TAKEN`. | integration | Proposed: `test/integration/delete-url.test.ts` | Must (F4) |
| AC 5: bearer parsing | `bearer <t>` is accepted. `Bearer  <t>` (two spaces), `Token <t>` and two `Authorization` headers each give 403. | security | Proposed: `test/integration/delete-url.test.ts` | Must (F4) |
| AC 6: timing-safe compare; no token in logs or URL | A spy on `crypto.timingSafeEqual` sees two 32-byte buffers. With the real logger config, fail if either token appears in any line from create or delete (including `link_deleted`). `?token=<t>` and a JSON body `{"token":"<t>"}` without a header each give 403. | security | Proposed: `test/integration/delete-url.test.ts` | Must (F4) |
| AC 7: listing disabled without an admin token | Admin token unset, and set to `""`: `GET /api/v1/urls` gives 403 with any bearer token, and also with `?limit=0` (auth runs before validation, so 400 fails the test). | security | Proposed: `test/integration/list-urls.test.ts` | Must (F5) |
| AC 8: admin token required; item shape | Token set: no header or a wrong token gives 403; the right one gives 200. Each item's keys are exactly `code, shortUrl, destination, createdAt, expiresAt, totalClicks`. Fail on any `token` or `hash` key. | security | Proposed: `test/integration/list-urls.test.ts` | Must (F5) |
| AC 9: limit bounds | Default is 50; 1 and 100 are accepted; 0, 101 and `1.5` give 400 `VALIDATION_FAILED`. | integration | Proposed: `test/integration/list-urls.test.ts` | Must (F5) |
| AC 10: keyset pagination and bad cursors | 120 links: pages of 50, 50 and 20, newest first; the last page has `nextCursor: null`; the union of codes has exactly 120 with no duplicates. Insert a link between page fetches and check that nothing is skipped or repeated. Cursors `!!!`, base64url(`abc`), base64url(`0`) and base64url(`9223372036854775808`) give 400 `INVALID_CURSOR`. | integration | Proposed: `test/integration/list-urls.test.ts` | Must (F5) |
| AC 11: deleted hidden, expired shown | A deleted link is absent; an expired link is present with its `expiresAt`. | integration | Proposed: `test/integration/list-urls.test.ts` | Must (F5) |
| AC 12: list totals match | Live links: `totalClicks` equals the analytics full-life total. Expired: equals a direct non-bot `count(*)`. | integration | Proposed: `test/integration/list-urls.test.ts` | Must (F5) |
| AC 13: weak admin token warns | A 10-character token: listing works, `admin_token_weak` is logged once at startup, and the line does not contain the token. The variable is in all three lists (OPS-4 test). | unit + integration | Proposed: `test/unit/config.test.ts`, `test/unit/config-lists.test.ts` | Must (F5) |
| AC 14: schemas incl. 429; list GET never writes | Route options declare every status, including 429. The statement recorder shows no write during `GET /api/v1/urls`. | integration | Proposed: `test/integration/list-urls.test.ts` | Must (F5) |
| AC 15: names and assumption comments | Manual review: files exist; tests are named `F4:` and `F5:`; comments cite existence-before-token, newest-first, the unsigned cursor and the weak-token warning. | manual | Proposed: review checklist | n/a (rules TEST-2, COMP-2) |

Test data and prerequisites:
- A helper that creates N links with increasing `created_at` (fake clock) and returns their tokens.
- `LINKSNIP_ADMIN_TOKEN` set per test via `buildApp({ config })`, not `process.env` (ARCH-6).

## RFC-009: Web UI

Features: F9, F25, F26, F27 (Must); F29 (Should). Prerequisites: RFC-002 (`createShortUrl`), RFC-003 (404 page, redirect headers), RFC-005 (`blocklistStatus`), RFC-007 (`getAnalytics`).

| Criterion | Test | Level | Exists? | Priority |
|---|---|---|---|---|
| AC 1: form, labels, works without JS | Integration: `GET /` has URL (required), alias and expiry inputs, each with a `<label for>`, in a `form method="post" action="/shorten"`. E2E with `javaScriptEnabled: false`: submitting a URL shows the created page. | integration + e2e | Proposed: `test/integration/web-shorten.test.ts`, `test/e2e/shorten.spec.ts` | Must (F25) |
| AC 2: created page; token never in the URL | It shows the short URL, destination, UTC expiry, token and warning text, and an analytics link; `Cache-Control: no-store`. E2E: after submit, fail if `page.url()` contains the token. | integration + e2e | Proposed: `test/integration/web-shorten.test.ts`, `test/e2e/shorten.spec.ts` | Must (F25) |
| AC 3: copy button per browser | Chromium (clipboard permission granted): after clicking, the clipboard text equals the short URL. Firefox and WebKit: after clicking, the input's text is selected (`selectionStart` 0, `selectionEnd` = length). JS disabled: the button is not visible. | e2e | Proposed: `test/e2e/shorten.spec.ts` | Must (F25) |
| AC 4: every failure re-renders with status, values and message | Table over INVALID_URL (including a 2,049-character URL), SELF_LINK, BLOCKLISTED_URL (fake checker), ALIAS_TAKEN, ALIAS_RESERVED, INVALID_ALIAS and INVALID_EXPIRATION. For each: the status equals the service error's status, the submitted values are in the inputs, the RFC's message is present, and the field's `aria-describedby` points to the message element's `id`. | integration | Proposed: `test/integration/web-shorten.test.ts` | Must (F25) |
| AC 5: "not checked" notice | No-op checker: the created page contains the exact "This URL was not checked against a malware blocklist." `"clean"`: the notice is absent. | integration | Proposed: `test/integration/web-shorten.test.ts` | Must (F7) |
| AC 6: datetime-local is UTC | `2026-12-31T23:59` is stored as `…T23:59:00Z`, and `…T23:59:30` as `…T23:59:30Z`. A blank expiry gives no expiry and "Never expires". The label contains "UTC". | integration | Proposed: `test/integration/web-shorten.test.ts` | Must (F25) |
| AC 7: no validation in web routes | Fail if any `src/routes/web/` file imports `validation.ts` or `RESERVED_ALIASES`, or contains a regex literal. A fixture with each violation must fail. | unit | Proposed: `test/unit/web-routes-no-validation.test.ts` | Must (F21) |
| AC 8: analytics page content | It shows the total, a `<canvas>` plus a `<table>` with the same bucket count and values, "Direct / none" for null hosts, country names with "Unknown" for null, "All times UTC" and the bot note. | integration | Proposed: `test/integration/web-analytics.test.ts` | Must (F26) |
| AC 9: GET filter, pre-filled; error mode | With no query, the form is pre-filled with the resolved `from`, `to` and `interval`. Submitting a range updates the total and all three tables consistently. An invalid range gives 400 with the message and the submitted values, and fails if a total, table or canvas is rendered. | integration + e2e | Proposed: `test/integration/web-analytics.test.ts`, `test/e2e/analytics.spec.ts` | Must (F26) |
| AC 10: not-found page | Unknown, deleted and expired codes give 404 with the `not-found.eta` content. | integration | Proposed: `test/integration/web-analytics.test.ts` | Must (F26) |
| AC 11: Chart.js only on analytics; JS budget; CSP | `/` has no `chart.umd` script; the analytics page loads it from `/static/vendor/`. `js-budget.test.ts` gzips (level 9) every script on `/` and fails above 10,240 bytes. A parse of all page templates' output fails on an inline `<script>` body or any `on*=` attribute. The CSP is unchanged from RFC-001. | integration | Proposed: `test/integration/js-budget.test.ts` | Must (F27) |
| AC 12: escaping on rendered pages | Destination `https://example.com/?q=<script>alert(1)</script>` is created via the form; a raw `<script>alert(1)</script>` `referrer_host` is inserted directly in the database. On the created and analytics pages, `innerText` contains the literal string, the HTML source contains it only as `&lt;script&gt;`, and the `script` elements are exactly the page's own `src` scripts. No dialog listener is used. | security (e2e) | Proposed: `test/e2e/analytics.spec.ts`, `test/integration/web-analytics.test.ts` | Must (F9) |
| AC 13: no raw output; `safeHref` | `views-lint` fails on `<%~` other than `include`. A `safeHref` unit table: `https://x` gives an anchor; `javascript:x` and `data:x` give plain text. | unit | Proposed: `test/unit/views-lint.test.ts` | Must (F9) |
| AC 14: journeys in three engines; axe clean | Shorten and View Analytics journeys pass in Chromium, Firefox and WebKit. An axe scan with the four WCAG tags on `/`, the created page, the analytics page and the not-found page fails on any violation. | e2e | Proposed: `test/e2e/shorten.spec.ts`, `test/e2e/analytics.spec.ts` | Must (F27) |
| AC 15: no horizontal scroll at 360 px | For each page above plus the error states: `scrollWidth <= 360`. | e2e | Proposed: `test/e2e/responsive.spec.ts` | Must (F27) |
| AC 16: page-load budget | Chromium with the RFC's CDP throttling profile: `loadEventEnd` for `/` under 2,000 ms, as the median of 5 runs (assumption: median, to reduce flakiness without loosening the bound). | performance (e2e) | Proposed: `test/e2e/page-load.spec.ts` | Must (F27) |
| AC 17: keyboard-only journey with visible focus | Tab through the fields, type, and press Enter to submit; the created page appears. Every focused element has a computed `outline-style` that is not `none` or a non-`none` `box-shadow`. Error states contain text, not only colour. | e2e | Proposed: `test/e2e/keyboard.spec.ts` | Must (F27) |
| AC 18: noindex headers and meta | The analytics page has `X-Robots-Tag: noindex` and `<meta name="robots" content="noindex">`; redirect 302 and 404 responses have `X-Robots-Tag: noindex`. | integration | Proposed: `test/integration/web-analytics.test.ts` | Should (F29) |
| AC 19: new routes reserved | `shorten` and `analytics` are in `RESERVED_ALIASES`. The RFC-001 route test passes, and an alias `Shorten` gives `ALIAS_RESERVED`. | integration | Proposed: `test/integration/reserved-routes.test.ts` | Must (F2) |
| AC 20: names and assumption comments | Manual review: files exist; tests are named `F25:` and so on; comments cite the UTC-append, throttling, CSRF and non-linked-referrer assumptions. | manual | Proposed: review checklist | n/a (rules TEST-2, COMP-2) |

Test data and prerequisites:
- Playwright runs against a server built with `buildApp` on a random port and a Testcontainers database, with `FakeUrlChecker` and `FakeGeoLookup` (TEST-4).
- The analytics dataset fixture from RFC-007 is reused, so page numbers can be checked against API numbers.
- Playwright's bundled engines are not "the last two versions of Chrome, Firefox, Safari and Edge" (F27). See Manual testing gaps.

## RFC-010: Rate Limiting and Client IP

Features: F8. Prerequisites: RFC-002 (create), RFC-003 (redirect), RFC-009 (`renderShortenForm`).

| Criterion | Test | Level | Exists? | Priority |
|---|---|---|---|---|
| AC 1: 100 per minute, then 429 | 100 API requests from one IP: none is 429. Request 101 gives 429 with `Retry-After` (a positive integer) and `RATE_LIMITED` in the error body. | integration | Proposed: `test/integration/rate-limit.test.ts` | Must (F8) |
| AC 2: one shared budget | 60 `POST /api/v1/urls` + 40 analytics GETs + 1 `POST /shorten`: the 101st request is 429. | integration | Proposed: `test/integration/rate-limit.test.ts` | Must (F8) |
| AC 3: per-IP budgets; window resets | A second IP gets a fresh budget. With `rateLimitWindowMs = 500`, after a 600 ms wait the first IP succeeds again. | integration | Proposed: `test/integration/rate-limit.test.ts` | Must (F8) |
| AC 4: rate-limited form re-render | The 101st `POST /shorten` gives 429 with `Retry-After`, the submitted values in the inputs, and "Too many requests". An E2E check confirms the message is visible. | integration + e2e | Proposed: `test/integration/rate-limit.test.ts`, `test/e2e/shorten-rate-limit.spec.ts` | Must (F25) |
| AC 5: redirect budget separate; HEAD counts | After the API budget is exhausted, 1,000 redirects from the same IP all give 302. With `LINKSNIP_REDIRECT_RATE_LIMIT=10`: 5 GET + 5 HEAD succeed, and the 11th request gives 429 with `Retry-After`, the `rate-limited.eta` page and the text "10 requests per minute", and no click row. | integration | Proposed: `test/integration/rate-limit.test.ts` | Must (F8) |
| AC 6: exempt paths | With both limits set to 5: 200 requests each to `/health`, `/static/css/site.css`, `/docs`, `/` and `/analytics/{code}` never give 429. | integration | Proposed: `test/integration/rate-limit.test.ts` | Must (F8) |
| AC 6a: unmatched API paths count | API limit 5: the 6th `/api/v1/nope` gives 429 (and the first 5 give 404). | integration | Proposed: `test/integration/rate-limit.test.ts` | Must (F8) |
| AC 7: forged XFF ignored without trusted proxies | From `203.0.113.5` with a different forged `X-Forwarded-For` on each request: the budget is exhausted at 101. | security | Proposed: `test/integration/rate-limit.test.ts` | Must (F8) |
| AC 8: trusted proxy honoured | `10.0.0.0/8` trusted: requests from `10.0.0.2` with XFF `198.51.100.7` and `198.51.100.8` have separate budgets. Also checked: from untrusted `192.0.2.1`, the same headers share one budget. | security | Proposed: `test/integration/rate-limit.test.ts` | Must (F8) |
| AC 9: invalid proxy list; never `trustProxy: true` | An entry like `not-an-ip` makes startup exit naming `LINKSNIP_TRUSTED_PROXIES`. The built app's `trustProxy` option is never `true` (checked for unset, one CIDR and several CIDRs). | unit | Proposed: `test/unit/config.test.ts` | Must (F8) |
| AC 10: XFF header read nowhere else | Case-insensitive grep for `x-forwarded-for` across `src/`, excluding `src/logger.ts`. A fixture violation must fail. | unit | Proposed: `test/unit/client-ip-usage.test.ts` | Must (F8) |
| AC 11: one `rate_limited` log line per window | 5 rejections give exactly 1 `rate_limited` line with the budget and route and without the IP. The first rejection of the next window logs again. | integration | Proposed: `test/integration/rate-limit.test.ts` | Must (F8) |
| AC 12: variables, README, validation | The OPS-4 test passes; README phrase checks for trusted proxies, per-instance limits and "load testing only". `a,,b`, `REDIRECT_RATE_LIMIT=0` and `API_RATE_LIMIT=1.5` each make startup exit naming the variable. | unit | Proposed: `test/unit/config.test.ts`, `test/unit/config-lists.test.ts`, `test/unit/readme-sections.test.ts` | Must (F8) |
| AC 13: names and assumption comments | Manual review: tests are named `F8:`; comments cite the shared budget, unlimited GET pages and IPv6 keying (OQ-6). | manual | Proposed: review checklist | n/a (rules TEST-2, COMP-2) |

Test data and prerequisites:
- `inject({ remoteAddress })` for per-IP tests. An injected window (`deps.rateLimitWindowMs`) keeps the tests fast (ARCH-9).
- IPv6 keying (per full address, an RFC-010 assumption) has no AC. A proposed extra row in `rate-limit.test.ts`: `2001:db8::1` and `2001:db8::2` get separate budgets, and `::ffff:203.0.113.5` shares a budget with `203.0.113.5` (assumption, follows RFC-003's IPv4-mapped handling). It is marked as beyond the ACs.

## RFC-011: OpenAPI, Swagger UI and API Completeness

Features: F21, F23, F24, F32 (API-latency half). Prerequisites: RFC-002, RFC-004 (load harness), RFC-007, RFC-008, RFC-010 (429 declared).

| Criterion | Test | Level | Exists? | Priority |
|---|---|---|---|---|
| AC 1: generated, valid OpenAPI 3.1 | `GET /docs/json` validates against the vendored OpenAPI 3.1 meta-schema with Ajv. A grep shows no `openapi*.json` or `.yaml` is loaded by `src/` (the committed snapshot is read only by tests). | contract | Proposed: `test/integration/openapi-contract.test.ts` | Must (F23) |
| AC 2: exactly four operations, fully described | Operation set = {create, delete, list, analytics}. Each has request schemas, every status including 429, `ErrorBody` on every 4xx and 5xx, tags and a summary. `security` is present on delete and list only. | contract | Proposed: `test/integration/openapi-contract.test.ts` | Must (F23) |
| AC 3: routes, spec and responses agree | Fail if a `/api/v1/` route or declared status is missing from the document, or if the document has an operation with no route. Replay recorded requests for the success and error paths of each operation and validate every real response against its documented schema. | contract | Proposed: `test/integration/openapi-contract.test.ts` | Must (F23) |
| AC 4: operation descriptions | Phrase check per operation: "not idempotent", "shown once", the `blocklistStatus` values, "UTC", "inclusive", "bots excluded", "Retry-After". | contract | Proposed: `test/integration/openapi-contract.test.ts` | Must (F23) |
| AC 5: Swagger UI renders under CSP | Chromium opens `/docs` and sees exactly four operations. Fail on any `securitypolicyviolation` event or a CSP console error, or on any request to a host other than the instance. Every response across the route table lacks `'unsafe-inline'`. `/docs` is never 429 (covered with RFC-010 AC 6). | e2e | Proposed: `test/e2e/docs.spec.ts` | Must (F24) |
| AC 6: UI–API parity metadata | Fail if any route lacks `config.kind`, if a `web` route lacks `apiEquivalent`, or if an `apiEquivalent` names no registered `api` route. A test-only route without `apiEquivalent` must make it fail. | integration | Proposed: `test/integration/api-parity.test.ts` | Must (F21) |
| AC 7: versioned prefix; JSON system routes | Every `kind:"api"` route starts with `/api/v1/`. Injecting each GET `system` route shows `application/json` only on `/health` and `/docs/json`. | integration | Proposed: `test/integration/api-parity.test.ts` | Must (F21) |
| AC 8: compatibility snapshot | Against `docs/openapi.json`: each breaking change in the Versioning list (operation removed, status removed, property removed, renamed or retyped, enum value removed, request field newly required, constraint tightened) has a fixture pair and must fail. Additive fixture pairs must pass and print the differences. | contract | Proposed: `test/integration/api-compat.test.ts` | Must (F21) |
| AC 9: API p95 < 200 ms per endpoint | `load/api.js` runs at 50 requests/s for 5 minutes on the 10M seed and fails on any non-2xx. `server-latency.ts` fails unless the p95 of each of create, delete, list and analytics is separately under 200 ms. The per-endpoint split is unit-tested with a synthetic log where one endpoint is at 201 ms and the rest are fast: it must fail. | performance | Proposed: `load/api.js`, `load/server-latency.ts`, `test/unit/server-latency.test.ts` *(new, from RFC-004)* | Must (F32) |
| AC 10: release verdict run committed | Manual release checklist: `load/results/<date>-<sha>/` holds the API run and RFC-004's redirect and durability verdict runs for the same commit. `RESULT.md` states rate, mix, checker and hardware. This needs the reference host. | manual | Proposed: release checklist | Must (F32) |
| AC 11: names and assumption comments | Manual review: tests are named `F21:`, `F23:`, `F24:`, `F32:`; comments cite 50 requests/s, the API-only spec scope and the snapshot guard. | manual | Proposed: review checklist | n/a (rules TEST-2, COMP-2) |

Test data and prerequisites:
- The vendored OpenAPI 3.1 meta-schema, and `ajv` as a devDependency (named by RFC-011 under STACK-4).
- Fixture pairs of small OpenAPI documents for AC 8.
- The load run uses the no-op checker and makes the rate limits inert (`LINKSNIP_API_RATE_LIMIT` override, RFC-010). See the NFR-8 conflict under Artifact conflicts.

## RFC-012: Docker Deployment and Operator Docs

Features: F30 (Must); F35 backup docs (Should). Prerequisites: RFC-001, RFC-003, RFC-005, RFC-006, RFC-008, RFC-009, RFC-010.

| Criterion | Test | Level | Exists? | Priority |
|---|---|---|---|---|
| AC 1: cold install healthy in < 300 s | `scripts/deploy-smoke.sh` steps 0 to 11 on the reference host. It fails if `/health` is not 200 within 300 s of `up`, or if any functional step fails (create gives 201 `"unchecked"`; list gives 403; the redirect gives 302 with a browser UA; analytics `totalClicks == 1` with a null country; `/` and `/docs` give 200). The time, bandwidth and image size go into `RESULT.md`. Guard checks: without `LINKSNIP_SMOKE_DESTROY=yes` it exits before any `docker` command (stub `docker` on `PATH` and assert it was not called), and every compose call uses `-p linksnip-smoke`. The timing run itself is manual because it needs the reference host and a ≥ 100 Mbps link. | deployment + manual | Proposed: `scripts/deploy-smoke.sh`, `test/unit/deploy-smoke-guard.test.ts` *(new)* | Must (F30) |
| AC 2: CI smoke on main | The CI job `deploy-smoke` runs the script with `LINKSNIP_SMOKE_DESTROY=yes` and no time assertion on every push to main. Parse `ci.yml` to check the trigger and the variable. | deployment | Proposed: `.github/workflows/ci.yml` job `deploy-smoke` | Must (F30) |
| AC 3: data survives restart; backup round-trip | Smoke steps 9 and 10: after `down` and `up` the link still gives 302. The README's exact backup and restore commands, extracted from the README by the script rather than copied, restore a state where the second link is 404 and the first is 302. | deployment | Proposed: `scripts/deploy-smoke.sh` | Should (F35) |
| AC 4: safe defaults with no optional variables | The smoke run without `.env` covers the HTTP-visible defaults. The extended `loadConfig` test asserts every value in the Safe defaults table. | unit + deployment | Proposed: `test/unit/config.test.ts`, `scripts/deploy-smoke.sh` | Must (F30) |
| AC 5: README sections and phrases | Fail if any of the 10 headings is missing, or any key phrase: `docker compose up`, the exact backup and restore commands, "design target", "non-commercial", the GeoLite2 attribution sentence, the retention variable names, and a secret column in the Configuration table. | unit | Proposed: `test/unit/readme-sections.test.ts` | Must (F30) |
| AC 6: no Compose v1 command | Fail if `docker-compose` appears in `README*.md`, `scripts/`, `load/`, `.github/` or `compose*.yaml`. PRD.md, RULES.md, RFCs and the test itself are excluded. A fixture with the string must fail. | unit | Proposed: `test/unit/no-compose-v1.test.ts` | Must (F30) |
| AC 7: GeoLite2 attribution | The README contains the sentence. Integration: the footer of `/` contains it with a license key configured (fake downloader) and not without one. | unit + integration | Proposed: `test/unit/readme-sections.test.ts`, `test/integration/web-shorten.test.ts` | Must (F13) |
| AC 8: config lists complete | The OPS-4 test passes with every variable from RFC-001 to RFC-010. | unit | Proposed: `test/unit/config-lists.test.ts` | Must (F30) |
| AC 9: test names | Manual review: the three tests are named `F30:`. | manual | Proposed: review checklist | n/a (rule TEST-2) |

Test data and prerequisites:
- Docker on the CI runner and on the reference host. The smoke script destroys only the `linksnip-smoke` project and must never be run without the opt-in variable.
- A fresh-install timing needs a cold cache. Run it on the reference host, not a developer laptop with images already pulled.

## Summary

Counts are taken from the tables above. "Rows" is the number of planned tests (one per criterion). "Automated" counts rows with at least an automated part. "Manual only" counts rows with no automated test.

| RFC | Criteria | Rows (tests planned) | Automated | Manual only | Partly manual |
|---|---|---|---|---|---|
| RFC-001 | 33 | 33 | 32 | 1 (AC 30) | 2 (AC 4, AC 29) |
| RFC-002 | 25 | 25 | 24 | 1 (AC 24) | 0 |
| RFC-003 | 25 | 25 | 24 | 1 (AC 24) | 0 |
| RFC-004 | 8 | 8 | 5 | 3 (AC 5, 6, 7) | 1 (AC 8) |
| RFC-005 | 10 | 10 | 9 | 1 (AC 10) | 0 |
| RFC-006 | 15 | 15 | 14 | 1 (AC 13) | 0 |
| RFC-007 | 18 | 18 | 17 | 1 (AC 17) | 0 |
| RFC-008 | 15 | 15 | 14 | 1 (AC 15) | 0 |
| RFC-009 | 20 | 20 | 19 | 1 (AC 20) | 0 |
| RFC-010 | 14 | 14 | 13 | 1 (AC 13) | 0 |
| RFC-011 | 11 | 11 | 9 | 2 (AC 10, 11) | 0 |
| RFC-012 | 9 | 9 | 8 | 1 (AC 9) | 1 (AC 1) |
| **Total** | **203** | **203** | **188** | **15** | **4** |

Existing tests: 0. Proposed: all 203 rows.

The 15 manual-only criteria are of two kinds:
- **Review conventions (11)**: test naming (TEST-2), file existence, and assumption comments (COMP-2). RFC-001 AC 30, RFC-002 AC 24, RFC-003 AC 24, RFC-005 AC 10, RFC-006 AC 13, RFC-007 AC 17, RFC-008 AC 15, RFC-009 AC 20, RFC-010 AC 13, RFC-011 AC 11, RFC-012 AC 9. They are judgments about code, checked during `/review-rfc`.
- **Reference-hardware and process steps (4)**: RFC-004 AC 5 (load README usability), AC 6 (verdict run labelling), AC 7 (stop for the OQ-7 decision), and RFC-011 AC 10 (release run committed).

## Manual testing gaps

What the automated tests above cannot establish, and who checks it when:

1. **Reference-host performance and durability (F32, NFR-1, NFR-3, NFR-8, NFR-9).** k6 scripts decide pass or fail, but they only count when run on the 2 vCPU / 4 GB fsync-honouring host with a separate generator. Run them before each release (RFC-004 AC 6, RFC-011 AC 10). CI cannot do this.
2. **Five-minute first deployment (NFR-7).** It needs a cold cache and a ≥ 100 Mbps link (RFC-012 AC 1). CI runs the script without the time bound.
3. **Real browsers (F27).** F27 says "last two versions of Chrome, Firefox, Safari and Edge". Playwright's bundled Chromium, Firefox and WebKit (TEST-7) are not real Safari, and they are one version each. Before release, run the two journeys by hand in the current and previous Safari (macOS and iOS) and Edge. Optionally, add Playwright's `msedge` and `chrome` channels in CI.
4. **Accessibility beyond axe (F27, WCAG 2.1 AA).** axe finds only part of WCAG failures. Before release, do one manual pass with a screen reader (VoiceOver or NVDA) on the Shorten and Analytics journeys. Check that the error announcements, the token warning and the chart's table equivalent are read in a sensible order, and that the page zooms to 200% without loss.
5. **Mid-range phone load time (F27).** RFC-009 AC 16 uses CDP throttling in desktop Chromium as a proxy. Check `/` once on a real mid-range Android phone.
6. **Real Safe Browsing provider (F7).** Tests never call Google (TEST-4). With a real key, create links to Google's published test URLs (`https://testsafebrowsing.appspot.com/s/malware.html` and `/s/phishing.html`). Expect `BLOCKLISTED_URL`, and a clean URL to give `"clean"`. This confirms the request format against the live API.
7. **Real GeoLite2 download (F13).** With a real MaxMind account and key, confirm the first download, the swap and a correct country for a known public IP. Then check the attribution in the footer.
8. **Behind a real reverse proxy (F8).** Run the instance behind nginx or Caddy with `LINKSNIP_TRUSTED_PROXIES` set. Confirm that the rate limit keys on the real client and that a forged `X-Forwarded-For` from outside has no effect.
9. **README usability (COMP-3, F30).** Phrase tests prove the sentences exist, not that an operator can follow them. Someone who did not write it should follow the README from a clean machine once before release.

## Artifact conflicts and interpretations

Order of authority: PRD.md > FEATURES.md > RULES.md > RFCs > this plan. Each item says what this plan tests and what should be corrected.

1. **HEAD records no click (RFC-003 AC 4) vs PRD FR-8 ("on each redirect").** Already flagged in RFCS.md item 11. This plan tests the RFC behavior, so that the test exists whichever way the decision goes. If the user rules for FR-8, AC 4's assertion flips to "HEAD creates one row". **Flag FR-8** (unchanged).
2. **NFR-8 measured with the no-op checker (RFC-011 AC 9) vs PRD NFR-8 ("all endpoints").** Already flagged in RFCS.md item 12. This plan tests the RFC's reading. With a real Safe Browsing key, create can wait up to 2 s, which this test does not see. **Flag NFR-8** (unchanged).
3. **F14 "both periods operator-configurable" vs RULES PRIV-3.** RFC-006 follows FEATURES.md (higher authority) with an opt-in aggregate purge. RFC-006 AC 8 tests that reading. **Flag PRIV-3** (unchanged from RFCS.md item 2).
4. **F12 "every click whose redirect was answered is present" vs RFC-003 AC 12 (a 302 sent after a 2 s insert timeout).** F12 itself allows a failed write to be logged rather than block the redirect, so the RFC does not contradict FEATURES.md. But a timed-out insert that later fails is a lost click that NFR-9 forbids. RFC-004 AC 4 counts any such loss as a failure, and the durability run reports `click_write_timeout` lines so that a loss is explained, not excused. **Flag for RFC-004 Implementation Notes** if timeouts appear under load. Not a new conflict, but no other document says it.
5. **F27 browser list vs RULES TEST-7 engines.** TEST-7 (Chromium, Firefox, WebKit) is how F27 is automated. It does not cover real Safari or Edge, or "last two versions". This plan follows TEST-7 for automation and lists the rest as manual gap 3. **Flag TEST-7** to say it is a proxy for F27's list, or to add the `msedge` channel.
6. **Self-link with a non-default port (RFC-002 AC 18).** SEC-1 compares the host "with any default port removed", so `lnk.example.com:8443` is *not* a self-link under SEC-1, although it may reach the same instance. This plan records the behavior in a test rather than guessing (assumption). **Flag SEC-1** for a decision.

## Assumptions

Each is also marked (assumption) where it is used above.

- Rows proving rule-only criteria (tooling, layering, naming) carry priority "n/a (rule ...)", because they belong to no feature and this plan does not invent a MoSCoW rating. They still gate their RFC.
- Where an RFC names no test file, this plan proposes one, marked *(new)*: `tooling.test.ts`, `sql-placement.test.ts`, `no-placeholders.test.ts`, `maxmind-geo.test.ts`, `jobs.test.ts`, `server-latency.test.ts`, `load-config.test.ts`, `deploy-smoke-guard.test.ts`, `test/fixtures/user-agents.ts`, `test/fixtures/analytics-dataset.ts`, and the CI jobs `image-check` and `compose-check`. An implementer may merge them into the RFC's named files.
- RFC-001 AC 27 and 28 run as CI jobs until RFC-012's smoke script exists.
- RFC-009 AC 16 uses the median of 5 runs, to reduce flakiness without changing the 2,000 ms bound.
- RFC-006 AC 2: exactly 00:15Z is tested, and the result is recorded against the RFC's "after 15 minutes" wording rather than assumed.
- RFC-010: an IPv6 row beyond the ACs is proposed, with IPv4-mapped addresses sharing the IPv4 budget.
- Timing tolerances (RFC-003 AC 12: 1.9 to 2.5 s; RFC-006 AC 5a: 1.8 to 3 s; RFC-001 AC 15: under 100 ms) are this plan's choice. The RFCs say "about".

## Self-check

- **Counts recounted from the tables**: 33 + 25 + 25 + 8 + 10 + 15 + 18 + 15 + 20 + 14 + 11 + 9 = 203 rows. Manual-only rows: 1+1+1+3+1+1+1+1+1+1+2+1 = 15. Automated rows: 203 − 15 = 188, which matches the column sum (32+24+24+5+9+14+17+14+19+13+9+8 = 188). Partly manual: RFC-001 AC 4 and 29, RFC-004 AC 8, RFC-012 AC 1 = 4. Each RFC's criteria count was checked against its Acceptance Criteria list, including sub-criteria: RFC-001 has 30 plus 22a, 22b and 25a; RFC-002 has 24 plus 13a; RFC-003 has 24 plus 6a; RFC-006 has 13 plus 4a and 5a; RFC-007 has 17 plus 7a; RFC-010 has 13 plus 6a. A first draft of the summary said 13 for RFC-010; the mechanical recount found 14 and the tables were corrected. A script also compared the AC numbers in each RFC with the AC numbers in its section here: all 12 sections match exactly, with no criterion missing or invented.
- **Priorities** were taken from FEATURES.md, not reassigned: F15, F29 and F35 rows are Should; F24 stays Must (OQ-11 demotion not taken); every other feature row is Must.
- **Cross-references checked**: F7 is the blocklist (RFC-005, RFC-009 AC 5), F13 GeoLite2 (RFC-012 AC 7), F14 privacy (RFC-001 AC 25, RFC-003 AC 14), F21 API parity (RFC-002 AC 22, RFC-009 AC 7), F23 OpenAPI (RFC-002 AC 23, RFC-007 AC 16), F30 configuration (the OPS-4 rows), F35 migrations and backup (RFC-001 AC 11, RFC-012 AC 3). RFCS.md conflict items 2, 7, 11 and 12 are cited by number and say what is quoted.
- **Section headings** follow `## RFC-[ID]: [title]` with the titles from the RFCS.md index, in implementation order (RFC-001 to RFC-012).
- **Priority labels checked mechanically**: every `Should (Fn)` label names F15, F29 or F35, each of which is Should in FEATURES.md. Every `Must (Fn)` label names a Must feature.
- `trace-check.py` was run on the project (`python3 skills/test-strategy/scripts/trace-check.py .`): 28 requirements, 44 features, 95 rules, 12 RFCs; **0 failures, 3 warnings**. All three warnings are expected and already explained in RFCS.md: F28 and F34 (Could) are deferred, and F32 is deliberately split across RFC-004 and RFC-011. The earlier warning that TEST-STRATEGY.md is missing is gone.
