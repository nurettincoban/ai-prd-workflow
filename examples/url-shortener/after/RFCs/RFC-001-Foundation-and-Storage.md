# RFC-001: Project Foundation and Storage

**Features**: F22, F31, F33, F35
**Depends on**: none
**Rules**: STACK-1, STACK-2, STACK-3, STACK-5, STACK-6, ARCH-1, ARCH-2, ARCH-3, ARCH-6, ARCH-8, ARCH-9, NAME-1, NAME-2, NAME-3, NAME-4, NAME-5, DATA-1, DATA-2, DATA-3, DATA-4, DATA-5, DATA-8, DATA-9, API-1, API-3, API-4, SEC-6, SEC-10, SEC-13, PRIV-1, PRIV-4, PERF-3, ERR-1, ERR-2, ERR-5, ERR-6, LOG-1, LOG-2, LOG-3, TEST-1, TEST-2, TEST-3, OPS-1, OPS-2, OPS-3, OPS-4, COMP-1, COMP-2, SEC-3, STACK-4, TEST-4
**Complexity**: High

## Summary

Everything later RFCs build on: the TypeScript/Fastify project skeleton, validated configuration, the PostgreSQL pool, versioned migrations that run before the server listens, the `short_urls` and month-partitioned `clicks` tables, the consistent JSON error body, the logger with IP redaction, the `/health` endpoint, graceful shutdown, the Docker image and `compose.yaml`, and CI. No user-facing link feature is built here; RFC-002 adds the first one.

Why the storage design comes first: every performance requirement (NFR-1, NFR-3, NFR-6) and every analytics feature depends on the `short_urls` / `clicks` schema (PRD-REVIEW critical path), so it is fixed once, here.

## Technical Approach

### Components and data flow

- `src/server.ts` exports `startServer(options?: { env?: NodeJS.ProcessEnv; migrationsDir?: string }): Promise<RunningServer>` and, when run as the entry point, calls it. Sequence: `loadConfig(options.env)` → create `pg.Pool` → `runMigrations(config.databaseUrl, logger, migrationsDir)` → `ensureClickPartitions(db, clock)` → `buildApp(deps)` → `app.listen()` → start the job scheduler → install the `SIGTERM`/`SIGINT` handler. Any failure before `listen` logs an `event` and exits with code 1 (ERR-5). `startServer` exists so tests can inject an environment and a migrations directory (cold read: there was no seam for AC 8 and AC 11).
- Module system (cold read): ESM. `package.json` has `"type": "module"`; `tsconfig.json` uses `"module": "NodeNext"`, `"moduleResolution": "NodeNext"`, `"rootDir": "."`, `"outDir": "dist"`, so `src/` compiles to `dist/src/` and `migrations/` to `dist/migrations/`. The `build` script runs `tsc` and then copies `src/views/` to `dist/src/views/`; `static/` is not compiled and is served from `<app root>/static/`.
- `src/app.ts`: `buildApp(deps: AppDeps): FastifyInstance`. `AppDeps` = `{ config, pool, clock }` in this RFC; later RFCs add `urlChecker` (RFC-002/005), `geo` and `botDetector` (RFC-003). Tests call `buildApp` with fakes (TEST-4). `buildApp` registers, in order: the error handler and API not-found handler, `@fastify/helmet` (SEC-10), `@fastify/static` for `static/` at `/static/`, `@fastify/view` with Eta (`autoEscape: true`, SEC-6), then the route modules.
- `src/config.ts`: the only reader of `process.env` (ARCH-6); validates against a TypeBox schema and returns a frozen `Config`.
- `src/clock.ts`: `export interface Clock { now(): Date }` and `export const systemClock: Clock`. The only place `Date.now()` / argument-less `new Date()` appear (ARCH-9).
- `src/db/`: `pool.ts` (creates the single pool, PERF-3, with `connectionTimeoutMillis: 1000` so a saturated or unreachable database fails fast instead of hanging requests), `migrate.ts` (node-pg-migrate programmatic runner), `health.ts` (`pingDatabase(pool)` → `SELECT 1`), `partitions.ts` (create and list monthly `clicks` partitions), `advisory-lock.ts` (`withAdvisoryLock(pool, key, fn)` using `pg_try_advisory_lock`).
- `src/services/partition-maintenance.ts`: `ensureClickPartitions(db, clock, monthsAhead = 2)`.
- `src/scheduler.ts`: `startScheduler(jobs, logger)`. Each job is `{ name, intervalMs, runAtStart, run }`. A job with `runAtStart: true` runs once immediately; every job then runs every `intervalMs` with `setInterval(...).unref()`. A job that throws is logged with `event: "job_failed"` and its name, and the scheduler keeps going. Each run is wrapped in `withAdvisoryLock`, so two instances on one database never run the same job at once. Registered here: `ensure-click-partitions`, every hour, `runAtStart: false` (because `startServer` already ran it before `listen`).
- `src/db/advisory-lock.ts` (cold read: the key and the semantics were unstated): `withAdvisoryLock(pool, jobName, fn)` checks out one dedicated client, runs `SELECT pg_try_advisory_lock(hashtext($1))` with the job name, and **skips** the run (log `job_skipped_locked`, debug level) when the lock is not acquired; it does not wait. Otherwise it runs `fn`, then calls `pg_advisory_unlock(hashtext($1))` in `finally` on the **same** client and releases that client. A session-level lock is released automatically if the process dies.
- `src/errors.ts`: `ApiError`, the error-code catalog and `registerErrorHandling(app)`.
- `src/services/reserved-aliases.ts`: `export const RESERVED_ALIASES: readonly string[]` (lower-case), initially `["api", "docs", "static", "health"]`. Every later RFC that adds a top-level route adds its segment here (ARCH-8).
- `src/routes/health.ts`: `GET /health`. (ARCH-1 names no folder for routes that are neither API, page nor redirect; health sits beside `redirect.ts` at `src/routes/` top level.)

### Configuration (this RFC's variables)

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `LINKSNIP_DATABASE_URL` | yes | -- | PostgreSQL connection string |
| `LINKSNIP_PUBLIC_HOST` | yes | -- | Public host[:port] short links are served on, e.g. `lnk.example.com` |
| `LINKSNIP_PUBLIC_SCHEME` | no | `https` | `http` or `https`, used to build `shortUrl` (assumption: needed because SEC-1 names only a host) |
| `LINKSNIP_PORT` | no | `3000` | Listen port |
| `LINKSNIP_BIND_ADDRESS` | no | `0.0.0.0` | Listen address |
| `LINKSNIP_DB_POOL_SIZE` | no | `20` | `pg.Pool` `max` (PERF-3) |
| `LINKSNIP_LOG_LEVEL` | no | `info` | pino level: `fatal`..`trace` |
| `LINKSNIP_DB_PASSWORD` | compose only | `linksnip` in `compose.yaml` | Used by `compose.yaml` to set the Postgres password and build `LINKSNIP_DATABASE_URL`; not read by `src/config.ts` |
| `LINKSNIP_HTTP_PORT` | compose only | `3000` | Host port that `compose.yaml` publishes; not read by `src/config.ts` |

Unknown keys (cold read): compose passes `.env` into the app, so the compose-only keys reach the process. `loadConfig` ignores the two compose-only keys. For any other `LINKSNIP_*` key not in the schema it logs one warning, `config_unknown_variable`, naming the key, and carries on. Startup does not fail, so a documented `.env` never crashes the app, but a typo is still visible. (assumption)

`LINKSNIP_PUBLIC_HOST` is lower-cased and a default port (`:80` for http, `:443` for https) is stripped at load time, so SEC-1's comparison is a plain string equality.

Pseudocode:

```
loadConfig(env = process.env):            # the only process.env read in src/ (ARCH-6)
  raw = pick every key starting with "LINKSNIP_", minus the compose-only keys
  unknown = keys not in ConfigSchema → returned as config.unknownKeys (logged by startServer once the logger exists)
  coerce numeric strings to numbers (lists are parsed by RFC-010)
  if !Value.Check(ConfigSchema, raw):
     throw new ConfigError(["Invalid configuration: <VARIABLE>: <reason>", ...])
  apply defaults; normalize PUBLIC_HOST; return Object.freeze(config)

startServer:
  try config = loadConfig(env)
  catch ConfigError e: process.stderr.write(e.lines.join("\n") + "\n"); process.exit(1)
     # the logger does not exist yet; process.stderr.write is not console.* (LOG-1)
```

### Error handling (F22)

Error body for every 4xx/5xx from an `/api/` route (API-3):

```json
{ "error": { "code": "ALIAS_TAKEN", "message": "The alias 'promo' is already in use." } }
```

`src/errors.ts` exports `class ApiError extends Error { constructor(readonly statusCode: number, readonly code: ErrorCode, message: string) }` and `ERROR_CODES`, a `const` object of every code with its status. Codes defined in this RFC:

| Code | Status | When |
|---|---|---|
| `INVALID_BODY` | 400 | Body is not valid JSON, or the content type is not `application/json` on a route that takes a JSON body |
| `VALIDATION_FAILED` | 400 | A TypeBox schema rejects params, querystring or body; the message names the first failing field |
| `NOT_FOUND` | 404 | Unknown `/api/` route, or (later RFCs) unknown/deleted/expired code |
| `INTERNAL_ERROR` | 500 | Anything not an `ApiError` |

Later RFCs add their codes to this catalog in the same file (ERR-1).

```
errorHandler(error, request, reply):
  if error instanceof ApiError: send(error.statusCode, {error:{code, message}})
  else if error.validation: send(400, VALIDATION_FAILED, first validation message)
  else if error.code in (FST_ERR_CTP_INVALID_MEDIA_TYPE, FST_ERR_CTP_EMPTY_JSON_BODY,
                         FST_ERR_CTP_INVALID_CONTENT_LENGTH) or error is a JSON SyntaxError:
       send(400, INVALID_BODY, "Request body must be valid JSON.")   # Fastify's default is 415/400 with its own shape
  else if error.code == FST_ERR_CTP_BODY_TOO_LARGE:      # bodyLimit is 16 KiB (assumption: a create body is < 3 KB)
       send(400, INVALID_BODY, "Request body is too large.")   # API-4 has no 413
  else if error.statusCode is a 4xx (any other Fastify client error, e.g. a malformed URL or a bad header):
       send(400, VALIDATION_FAILED, generic message)          # API-4 lists 400 for invalid input
  # 429 cannot arise before RFC-010. RFC-010 adds a branch here that formats it as RATE_LIMITED.
  else:
       request.log.error({event:"unhandled_error", err: error, route: request.routeOptions.url})
       send(500, INTERNAL_ERROR, "Internal server error.")   # never the stack or SQL (ERR-1)
```

For non-`/api/` requests the same handler renders the HTML error page `src/views/error.eta` with the status and a generic message instead of JSON (the web UI RFC-009 styles it). `setNotFoundHandler`: `/api/*` → `NOT_FOUND` JSON; otherwise the HTML 404 page `src/views/not-found.eta`.

### Data model (migration `migrations/<timestamp>_create-short-urls-and-clicks.ts`)

```sql
CREATE TABLE short_urls (
  id                     bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  code                   text COLLATE "C" NOT NULL,
  destination            text NOT NULL,
  is_alias               boolean NOT NULL,
  management_token_hash  bytea NOT NULL,              -- SHA-256, 32 bytes (SEC-4, filled by RFC-002)
  blocklist_status       text NOT NULL CHECK (blocklist_status IN ('clean','unchecked')),
  created_at             timestamptz NOT NULL,
  expires_at             timestamptz NULL,
  deleted_at             timestamptz NULL,
  CONSTRAINT short_urls_code_key UNIQUE (code)       -- DATA-3: the guarantee, not a prior SELECT
);
CREATE INDEX short_urls_live_idx ON short_urls (id) WHERE deleted_at IS NULL;   -- keyset listing, RFC-008

CREATE TABLE clicks (
  id             bigint GENERATED ALWAYS AS IDENTITY,
  short_url_id   bigint NOT NULL REFERENCES short_urls(id),
  clicked_at     timestamptz NOT NULL,
  referrer       text NOT NULL DEFAULT '',      -- full Referer header, truncated to 2,048 chars
  referrer_host  text NOT NULL DEFAULT '',      -- lower-cased host, '' when none or unparseable
  user_agent     text NOT NULL DEFAULT '',      -- truncated to 1,024 chars
  country        char(2) NULL,                  -- ISO 3166-1 alpha-2; NULL = Unknown (PRIV-2)
  is_bot         boolean NOT NULL DEFAULT false,
  PRIMARY KEY (short_url_id, clicked_at, id)
) PARTITION BY RANGE (clicked_at);
-- No column holds an IP address or any part of one (DATA-9, PRIV-1).
```

The primary key leads with `short_url_id, clicked_at`, which is also the index every analytics query needs (DATA-5). No default partition: a row whose month has no partition fails to insert, which RFC-003 logs and survives (ERR-3); the hourly job keeps the current month and the next two months created, so this happens only if the job has not run for two months.

Partitions are named `clicks_yYYYYmMM` (e.g. `clicks_y2026m11`) and cover `[first day of month 00:00 UTC, first day of next month 00:00 UTC)`.

```
ensureClickPartitions(db, clock, monthsAhead=2):
  for m in month(clock.now() in UTC) .. +monthsAhead:
     CREATE TABLE IF NOT EXISTS clicks_yYYYYmMM PARTITION OF clicks
        FOR VALUES FROM ('YYYY-MM-01T00:00:00Z') TO ('<next month>-01T00:00:00Z')
     -- partition bounds are built from validated integers, never from input; table names are
     -- formatted from integers only (the single documented exception to "values as parameters",
     -- DATA-8: DDL identifiers cannot be bound parameters; assert /^clicks_y\d{4}m\d{2}$/ before use)
```

Partitions for past months are not created; clicks are written with `clicked_at = clock.now()`.

### Health (F33)

`GET /health` → `pingDatabase` → `200 {"status":"ok"}` or `503 {"status":"unavailable"}` (ERR-5). The 1-second bound works like this: the pool's `connectionTimeoutMillis: 1000` caps the wait for a connection, and `pingDatabase` races `SELECT 1` against a 1,000 ms timer (`Promise.race`), treating the timer as failure. A late query result is ignored. The route is not under `/api/v1/` and is not rate limited (SEC-9). Its completion log is written at `debug` (see Logging), so container health probes do not flood the logs.

**Restart on failure** (cold read: `restart: unless-stopped` does not restart a container that is merely unhealthy). `src/services/health-watchdog.ts` pings the database every 10 s. After 6 consecutive failures (60 s) it logs `health_watchdog_exit` and starts the normal shutdown with exit code 1. Docker's restart policy then restarts the container, which is how F33's "a failed instance is restarted" is met. (assumption)

### Logging

`src/logger.ts` exports the pino options passed to Fastify: JSON lines, level from config, `redact` paths exactly as PRIV-1 lists (tokens travel only in `Authorization`, API-5, which that list already redacts). Field names (cold read): Fastify's built-in request logging is turned off (`disableRequestLogging: true`). An `onResponse` hook writes exactly one line per request:

```json
{"level":30,"time":"...","event":"request_completed","method":"GET","route":"/:code","statusCode":302,"responseTimeMs":3.1}
```

`route` is the route pattern (`request.routeOptions.url`), or `"<not-found>"` when no route matched. The path and query string are not logged; `route` is enough for LOG-3 and keeps codes and parameters out of logs. The line is written at `info`, except for route `/health`, which is written at `debug`. App log calls always include `event` (LOG-2). RFC-004 and RFC-011 compute latency from these exact fields.

### Migrations (F35)

- `src/db/migrate.ts`: `runMigrations(databaseUrl, logger)` calls node-pg-migrate's programmatic `runner` with `dir` = the compiled migrations directory (`dist/migrations` in the image, `migrations/` via tsx in dev), `direction: "up"`, `migrationsTable: "pgmigrations"`, and a lock so concurrent starts serialize. Failure → log `migration_failed`, exit 1.
- `npm run migrate` runs the same function from the command line.
- Migrations are never edited after merge (DATA-1); each later RFC that changes the schema adds a new file.

### Graceful shutdown (ERR-6)

```
on SIGTERM or SIGINT (once):
  log event "shutdown_started"
  stop scheduler timers
  await app.close()      # stops accepting, waits for in-flight requests incl. their click inserts
  await pool.end()
  exit(0)
  if not done within 10 s: log "shutdown_timeout", exit(1)
```

`compose.yaml` sets `stop_grace_period: 15s` so Docker waits longer than the app's own timeout.

### Docker and Compose

- `Dockerfile`: stage `build` from `node:26.13.1-alpine` (STACK-1): `npm ci`, `npm run build` (tsc to `dist/`, copies `src/views/` to `dist/src/views/`); stage `runtime` from the same image: `npm ci --omit=dev`, copies `dist/`, `static/`, views; `USER node`; `CMD ["node","dist/src/server.js"]` (OPS-3).
- `compose.yaml` (OPS-1): services `db` (`postgres:18.7-alpine`, `POSTGRES_USER=linksnip`, `POSTGRES_DB=linksnip`, `POSTGRES_PASSWORD=${LINKSNIP_DB_PASSWORD:-linksnip}`, named volume `linksnip-db` mounted at `/var/lib/postgresql` (OPS-2). Cold read: from 18 on, the official image keeps its data in a version-specific directory under `/var/lib/postgresql`, so the volume is mounted at the parent, not the older `/var/lib/postgresql/data`. AC 28's persistence check proves the mount works, healthcheck `pg_isready -U linksnip`, no published port) and `app` (built from the Dockerfile, `depends_on: db: condition: service_healthy`, `LINKSNIP_DATABASE_URL=postgres://linksnip:${LINKSNIP_DB_PASSWORD:-linksnip}@db:5432/linksnip`, `LINKSNIP_PUBLIC_HOST=${LINKSNIP_PUBLIC_HOST:-localhost:3000}`, `LINKSNIP_PUBLIC_SCHEME=${LINKSNIP_PUBLIC_SCHEME:-http}`, `env_file` `.env` marked `required: false`, published port `${LINKSNIP_HTTP_PORT:-3000}:3000`, healthcheck `wget -qO- http://127.0.0.1:3000/health || exit 1` every 10 s, `restart: unless-stopped`).
- The defaults let `docker compose up` work on a fresh checkout with no `.env` (F30's "safe defaults"); the default database password is acceptable only because the database port is not published (README says to set `LINKSNIP_DB_PASSWORD` for any real deployment).

### Configuration lists (OPS-4)

`README.md` gets a `## Configuration` section with a table (variable, required, default, meaning) and `.env.example` lists every variable. `test/unit/config-lists.test.ts` parses the `ConfigSchema` keys, the `.env.example` keys and the README table's first column and fails if the three sets differ (with `LINKSNIP_DB_PASSWORD` and `LINKSNIP_HTTP_PORT` allowed in `.env.example` and README only, marked "compose only"). Every later RFC that adds a variable updates all three; this test enforces it.

## File Structure

```
package.json  package-lock.json  tsconfig.json  eslint.config.mjs  .prettierrc.json
vitest.config.ts  .gitignore  .dockerignore  .env.example  README.md
Dockerfile  compose.yaml  .github/workflows/ci.yml
src/server.ts  src/app.ts  src/config.ts  src/clock.ts  src/errors.ts  src/logger.ts  src/scheduler.ts
src/db/pool.ts  src/db/migrate.ts  src/db/health.ts  src/db/partitions.ts  src/db/advisory-lock.ts
src/services/partition-maintenance.ts  src/services/reserved-aliases.ts  src/services/health-watchdog.ts
src/routes/health.ts
src/views/layout.eta  src/views/error.eta  src/views/not-found.eta
static/css/site.css
migrations/<timestamp>_create-short-urls-and-clicks.ts
test/integration/helpers/database.ts      # starts postgres:18.7-alpine via @testcontainers/postgresql, runs migrations
test/unit/config.test.ts  test/unit/config-lists.test.ts  test/unit/clock-usage.test.ts
test/integration/migrations.test.ts  test/integration/partitions.test.ts
test/integration/errors.test.ts  test/integration/health.test.ts  test/integration/reserved-routes.test.ts
test/integration/shutdown.test.ts  test/integration/startup.test.ts  test/integration/health-watchdog.test.ts
test/unit/logger.test.ts  test/fixtures/failing-migrations/<timestamp>_fail.ts
```

## Implementation Considerations

- **Version compatibility** (RULES Technology Stack, "Not verified"): the first `npm ci && npm test` in this RFC confirms the pinned versions work together. If a pair is incompatible, take the newest compatible version from the registry and update the RULES.md table in the same change (STACK-4) -- never a remembered number.
- **TypeScript migrations**: the runner always loads compiled JavaScript from `dist/migrations`, in production (where the image has no devDependencies, OPS-3), in dev, and in tests. Vitest's `globalSetup` runs `tsc` once before the integration tests, and `npm run migrate` builds first. This gives one loading path instead of two (cold read: `dist/migrations` vs `migrations/`).
- **Partition DDL** cannot use bound parameters for identifiers or bounds; build them only from integers derived from the clock and assert the name pattern (DATA-8's intent is preserved: no request value reaches SQL text).
- **Testing**: integration tests use a real PostgreSQL container (TEST-1); a `test/unit/clock-usage.test.ts` greps `src/` and fails if `Date.now(` or `new Date()` appears outside `src/clock.ts` (ARCH-9), and if `console.` or `Math.random` appears anywhere in `src/` (LOG-1, SEC-3). Coverage thresholds of 80% lines/branches for `src/services/` and `src/db/` are set in `vitest.config.ts` (TEST-3).
- **CI** (`.github/workflows/ci.yml`): `npm ci`, `npm run lint` (ESLint strict + Prettier check, STACK-6), `npm run typecheck`, `npm test` with coverage. Docker is available on GitHub-hosted Ubuntu runners for Testcontainers.
- **Security**: helmet's CSP `script-src 'self'` (SEC-10) is set here so every later page inherits it. Cold read: helmet's defaults send HSTS and `upgrade-insecure-requests`, which would break the default `http://localhost:3000` deployment. So both are enabled only when `LINKSNIP_PUBLIC_SCHEME=https` and are disabled for `http`. `.env` is git-ignored (SEC-13).
- **Backups** (F35/OPS-2): this RFC creates the named volume. The backup and restore README section is written in RFC-012, AC 5.
- **Compliance**: no click data is written yet; DATA-9 is enforced from the first migration.
- **Third-party**: only the stack in RULES.md.

## Acceptance Criteria

**Project and tooling**
1. `package.json` pins every dependency exactly, sets `"type": "module"` and `"engines": {"node": ">=26.13.1 <27"}`, and defines scripts `build`, `start`, `dev` (tsx), `migrate`, `lint`, `typecheck`, `test`. Each script runs something real in this RFC (COMP-1); `test:e2e` and the `load:*` scripts are added by RFC-009 and RFC-004. `package-lock.json` is committed (STACK-1, STACK-3).
2. `tsconfig.json` has `"strict": true`; `src/`, `test/`, `migrations/` contain no `.js` files (STACK-2).
3. `eslint.config.mjs` uses typescript-eslint `strict` with `no-explicit-any` as an error; `.prettierrc.json` exists; `npm run lint` fails on any lint or format error (STACK-6).
4. `.github/workflows/ci.yml` runs lint, typecheck and tests with coverage on every push and pull request and fails if any step fails or coverage for `src/services/` or `src/db/` is below 80% lines or branches (TEST-3).
5. `.gitignore` lists `.env`, `node_modules/`, `dist/`, `coverage/`; `.dockerignore` excludes the same plus `.git/` (SEC-13).
6. `test/unit/clock-usage.test.ts` fails if `src/` contains `Date.now(`, an argument-less `new Date()` outside `src/clock.ts`, `console.`, `Math.random` or a `process.env` read outside `src/config.ts` (ARCH-6, ARCH-9, LOG-1, SEC-3).

**Configuration**
7. With all required variables valid, `loadConfig` returns the documented defaults for every optional variable in the table above.
8. A missing `LINKSNIP_DATABASE_URL` or `LINKSNIP_PUBLIC_HOST`, or an invalid value (e.g. `LINKSNIP_DB_POOL_SIZE=abc`, `LINKSNIP_PUBLIC_SCHEME=ftp`), makes `loadConfig` throw a `ConfigError` naming the variable (unit test). A child-process test that runs `node dist/src/server.js` with that environment sees a non-zero exit and the message on stderr (ARCH-6). An unknown `LINKSNIP_FOO=1` logs `config_unknown_variable` and does not stop startup. `LINKSNIP_DB_PASSWORD` and `LINKSNIP_HTTP_PORT` are ignored silently.
9. `LINKSNIP_PUBLIC_HOST=LNK.Example.com:443` with scheme `https` is normalized to `lnk.example.com`.
10. `README.md` has a `## Configuration` table and `.env.example` lists every variable; `test/unit/config-lists.test.ts` fails when a variable is in one of `ConfigSchema`, `.env.example`, README but not the others (OPS-4).

**Storage (F31) and migrations (F35)**
11. On startup the server runs pending migrations before `listen`, and a second start runs none. `startServer({ migrationsDir: <fixture dir containing a migration that throws> })` logs `migration_failed`, never listens, and exits non-zero (the test stubs `process.exit`) (DATA-1, ERR-5).
12. After migration, `short_urls` and the partitioned `clicks` table exist exactly as in the Data model section: `code` has `COLLATE "C"` and a unique constraint; inserting `abc1234` and `ABC1234` both succeed and a second `abc1234` fails with SQLSTATE `23505` (DATA-3); every time column is `timestamptz` (DATA-2). The columns of `clicks` read from `information_schema.columns` are exactly `id, short_url_id, clicked_at, referrer, referrer_host, user_agent, country, is_bot`, so no IP column can be added without failing this test (DATA-9).
13. `ensureClickPartitions` with a clock at 2026-11-15 creates `clicks_y2026m11`, `clicks_y2026m12`, `clicks_y2027m01`; running it twice is a no-op; a click with `clicked_at` 2026-12-31T23:59:59.999Z lands in `clicks_y2026m12` and one at 2027-01-01T00:00:00Z in `clicks_y2027m01` (DATA-5).
14. `EXPLAIN` of `SELECT ... FROM clicks WHERE short_url_id = 1 AND clicked_at >= '2026-11-01T00:00:00Z' AND clicked_at < '2026-12-01T00:00:00Z'`, with literal values so that pruning happens at plan time, lists only `clicks_y2026m11` (DATA-5).
15. `startServer` runs `ensureClickPartitions` before `listen`, and the scheduler runs it hourly after that. When two processes call `withAdvisoryLock` with the same job name at the same moment, one runs and the other logs `job_skipped_locked` and returns without waiting. A job that throws logs `job_failed` and runs again at its next interval.
16. Only files under `src/db/` import `pg` or contain SQL (ARCH-2); every SQL value is a bound parameter except the integer-derived partition DDL described above (DATA-8).
17. One `pg.Pool` is created per process with `max` = `LINKSNIP_DB_POOL_SIZE` (PERF-3).

**Errors (F22)**
18. A `POST` to a test route with body `{not json` and content type `application/json` returns 400 `{"error":{"code":"INVALID_BODY",...}}`; with content type `text/plain` it returns 400 `INVALID_BODY` (not 415); a schema-invalid body returns 400 `VALIDATION_FAILED` naming the field.
19. A handler throwing a plain `Error` returns 500 `{"error":{"code":"INTERNAL_ERROR","message":"Internal server error."}}` with no stack trace or SQL in the body, and logs `unhandled_error` (ERR-1).
20. `GET /api/v1/does-not-exist` returns 404 with the error body and code `NOT_FOUND`; every error response from an `/api/` route has exactly the shape `{error:{code,message}}` and `Content-Type: application/json` (API-3, API-4).
21. A non-`/api/` error or unknown path renders `error.eta` / `not-found.eta` as HTML with the right status and no internal detail.

**Health (F33) and operations**
22. `GET /health` returns 200 `{"status":"ok"}` when the database answers `SELECT 1`. With the database container paused, it returns 503 `{"status":"unavailable"}` in under 1.5 seconds (ERR-5). Its `request_completed` line is logged at `debug`.
22a. With the database paused, the health watchdog logs `health_watchdog_exit` after 6 failed pings (fake timers) and starts shutdown with exit code 1. In compose, `restart: unless-stopped` then restarts the container (F33).
22b. A body larger than 16 KiB returns 400 `INVALID_BODY`. Any other Fastify 4xx returns 400 `VALIDATION_FAILED` with the error body, never 500.
23. `RESERVED_ALIASES` contains `api`, `docs`, `static`, `health`; `test/integration/reserved-routes.test.ts` enumerates the app's registered routes and fails if any top-level path segment (other than route parameters such as `:code`) is missing from the list (ARCH-8).
24. Responses carry the helmet headers with CSP `script-src 'self'` and no `'unsafe-inline'` (SEC-10); Eta is configured with `autoEscape: true` explicitly (SEC-6).
25. Log lines are single-line JSON. A unit test logs an object that has every PRIV-1 redact path set, through the configured logger, and sees `[Redacted]` for each (it does not rely on headers simply not being logged). An integration test sends a request with `Authorization`, `Cookie`, `X-Forwarded-For` and `X-Real-IP` from `remoteAddress` `203.0.113.9` and finds none of those values, and not the IP, in any captured line (PRIV-1, PRIV-4). Each request produces exactly one `request_completed` line with `method`, `route`, `statusCode` and `responseTimeMs` (LOG-3).
25a. With `LINKSNIP_PUBLIC_SCHEME=http`, responses carry no `Strict-Transport-Security` header and the CSP has no `upgrade-insecure-requests`. With `https`, both are present.
26. On `SIGTERM` during an in-flight request, that request completes, the pool closes, and the process exits 0 (ERR-6); `test/integration/shutdown.test.ts` proves it with a deliberately slow test route.
27. `docker build` produces an image whose final stage has no devDependencies and runs as user `node` (OPS-3).
28. `docker compose up` on a fresh checkout with no `.env` starts `db` and `app`; `app` starts only after `db` is healthy; the `app` container becomes healthy via `/health`; data persists in the named volume `linksnip-db` across `docker compose down` / `up` (OPS-1, OPS-2, F33).
29. No `TODO`, `FIXME`, `XXX`, placeholder or not-implemented stub is merged (COMP-1); every assumption implemented here (e.g. `LINKSNIP_PUBLIC_SCHEME`) has a code comment citing this RFC (COMP-2).
30. Tests for this RFC's behaviors are named with their feature ID where one applies (`"F22: ..."`, `"F31: ..."`, `"F33: ..."`, `"F35: ..."`) (TEST-2).
