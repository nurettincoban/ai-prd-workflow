# RFCS: LinkSnip URL Shortener

Source: `PRD.md` (FR-1 to FR-19, NFR-1 to NFR-9, OQ-1 to OQ-15), `PRD-REVIEW.md` (H1-H5), `FEATURES.md` (F1-F44), `RULES.md` (95 rules).

This plan was written non-interactively: no person was available to answer questions. Where an RFC makes a choice no document settles, it is marked **(assumption)** in that RFC; the most consequential ones are collected under Assumptions below.

**How to implement**: run `/implement-rfc <id>` for each RFC (e.g. `/implement-rfc RFC-001`), then `/review-rfc <id>`. Those commands keep the Status column below current. No per-RFC implementation prompt files are generated: they would duplicate `/implement-rfc` and drift from it.

## Breakdown approach

The redirect path is the critical path (PRD-REVIEW): every performance requirement and every analytics feature depends on the `short_urls` / `clicks` schema, and the riskiest assumption in the PRD -- a durable click insert on every redirect inside 100 ms p95 at 1,000/s (OQ-7) -- can only be settled by measuring it. So the plan fixes storage first (RFC-001), builds the shortest route to a working redirect with click recording (RFC-002, RFC-003), and load-tests it immediately (RFC-004) before analytics, UI and documentation are built on top. Features are grouped by the code they share: one create service used by API and UI, one redirect handler, one analytics service, and so on. Integrations with third parties (Safe Browsing, GeoLite2) sit behind interfaces so the core works and tests without them.

## Product Type

PRD.md records **Web app + service/API**; this plan applies the checks of both.

Applied: authorization per resource (RFC-008 tokens), data model and migrations (RFC-001, RFC-006), accessibility, responsive layout and browser support (RFC-009), page-load budget (RFC-009, PERF-6), API contracts and versioning (RFC-002, RFC-007, RFC-008, RFC-011), authentication of destructive operations and rate limiting (RFC-008, RFC-010), idempotency and retries (RFC-002: creation is not idempotent, stated in the API docs; RFC-008: delete is idempotent in effect; RFC-005: no retry of the blocklist call), observability (request and event logs in RFC-001; metrics deferred, see F34), data retention and privacy (RFC-006), SLOs and scaling (RFC-004, RFC-011), SEO for public pages (RFC-009, F29).

Skipped, visibly:
- **Binary size** -- no client binary is shipped (PRD Product Type). Docker image size is recorded instead (RFC-012) because it drives the 5-minute deployment.
- **Offline sync** -- every operation needs the server.
- **Sessions / login security** -- no accounts in v1.0 (F36). With no cookies or ambient credentials, CSRF protection is not needed either (RFC-009, assumption).
- **Mobile app, library/SDK, CLI, data pipeline, game checks** -- not this product type.

## RFC index (implementation order)

| RFC | Title | Features | Depends on | Complexity | Status | Cold read |
|---|---|---|---|---|---|---|
| RFC-001 | [Project Foundation and Storage](RFCs/RFC-001-Foundation-and-Storage.md) | F22, F31, F33, F35 | none | High | Not started | Fable 5.2, 2026-11-15 -- findings fixed |
| RFC-002 | [Link Creation](RFCs/RFC-002-Link-Creation.md) | F1, F2, F3, F6 | RFC-001 | Medium | Not started | Fable 5.2, 2026-11-15 -- findings fixed |
| RFC-003 | [Redirect and Click Recording](RFCs/RFC-003-Redirect-and-Click-Recording.md) | F10, F11, F12, F13, F15 | RFC-001, RFC-002 | High | Not started | Fable 5.2, 2026-11-15 -- findings fixed |
| RFC-004 | [Redirect Load and Durability Tests](RFCs/RFC-004-Redirect-Load-and-Durability-Tests.md) | F32 (redirect, durability) | RFC-003 | High | Not started | Fable 5.2, 2026-11-15 -- findings fixed |
| RFC-005 | [Safe Browsing Blocklist](RFCs/RFC-005-Safe-Browsing-Blocklist.md) | F7 | RFC-002 | Medium | Not started | Fable 5.2, 2026-11-15 -- findings fixed |
| RFC-006 | [Click Rollup and Retention](RFCs/RFC-006-Click-Rollup-and-Retention.md) | F14 | RFC-001, RFC-003 | Medium | Not started | Fable 5.2, 2026-11-15 -- findings fixed |
| RFC-007 | [Analytics API](RFCs/RFC-007-Analytics-API.md) | F16, F17, F18, F19, F20 | RFC-003, RFC-006 | Medium | Not started | Fable 5.2, 2026-11-15 -- findings fixed |
| RFC-008 | [Delete and List](RFCs/RFC-008-Delete-and-List.md) | F4, F5 | RFC-002, RFC-003, RFC-007 | Medium | Not started | Fable 5.2, 2026-11-15 -- findings fixed |
| RFC-009 | [Web UI](RFCs/RFC-009-Web-UI.md) | F9, F25, F26, F27, F29 | RFC-002, RFC-003, RFC-005, RFC-007 | Medium | Not started | Fable 5.2, 2026-11-15 -- findings fixed |
| RFC-010 | [Rate Limiting and Client IP](RFCs/RFC-010-Rate-Limiting.md) | F8 | RFC-002, RFC-003, RFC-009 | Medium | Not started | Fable 5.2, 2026-11-15 -- findings fixed |
| RFC-011 | [OpenAPI, Swagger UI and API Completeness](RFCs/RFC-011-OpenAPI-and-API-Completeness.md) | F21, F23, F24, F32 (API latency) | RFC-002, RFC-004, RFC-007, RFC-008, RFC-010 | Medium | Not started | Fable 5.2, 2026-11-15 -- findings fixed |
| RFC-012 | [Docker Deployment and Operator Docs](RFCs/RFC-012-Deployment-and-Operator-Docs.md) | F30 | RFC-001, RFC-003, RFC-005, RFC-006, RFC-008, RFC-009, RFC-010 | Low | Not started | Fable 5.2, 2026-11-15 -- findings fixed |

12 RFCs: 3 High, 8 Medium, 1 Low complexity.

## Dependency table

| RFC | Predecessors (must be complete first) | Successors (declare it as a predecessor) |
|---|---|---|
| RFC-001 | none | RFC-002, RFC-003, RFC-006, RFC-012 |
| RFC-002 | RFC-001 | RFC-003, RFC-005, RFC-008, RFC-009, RFC-010, RFC-011 |
| RFC-003 | RFC-001, RFC-002 | RFC-004, RFC-006, RFC-007, RFC-008, RFC-009, RFC-010, RFC-012 |
| RFC-004 | RFC-003 | RFC-011 |
| RFC-005 | RFC-002 | RFC-009, RFC-012 |
| RFC-006 | RFC-001, RFC-003 | RFC-007, RFC-012 |
| RFC-007 | RFC-003, RFC-006 | RFC-008, RFC-009, RFC-011 |
| RFC-008 | RFC-002, RFC-003, RFC-007 | RFC-011, RFC-012 |
| RFC-009 | RFC-002, RFC-003, RFC-005, RFC-007 | RFC-010, RFC-012 |
| RFC-010 | RFC-002, RFC-003, RFC-009 | RFC-011, RFC-012 |
| RFC-011 | RFC-002, RFC-004, RFC-007, RFC-008, RFC-010 | none |
| RFC-012 | RFC-001, RFC-003, RFC-005, RFC-006, RFC-008, RFC-009, RFC-010 | none |

Dependency graph (an arrow means "is needed by"):

```
RFC-001 ──► RFC-002 ──► RFC-003 ──► RFC-004 ─────────────────────────────┐
   │           │           │                                              ▼
   │           │           ├──► RFC-006 ──► RFC-007 ──► RFC-008 ──────► RFC-011
   │           │           │                   │           │              ▲
   │           ├──► RFC-005 ─────────┐         │           │              │
   │           │                     ▼         ▼           │              │
   │           └───────────────────► RFC-009 ◄─┘           │              │
   │                                    │                  │              │
   │                                    └──► RFC-010 ──────┼──────────────┘
   │                                            │          │
   └──────────────────────────────────────────► RFC-012 ◄──┘   (also needs RFC-003, RFC-005, RFC-006, RFC-009)
```

## Roadmap

A solo implementer follows the numbers. A team can run branches in parallel once their predecessors are done:

| Phase | RFCs | Notes | PRD timeline |
|---|---|---|---|
| 1. Foundation | RFC-001 | Settles stack compatibility (`npm ci && npm test`), schema, migrations, CI | Week 1 |
| 2. Core path | RFC-002, then RFC-003 | First working short link and redirect with click recording | Week 1-2 |
| 3. Prove the hot path | RFC-004 ∥ RFC-005 ∥ RFC-006 | RFC-004 settles OQ-7; a failure here stops the plan for a decision before analytics are built on the write path | Week 2-3 |
| 4. Analytics and ownership | RFC-007, then RFC-008 | | Week 3-4 |
| 5. UI and abuse | RFC-009, then RFC-010 | RFC-009 can start as soon as RFC-007 and RFC-005 are done, in parallel with RFC-008 | Week 4-5 |
| 6. Contract and ship | RFC-011 ∥ RFC-012 | Release load-test run and fresh-install timing | Week 6 |

Critical path: RFC-001 → RFC-002 → RFC-003 → RFC-006 → RFC-007 → RFC-009 → RFC-010 → RFC-011.

The PRD's timeline puts custom aliases and expiration in week 5; this plan builds them in RFC-002 with generated codes because they are the same endpoint, the same insert and the same unique index, and splitting them would mean revising the create contract twice.

## Feature coverage

Every Must feature belongs to an RFC. Should and Could features are either scheduled or deferred below. Won't features (F36-F44) are not planned.

| Feature | Priority | RFC |
|---|---|---|
| F1 Create short URL with generated code | Must | RFC-002 |
| F2 Custom alias | Must | RFC-002 |
| F3 Expiration date-time | Must | RFC-002 |
| F4 Management token and delete | Must | RFC-008 (token issued and hashed by RFC-002 as part of F1) |
| F5 List short URLs (operator only) | Must | RFC-008 |
| F6 Destination URL validation | Must | RFC-002 |
| F7 Malware and phishing blocklist check | Must | RFC-005 (interface and no-op checker in RFC-002) |
| F8 Rate limiting | Must | RFC-010 |
| F9 Output escaping in the web UI | Must | RFC-009 (Eta auto-escape configured in RFC-001) |
| F10 Redirect with 302 | Must | RFC-003 (latency verified in RFC-004) |
| F11 404 for expired, deleted and unknown links | Must | RFC-003 |
| F12 Click recording | Must | RFC-003 (durability verified in RFC-004) |
| F13 Country geolocation | Must | RFC-003 |
| F14 Click data privacy and retention | Must | RFC-006 |
| F15 Bot and link-preview filtering | Should | RFC-003 (flag), RFC-007 (exclusion) -- scheduled |
| F16 Total click count | Must | RFC-007 |
| F17 Click timeline | Must | RFC-007 |
| F18 Top referrers | Must | RFC-007 |
| F19 Geographic breakdown | Must | RFC-007 |
| F20 Date-range filter | Must | RFC-007 |
| F21 REST API for all operations | Must | RFC-011 |
| F22 JSON format and consistent error body | Must | RFC-001 |
| F23 OpenAPI specification | Must | RFC-011 |
| F24 Swagger UI | Must | RFC-011 |
| F25 Shorten page | Must | RFC-009 (rate-limit message verified in RFC-010) |
| F26 Analytics page | Must | RFC-009 |
| F27 Web UI quality bars | Must | RFC-009 |
| F28 Delete from the web UI | Could | **Deferred** (below) |
| F29 Keep public pages out of search indexes | Should | RFC-009 -- scheduled |
| F30 Docker Compose deployment | Must | RFC-012 (image and compose file first built in RFC-001) |
| F31 Storage for 10M short URLs | Must | RFC-001 (verified at 10M rows in RFC-004) |
| F32 Performance verification | Must | RFC-004 (redirect, durability) and RFC-011 (API latency) -- deliberately split |
| F33 Health check endpoint | Must | RFC-001 |
| F34 Observability | Could | **Deferred** (below) |
| F35 Schema migrations and backup | Should | RFC-001 (migrations), RFC-012 (backup docs) -- scheduled; listed under RFC-001 |

Counts: 30 Must, all assigned; 3 Should (F15, F29, F35), all scheduled; 2 Could (F28, F34), both deferred; 9 Won't, not planned. 35 non-Won't features, 33 planned.

**Why F32 is split**: FEATURES.md says F32 "must run early against F10 and F12 to settle OQ-7", but its API-latency criterion needs endpoints that do not exist until RFC-007 and RFC-008. RFC-004 owns the harness, the redirect thresholds and the durability test; RFC-011 adds the API scenario and the release run. `trace-check.py` warns about the split; it is intended.

### Deferred

| Feature | Priority | Reason |
|---|---|---|
| F28 Delete from the web UI | Could | FR-18 names only the Shorten and View Analytics journeys; the Delete journey allows "the delete endpoint (or the UI)", so the API (RFC-008) satisfies it. Adding a UI form later is small (a POST form that passes the token to `deleteShortUrl`); the RFC that adds it must confirm that a POST body field is not one API-5 forbids, since API-5 bans tokens only where they end up in a URL. |
| F34 Observability (metrics) | Could | No PRD requirement names it. Structured JSON logs with `event` fields and per-request latency (RFC-001, LOG-2, LOG-3) already let operators count click-write failures, blocklist failures and rate-limit rejections and compute latency from logs. A metrics endpoint (e.g. Prometheus) would need a new dependency (STACK-4) and is left for after v1.0. |

## PRD-REVIEW High-impact findings

| Finding | Reflected in acceptance criteria |
|---|---|
| H1 -- 301 caching breaks tracking and expiry | RFC-003 AC 1 (302 + `Cache-Control: private, no-store`, never 301), AC 3 (repeat clicks both recorded), AC 6 (404 with `no-store`) |
| H2 -- anyone can delete or list every link | RFC-008 AC 1-2 (delete needs the management token; wrong token → 403 and the link still redirects), AC 7-8 (listing needs the admin token; disabled when unset) |
| H3 -- contradictory scale targets | RFC-001 AC 12-14 (indexed codes, month-partitioned clicks), RFC-004 AC 1-2 (load test seeded with 10M URLs, 10,000 active) |
| H4 -- click data is personal data, no retention | RFC-003 AC 14 (IP never stored or logged), RFC-006 AC 5 (13-month partition drop), AC 10 (end-to-end IP absence), AC 11 (privacy note) |
| H5 -- blocklist provider unchosen, licensing | RFC-005 AC 1-4 (Safe Browsing behind `UrlChecker`, disabled without a key, fail open), AC 9 (non-commercial terms documented) |

## Artifact conflicts and interpretations

Order of authority: PRD.md > FEATURES.md > RULES.md > RFCs. Each item says what was followed and what should be corrected.

1. **API path in PRD-REVIEW R2** (`DELETE /api/urls/{code}`) vs **RULES API-1** (`/api/v1/`). R2 is an example in a review, not a requirement; FEATURES.md F21 and RULES API-1 both say `/api/v1/`. Followed `/api/v1/`. No correction needed beyond noting R2's example predates the versioning decision.
2. **F14 "both periods operator-configurable"** vs **RULES PRIV-3** ("`click_daily` aggregates are never purged by it"). Followed FEATURES.md (higher authority): RFC-006 adds an opt-in aggregate purge, separate from the raw-retention job and off by default, which keeps PRIV-3's literal wording true. **Flag PRIV-3** for rewording so the two clearly agree.
3. **F22** leaves the error-body fields to "the API RFC"; **RULES API-3** already fixes them. RFC-001 adopts API-3 unchanged, so no rule is retired.
4. **RULES ARCH-1** lists the source layout but has no place for the health route, logger, scheduler, rate-limit setup or shared schemas. RFC-001, RFC-010 place them as files directly under `src/` (`src/routes/health.ts`, `src/logger.ts`, `src/scheduler.ts`, `src/rate-limit.ts`). **Flag ARCH-1** to list them.
5. **RULES DATA-8** (all SQL values as parameters) cannot apply to partition DDL, where identifiers and bounds cannot be bound. RFC-001 and RFC-006 build them only from integers and catalog names checked against a fixed pattern. **Flag DATA-8** to state the exception.
6. **RULES ARCH-2** (only `src/db/` contains SQL) is read as governing app code; the load-test seed in `load/` uses SQL directly (RFC-004). **Flag ARCH-2** if the reading is wrong.
7. **RULES OPS-5** (no GeoLite2 database committed) is read as covering real GeoLite2 data, not MaxMind's published test database, which RFC-003 commits as a test fixture. If that license is unclear, RFC-003 says to generate a fixture instead.
8. **FEATURES F15** says bots are excluded "by default" but no feature defines a way to include them; RFC-007 always excludes them and reports `excludesBots: true`.
9. **OQ-6 / RULES SEC-9** limit UI form submissions only; GET UI pages (`/`, `/analytics/{code}`) are therefore unlimited (RFC-010), although an analytics page costs about the same as an API analytics call. **Flag OQ-6** for the user: limiting GET pages is a one-line change.
10. **RULES OPS-5** says the GeoLite2 database "is downloaded at startup". RFC-003 starts the download at startup but lets it finish after `listen`, so that startup never waits on MaxMind, and it refreshes the file weekly into a volume. **Flag OPS-5** for rewording to "fetched when the app starts, and refreshed".
11. **PRD FR-8** says "record click metadata on each redirect". RFC-003 records nothing for `HEAD` requests, because link checkers and preview fetchers use `HEAD` and FR-8 is about visits. **Flag FR-8** for the user to confirm.
12. **PRD NFR-8** (< 200 ms p95 for all endpoints) vs Safe Browsing: with a key configured, creation can wait up to 2 s on Google. RFC-005 and RFC-011 measure NFR-8 with the no-op checker, which excludes third-party time. **Flag NFR-8** for a PRD decision on whether third-party time counts.
13. **PRD FR-16** fixes the API limit at 100/min. RFC-010 adds `LINKSNIP_API_RATE_LIMIT` (default 100), so that load tests can make the limiter inert, and the README says not to change it in production. **Flag FR-16** to confirm the override is acceptable.
14. **RULES SEC-10** allows only `script-src 'self'`. If the pinned Swagger UI needs an inline script, RFC-011 allows that script's hash on `/docs` only, and never `'unsafe-inline'`. **Flag SEC-10** to allow it.
15. **RULES SEC-13** (secrets only from the environment) vs the default `LINKSNIP_DB_PASSWORD=linksnip` in `compose.yaml`, which keeps `docker compose up` zero-setup. The database port is not published, and the README says to set the password. **Flag SEC-13**.
16. **RULES SEC-9** names `@fastify/rate-limit`. If the pinned version cannot share one counter across routes, RFC-010 falls back to an in-house limiter, and SEC-9 would then need amending. This is recorded here in advance.

## Assumptions

Each is marked (assumption) in its RFC and needs a code comment citing it (COMP-2). The ones a reviewer is most likely to want to overturn:

- Creation is not idempotent; no `Idempotency-Key` in v1.0 (RFC-002).
- Unknown JSON fields in the create body are rejected (RFC-002).
- `LINKSNIP_PUBLIC_SCHEME` is added because SEC-1 names only a host (RFC-001).
- HEAD on a short link records no click; query strings on short links are not forwarded (RFC-003).
- An empty user-agent counts as a bot (RFC-003).
- The GeoLite2 download uses MaxMind's basic-auth endpoint, so `LINKSNIP_GEOLITE2_ACCOUNT_ID` is required with the key; the database refreshes weekly into a named volume (RFC-003).
- A failed redirect lookup returns 503, and a click insert that is still waiting after 2 s is abandoned with the redirect still sent (RFC-003).
- The reference host has fsync-honouring SSD storage, and k6 runs on a separate machine (RFC-004).
- Raw clicks are kept 13 to 14 months because retention drops whole months (RFC-006).
- Analytics: one endpoint for all views; interval defaults by range length; at most 400 buckets; top-10 referrer tie-break by host (RFC-007).
- Delete checks existence before the token; expired and malformed codes give 404; list is newest first, includes expired, excludes deleted; an unsigned cursor is a position; a short admin token only warns (RFC-008).
- The UI's datetime input is interpreted as UTC (RFC-009); no CSRF token (RFC-009).
- One shared 100/min budget across `/api/*`, unmatched `/api/` paths and UI POSTs, overridable by `LINKSNIP_API_RATE_LIMIT` for load tests; per full IPv6 address (RFC-010).
- Rollup waits 15 minutes after a UTC day ends (RFC-006); `from`/`to` are bounded to 2000-01-01 .. today + 366 days (RFC-007).
- NFR-8 is load-tested at 50 requests/s with the no-op blocklist checker (RFC-005, RFC-011).

## Cold reads

Cold reads were run on 2026-11-15 by clean-context readers on a different model (Fable 5.2). Each reader had only PRD.md, FEATURES.md, RULES.md and one RFC, and answered: **"What would you have to guess to implement this?"** The reports were delivered in three files, one for RFC-001 to RFC-004, one for RFC-005 to RFC-008, and one for RFC-009 to RFC-012.

All three reports have been applied. The first was applied in the commit "/generate-rfcs: fix cold-read findings". The other two were applied later, once they were placed inside the project, in "/generate-rfcs: fix cold-read findings (RFC-005 to RFC-012)". Where a finding needed a decision the documents could not settle, the RFC now makes the decision and marks it (assumption). Where the decision conflicts with PRD.md or RULES.md, it is also flagged under Artifact conflicts above.

What changed after the cold read:

| RFC | Changes |
|---|---|
| RFC-001 | Fixed ESM/`NodeNext` and the `dist/` layout. Gave `startServer` a single signature, with test seams for exit paths. Config errors are thrown by `config.ts` and printed by `server.ts`. Unknown `LINKSNIP_*` keys now warn instead of failing, and `LINKSNIP_HTTP_PORT` is listed as compose-only. Every Fastify 4xx (including 413) maps to API-4 codes. The advisory lock now has a defined key and skip semantics. Logs have one `request_completed` line with fixed field names, and `/health` logs at debug. The `/health` 1 s bound is specified. A health watchdog makes Docker actually restart the app. HSTS is off on http. The PG 18 volume path is decided. Placeholder scripts are gone. Weak criteria (AC 12, 14, 25) are replaced with testable ones. |
| RFC-002 | Ajv is configured per request part, so the body is not coerced and unknown fields are not stripped. Body schemas are shallow, so services return their specific error codes. Empty or `null` optional fields count as absent. Expiry follows an exact RFC 3339 grammar with range checks for impossible dates. URL pre-checks cover the WHATWG parser's leniency. The logger, `generateCode` and `reservedAliases` are injected. A throwing checker fails open. Universal-negative criteria are made concrete (spies, grep tests, route-table test). |
| RFC-003 | A failed lookup returns 503. The insert has a 2 s timeout, and geo or bot failures are logged with named events. Malformed codes get the same 404 in the handler, and `/{code}/x` is 404. The MaxMind endpoint is decided (basic auth, so the account ID is required), with a URL seam for tests. The GeoLite2 file has a defined lifecycle (mtime age, stale file served while refreshing, daily check, named volume). The custom bot list is case-insensitive and does not depend on an isbot export. IPv4-mapped addresses are handled. Criteria use `inject` with `remoteAddress`. OPS-5 and HEAD-vs-FR-8 are flagged. |
| RFC-004 | The fsync-honouring reference host and a separate k6 machine are defined. The seed is pure SQL via `psql` with `ON CONFLICT DO NOTHING` top-up: exact count, no `pg-copy-streams` dependency. Warm-up and steady scenarios are separate. The server-side figure from `request_completed` logs decides NFR-1. The durability test runs three times at random kill times, with no truncation. Forbidden tuning (`synchronous_commit`, `fsync`, schema changes) is listed. The verdict run is tied to release (RFC-011 AC 10). |
| RFC-005 | The checker takes injected `fetch`, signal factory and logger, so the timeout test is deterministic. Header-only key, with the query-string fallback removed. The normalized URL is defined as RFC-002's `href`. Failure logs carry the hostname. `APP_VERSION` is generated. `buildDeps` makes the checker choice observable, and a whitespace-only key counts as unset. AC 6 and 7 assert on captured `fetch` URLs. The F7 UI half points to RFC-009. NFR-8 flagged. |
| RFC-006 | Rollup waits a 15-minute grace period after midnight. Detach and drop share one transaction with `lock_timeout` 2s, and an orphan sweep is added. Partitions are discovered from `pg_inherits`. Retention runs rollup first and logs blocked partitions at warn. A guard stops rollup rebuilding a day whose raw data is gone. The aggregate-purge cutoff and bounds are defined. Job registration is unit-tested. The IP test proves the IP reached the app. Crash injection uses a hook. "No DELETE" is checked through a statement recorder. PRIV-3 flagged (item 2). |
| RFC-007 | The service validates dates and interval, so every bad value gives `INVALID_RANGE`. `from` and `to` have bounds, and the 400-bucket cap applies to defaulted intervals too. Range length is counted inclusively. Default `from` is clamped to `to`. Null host and country are represented and sorted last. The watermark is read inside the snapshot. `totalClicksFor` has explicit `clicked_at` bounds and converts bigints. `no-store` is on errors too. 429 is declared. The sum criteria are corrected. Isolation is checked with a statement recorder. F15 flagged (item 8). |
| RFC-008 | Admin auth runs in `preValidation`, before schema validation. Expired and malformed codes return 404 on DELETE (API-4). Bearer parsing is defined. Cursor rules are defined (unsigned position, explicit invalid cases). `shortUrl` source and the backward index scan are stated. A short admin token now warns instead of failing (F5/SEC-5). 429 is declared. Log and total-click criteria are made checkable. |
| RFC-009 | Uses RFC-007's `getAnalytics` contract, and the filter is pre-filled from it. `renderShortenForm` helper for RFC-010's 429. `toIso` handles blanks and seconds, and "Never expires" is shown. Messages cover every code. The error and not-found pages are defined and marked "modified". The 400 analytics page has a defined mode. Concrete checks replace vague ones: CDP throttling numbers with `loadEventEnd`, Chromium only; escaping tested on rendered text with a raw DB fixture; clipboard per browser; a no-validation grep; a keyboard e2e; a gzip JS-budget test. |
| RFC-010 | Two encapsulated contexts, each with a global limiter, give a shared API budget, with an in-house fallback. The hook runs at `preHandler`, so the form re-renders with values. One error-handler branch formats 429 per surface, and a `rate-limited.eta` page is added. HEAD shares the redirect counter. Unmatched `/api/` paths are limited. `LINKSNIP_API_RATE_LIMIT` is added. Explicit log de-duplication. Validation of config edge cases. Each budget's message names its own limit. Tests use an injected window. Concrete never-limited and budget-separation criteria. FR-16 flagged. |
| RFC-011 | `ajv` is added as a devDependency per STACK-4. Routes are listed through an `onRoute` hook, and HEAD routes are excluded. `config.kind` and `apiEquivalent` live on the routes, so parity cannot pass by construction. The compatibility diff rules are defined, and additive changes are snapshotted by hand. The `ErrorBody` `$id` and `addSchema` are specified. The load mix follows keyset cursors and expects no 4xx. Limits are made inert. Server-side p95 is checked per endpoint. Contract tests cover error paths. A Swagger UI e2e is added. The CSP decision is "hash on /docs only", and SEC-10 is flagged. |
| RFC-012 | A true cold start: build cache pruned and base image removed. The project name `linksnip-smoke` plus an explicit opt-in guard `down -v`. Bandwidth is measured, with a 100 Mbps assumption. Every variable is in the defaults table, and each default is observable. Exact backup and restore commands use `-T`, with a round-trip step. The GeoLite2 attribution and footer rule are defined. README-section and no-compose-v1 tests have scoped greps. `start_period` and the image name are set explicitly. The CI trigger is defined. SEC-13 flagged. |
## Next steps

- Run `/test-strategy` before implementing (no TEST-STRATEGY.md exists yet).
- Consider a second cold read of the revised RFCs, since the fixes added text that no reader has seen yet.
- Answer the flagged conflicts (PRIV-3, ARCH-1, DATA-8, ARCH-2, OQ-6, OPS-5, FR-8, NFR-8, FR-16, SEC-10, SEC-13, SEC-9) in RULES.md / PRD.md.

## Self-check

- Counts recounted from the RFC files: 12 RFCs; complexity High 3 (RFC-001, RFC-003, RFC-004), Medium 8 (RFC-002, RFC-005, RFC-006, RFC-007, RFC-008, RFC-009, RFC-010, RFC-011), Low 1 (RFC-012). Feature coverage: 30 Must assigned; F15, F29, F35 scheduled; F28, F34 deferred.
- The index, dependency table and graph were checked against each RFC's `**Depends on**` line: every predecessor is lower-numbered, and every successor list is the inverse of the predecessor lists.
- Feature IDs in each RFC's `**Features**` line were checked against FEATURES.md titles (e.g. F22 is the error body, F31 storage, F33 health, F35 migrations; F9 escaping; F29 noindex); rule IDs in every `**Rules**` line exist in RULES.md and were spot-checked for meaning (e.g. SEC-8 trusted proxies in RFC-003/RFC-010, PERF-2 awaited insert in RFC-003/RFC-004, DATA-6 partition drops in RFC-006, API-7 pagination in RFC-008).
- Every H1-H5 row cites acceptance criteria numbers that exist in the named RFC and say what the row claims.
- `trace-check.py` was run on the project (`python3 trace-check.py .`): 28 requirements, 44 features, 95 rules, 12 RFCs; **0 failures, 4 warnings**. The warnings are all expected: F28 and F34 (Could) are unassigned -- deferred above; F32 is split across RFC-004 and RFC-011 -- intended, explained above; TEST-STRATEGY.md does not exist -- run `/test-strategy` next. A first run showed no failures; a separate scripted check found rule IDs cited in RFC bodies but missing from their `**Rules**` lines, and those were added.
- Cold reads: run by Fable 5.2 on 2026-11-15 for all 12 RFCs, and the findings of all 12 applied (see Cold reads).
