# RFC-012: Docker Deployment and Operator Documentation

**Features**: F30
**Depends on**: RFC-001, RFC-003, RFC-005, RFC-006, RFC-008, RFC-009, RFC-010
**Rules**: OPS-1, OPS-2, OPS-3, OPS-4, OPS-5, SEC-13, STACK-3, COMP-3, ERR-5, TEST-2, COMP-2, DATA-1
**Complexity**: Low

## Summary

Finishes F30: a single `docker compose up` (Compose v2, D2) on a fresh Docker install starts a working instance in under 5 minutes, every operator setting is documented in one place, and the instance starts with safe defaults when optional settings are absent. RFC-001 already built the image, `compose.yaml` and the configuration-list test; later RFCs added variables. This RFC verifies the whole set end to end, measures the first-deployment time, and completes the README's operator sections (COMP-3). It is last because it documents settings introduced by RFC-003, RFC-005, RFC-006, RFC-008 and RFC-010, and adds the GeoLite2 attribution to the RFC-009 page layout.

## Technical Approach

### Fresh-install smoke test

`scripts/deploy-smoke.sh` (bash; outside `src/`, so STACK-2 does not apply):

```
0. refuse to run unless LINKSNIP_SMOKE_DESTROY=yes; always use the dedicated project name: COMPOSE="docker compose -p linksnip-smoke"
   (cold read: the project name gives the smoke run its own volumes, so `down -v` can never touch a real
   deployment's linksnip-db volume)
1. $COMPOSE down -v; docker image rm -f linksnip-app:local postgres:18.7-alpine node:26.13.1-alpine; docker builder prune -af
   (a real cold start: nothing pulled, no build cache; compose.yaml names the app image linksnip-app:local)
1b. record bandwidth: time a `docker pull` of postgres:18.7-alpine and divide its compressed size by the time,
    then remove it again
2. t0 = now; $COMPOSE up -d --build
3. poll http://localhost:${LINKSNIP_HTTP_PORT:-3000}/health every 2 s until 200 (fail after 300 s)
4. t1 = now; print elapsed; fail if t1 - t0 > 300 s           (NFR-7: under 5 minutes)
5. POST /api/v1/urls {"url":"https://example.com/"} → expect 201 and blocklistStatus "unchecked"; GET /api/v1/urls → expect 403 (no admin token);
   app log contains blocklist_disabled and no geoip download event
6. GET /<code> with redirects disabled and User-Agent "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
   (curl's default UA counts as a bot and would not be counted, RFC-003) → expect 302 to https://example.com/
7. GET /api/v1/urls/<code>/analytics → expect the RFC-007 field totalClicks == 1 and countries == [{country: null, clicks: 1}] (no GeoLite2 key)
8. GET / → 200 HTML; GET /docs → 200
9. $COMPOSE down (keep volume); $COMPOSE up -d; wait healthy; GET /<code> → still 302   (OPS-2)
10. backup round trip: run the README's exact backup command, create a second link, run the README's exact
    restore command, then check that the second link returns 404 and the first still returns 302 (OPS-2, F35)
11. $COMPOSE down -v
```

It runs with no `.env` file, which proves the safe defaults. The measured time is recorded on RFC-004's reference host in `load/results/<YYYY-MM-DD>-<sha>/RESULT.md`, together with the measured bandwidth. The 300 s target assumes at least 100 Mbps (assumption). A run on a slower link is recorded as such and does not count as a failure of NFR-7.

The CI job `deploy-smoke` runs the same script on a GitHub-hosted runner on every push to the main branch, with `LINKSNIP_SMOKE_DESTROY=yes` and without the 300 s assertion, because runner networks vary. It catches broken builds and defaults.

### Safe defaults (verified, not new)

| Setting | Absent → |
|---|---|
| `LINKSNIP_PUBLIC_HOST` / `_SCHEME` | compose supplies `localhost:3000` / `http` |
| `LINKSNIP_ADMIN_TOKEN` | listing disabled (403) |
| `LINKSNIP_SAFE_BROWSING_API_KEY` | blocklist check disabled; links `unchecked` |
| `LINKSNIP_GEOLITE2_LICENSE_KEY` | countries Unknown; no MaxMind request |
| `LINKSNIP_TRUSTED_PROXIES` | no proxy trusted |
| `LINKSNIP_REDIRECT_RATE_LIMIT` | 6,000/min |
| `LINKSNIP_CLICK_RETENTION_MONTHS` | 13 |
| `LINKSNIP_AGGREGATE_RETENTION_MONTHS` | unset: aggregates kept forever |
| `LINKSNIP_API_RATE_LIMIT` | 100/min |
| `LINKSNIP_DB_POOL_SIZE` | 20 (PERF-3) |
| `LINKSNIP_PORT` / `LINKSNIP_BIND_ADDRESS` / `LINKSNIP_LOG_LEVEL` | 3000 / 0.0.0.0 / info |
| `LINKSNIP_HTTP_PORT` | 3000 (compose only) |
| `LINKSNIP_GEOLITE2_DIR` | `/var/lib/linksnip/geoip` (volume `linksnip-geoip`) |
| `LINKSNIP_BOT_PATTERNS_FILE` | isbot's default list |
| `LINKSNIP_DB_PASSWORD` | `linksnip` (the database port is not published). This conflicts with SEC-13, which says secrets come only from the environment; it is kept so that `docker compose up` works with no setup. RFCS.md **flags SEC-13** (assumption). |

How each default is observed: the smoke script checks the HTTP-visible ones (blocklist `unchecked`, listing 403, country Unknown, no MaxMind request in the log). The rest (limits, retention, pool size, ports, log level) are covered by RFC-001 AC 7's `loadConfig` defaults test, extended to every variable in this table.

### README (operator guide)

Sections, each a criterion below:

- `## Quick start`: `git clone`, `docker compose up`, open `http://localhost:3000`. Uses `docker compose`, never `docker-compose` (OPS-1, D2), and says Docker Engine with the Compose v2 plugin is required.
- `## Configuration`: the table (already enforced by the OPS-4 test) with a "secret" column; secrets go in `.env` (git-ignored) or the orchestrator's secret store, never committed (SEC-13).
- `## Running behind a reverse proxy`: set `LINKSNIP_PUBLIC_HOST`, `LINKSNIP_PUBLIC_SCHEME=https`, `LINKSNIP_TRUSTED_PROXIES` (RFC-010).
- `## Malware and phishing check` and `## Privacy and data retention`: written by RFC-005 (its AC 9 lists the content) and RFC-006 (its AC 11 lists the content). `test/unit/readme-sections.test.ts` checks the key phrases from those two criteria.
- `## Country data (GeoLite2)`: how to obtain a MaxMind account ID and license key (both required, RFC-003). The database is fetched when the app starts, checked daily and refreshed when 7 days old, and kept in the `linksnip-geoip` volume, never baked into the image (OPS-5, whose wording RFCS.md flags). It also gives the attribution text: "This product includes GeoLite2 data created by MaxMind, available from https://www.maxmind.com." (MaxMind's published wording; assumption that it is current). The web UI footer shows the same text **only when a GeoLite2 license key is configured** (assumption: attribution is owed only when the data is used).
- `## Backups`: the names are those `compose.yaml` defines (RFC-001): service `db`, user `linksnip`, database `linksnip`, volume `linksnip-db`.
  - Back up: `docker compose exec -T db pg_dump -U linksnip -d linksnip -Fc > linksnip.dump`. `-T` disables the TTY, which would otherwise corrupt the binary dump.
  - Restore: `docker compose exec -T db pg_restore -U linksnip -d linksnip --clean --if-exists < linksnip.dump`.
  - The section warns that `docker compose down -v` deletes the volume and all data. Smoke step 10 runs these exact commands (OPS-2, F35).
- `## Upgrading`: pull, `docker compose up -d --build`; migrations run automatically before the server listens (DATA-1, F35); back up first.
- `## Availability`: the 99.9% uptime figure (NFR-2) is a design target for LinkSnip itself -- no single-request failure mode -- not a guarantee LinkSnip can make for an operator's deployment, which depends on their host, database and network (OQ-8, COMP-3, F32).
- `## Behavior notes`: HEAD requests and link previews (RFC-003), query strings on short links not forwarded, bots excluded from analytics, creation not idempotent.

## File Structure

```
scripts/deploy-smoke.sh
.github/workflows/ci.yml          (deploy-smoke job added)
README.md                         (sections above)
src/views/layout.eta              (GeoLite2 attribution in footer)
compose.yaml                      (start_period 30s, image name linksnip-app:local)
.env.example                      (verified)
test/unit/readme-sections.test.ts  test/unit/no-compose-v1.test.ts
load/results/<run>/RESULT.md      (first-deployment time)
```

## Implementation Considerations

- **Image size** drives the 5-minute budget: the alpine base and `npm ci --omit=dev` (OPS-3) keep it small; record the final image size in `RESULT.md`.
- **Health timing**: this RFC changes `compose.yaml` to set the app healthcheck's `start_period: 30s`, which allows for migrations on first start, and names the app image `linksnip-app:local`.
- **Compatibility**: Docker Engine with Compose v2 on Linux, macOS (Docker Desktop) and Windows (Docker Desktop, WSL2); the smoke script is bash and is run on Linux.
- **Third-party**: none new.

## Acceptance Criteria

1. `scripts/deploy-smoke.sh` on the reference host, with no `.env`, no images and no build cache, reaches a healthy `/health` in under 300 seconds on a link of at least 100 Mbps, and passes every functional step listed above (F30, NFR-7). The time, the measured bandwidth and the image size are recorded in `load/results/<YYYY-MM-DD>-<sha>/RESULT.md`. Without `LINKSNIP_SMOKE_DESTROY=yes` the script exits before touching anything, and it only ever uses the compose project `linksnip-smoke`.
2. The CI `deploy-smoke` job runs the script (without the time assertion) on every push to the main branch.
3. Data survives `docker compose down` and `up` (step 9), and the README's backup and restore commands round-trip (step 10) (OPS-2).
4. The instance starts and serves links with every optional variable absent. The smoke script observes the HTTP-visible defaults, and the extended `loadConfig` test asserts every other value in the Safe defaults table (F30).
5. `test/unit/readme-sections.test.ts` checks that the README has the headings Quick start, Configuration, Running behind a reverse proxy, Malware and phishing check, Privacy and data retention, Country data (GeoLite2), Backups, Upgrading, Availability and Behavior notes. It also checks these key phrases: `docker compose up`; the exact backup and restore commands; "design target" in Availability; "non-commercial"; the GeoLite2 attribution sentence; the retention variable names; and a secret column in the Configuration table (COMP-3, OPS-2, OPS-5).
6. `test/unit/no-compose-v1.test.ts` fails if the string `docker-compose` appears in `README*.md`, `scripts/`, `load/`, `.github/` or `compose*.yaml`. PRD.md, RULES.md, RFCs and the test file itself are excluded, because they quote the old command in order to forbid it (OPS-1, D2).
7. The GeoLite2 attribution appears in the README. It appears in the web UI footer when `LINKSNIP_GEOLITE2_LICENSE_KEY` is set and not otherwise.
8. The OPS-4 configuration-list test passes with every variable added by RFC-001 through RFC-010.
9. The Vitest tests `test/unit/readme-sections.test.ts`, `test/unit/no-compose-v1.test.ts` and the extended config-defaults test are named `"F30: ..."` (TEST-2).
