# FEATURES: LinkSnip URL Shortener

Source: `PRD.md` (FR-1 to FR-19, NFR-1 to NFR-9, D1-D6, OQ-1 to OQ-15) and `PRD-REVIEW.md` (H1-H5, M1-M9, L1-L10, R1-R11).

This file was written non-interactively: no person was available to answer questions. Where a feature rests on one of the PRD's open questions, it follows the assumption PRD.md records for that question and says so with **(assumption)**. Where this file adds an assumption of its own, it is marked **(assumption)** and explained in the Assumptions section at the end.

## Product Overview

LinkSnip is a self-hostable web app and REST API that turns long URLs into short links and reports click analytics. It serves two personas: Developer Dave, who wants fast URL shortening through an API on his own infrastructure, and Marketer Maria, who wants branded aliases and simple engagement analytics. v1.0 has no user accounts; all links are public, deletion is protected by a per-link management token and listing by an operator admin token (OQ-1, assumption). The product runs from a single `docker compose up` and targets sub-100ms p95 redirects at 1,000 redirects per second, with storage for 10M short URLs.

Feature IDs are permanent. New features take the next unused number; removed features are marked [REMOVED], never deleted or renumbered, because RFCs cite these IDs.

## Summary

### Feature counts by priority

| Priority | Count |
|---|---|
| Must | 30 |
| Should | 3 |
| Could | 2 |
| Won't | 9 |
| **Total** | **44** |

### Feature counts by category

| Category | Must | Should | Could | Won't | Total |
|---|---|---|---|---|---|
| URL Management | 5 | 0 | 0 | 0 | 5 |
| Input Validation and Abuse Prevention | 4 | 0 | 0 | 0 | 4 |
| Redirection and Click Tracking | 5 | 1 | 0 | 0 | 6 |
| Analytics | 5 | 0 | 0 | 0 | 5 |
| API | 4 | 0 | 0 | 0 | 4 |
| Web UI | 3 | 1 | 1 | 0 | 5 |
| Deployment and Operations | 4 | 1 | 1 | 0 | 6 |
| Out of Scope (v1.0) | 0 | 0 | 0 | 9 | 9 |
| **Total** | **30** | **3** | **2** | **9** | **44** |

Priorities follow D4: every PRD requirement is Must for v1.0 because the PRD's In Scope list commits to all of them. Should and Could features are additions that come from the review's recommendations or the open-question assumptions, not from PRD requirements. OQ-11 names the demotion candidates if the six weeks slip: F20 (date-range filter) and F24 (Swagger UI; the OpenAPI file, F23, stays Must).

## Features

### URL Management

| ID | Feature | Priority | Source | Complexity | Acceptance Criteria |
|---|---|---|---|---|---|
| F1 | Create short URL with generated code | Must | FR-1, FR-14 | Medium | Creating a short URL from a valid long URL returns a 7-character code matching `[0-9A-Za-z]{7}` and the full short URL; codes are case-sensitive (`abc1234` and `ABC1234` are different links); codes are generated randomly, and a generated code that collides with any existing code or alias is retried, never returned and never overwrites an existing link; the destination is validated first (F6) and blocklist-checked (F7); the response also carries the management token (F4). |
| F2 | Custom alias | Must | FR-2 | Medium | A create request may supply an alias of 3-30 characters from `[0-9A-Za-z]`; 2 or 31 characters, or any other character, is rejected with a 400 and the consistent error body (F22); the alias must be unique across all generated codes and aliases (D3), and a taken alias returns 409 and leaves the existing link unchanged; reserved paths used by the UI or API (at least `api`, `docs`, `static`, `health`) are rejected with an error that says the alias is reserved; aliases are case-sensitive, so `Promo` and `promo` are different links (OQ-15, assumption), and the reserved-word check is case-insensitive so `API` cannot shadow `/api` (assumption). |
| F3 | Expiration date-time | Must | FR-3 | Low | A create request may supply an expiration date-time; it is stored in UTC (OQ-12, assumption); a value in the past or equal to now is rejected with a 400; a value without a time-zone offset is rejected rather than guessed (assumption); once the expiration passes, the link returns 404 (F11); the expiration cannot be changed after creation (editing is out of scope, F41). |
| F4 | Management token and delete | Must | FR-4 | Medium | Creating a short URL returns a secret management token exactly once; the server stores only a hash of it (assumption) and cannot show it again; DELETE of a short URL with the correct token returns success and the link returns 404 from then on (F11); DELETE without a token or with a wrong token returns 403 and the link still redirects (R2); deleting an already-deleted or non-existent code returns 404; a deleted code or alias is never reissued to a new link (assumption, so an old shared link never starts pointing somewhere new). (OQ-1, assumption) |
| F5 | List short URLs (operator only) | Must | FR-5 | Low | Listing returns, per short URL: code, destination, created time, expiration time, total clicks; it requires the operator admin token set in deployment configuration (OQ-1, assumption); a request without a valid admin token returns 403; if no admin token is configured, listing is disabled and returns 403 (assumption); the list is paginated so 10M rows (NFR-6) are never returned in one response (assumption); management tokens are never included. |

### Input Validation and Abuse Prevention

| ID | Feature | Priority | Source | Complexity | Acceptance Criteria |
|---|---|---|---|---|---|
| F6 | Destination URL validation | Must | FR-19, NFR-5 | Medium | Only absolute `http` and `https` URLs are accepted; `javascript:`, `data:`, `file:`, `ftp:` and other schemes are rejected with 400; malformed URLs (no host, invalid characters, relative paths) are rejected; URLs whose host is the LinkSnip instance's own public host are rejected as redirect loops (D5); URLs longer than 2,048 characters are rejected (R7, assumption); aliases and all query parameters on API endpoints are validated and an invalid value returns 400, never a 500; no reachability check is made (OQ-14, assumption; see F43). |
| F7 | Malware and phishing blocklist check | Must | NFR-4 | High | A pluggable checker interface is called at creation time; Google Safe Browsing Lookup API v4 is the first implementation, using an operator-supplied API key (OQ-2, assumption); a destination the provider lists is rejected with a clear "blocklisted URL" error; with no key configured the check is disabled and both the API create response and the UI say the URL was not checked; if the provider is unreachable or times out, the link is created, the failure is logged, and the response says it was not checked (fail open; R5, assumption); the deployment docs state that Safe Browsing's free API is non-commercial only and that commercial deployments need Google Web Risk or another provider; existing links are not re-checked (F42). Needs a third-party integration. |
| F8 | Rate limiting | Must | FR-16 | Medium | `/api/*` requests and UI form submissions are limited to 100 requests per minute per client IP (OQ-6, assumption); request 101 within the window returns 429 with a `Retry-After` header and the consistent error body (F22); redirects are not subject to the 100/min limit but to a separate, much higher, operator-configurable abuse limit (OQ-6, assumption); the client IP is taken from `X-Forwarded-For` only when the request comes from a proxy listed in configuration, otherwise from the socket address, so a spoofed header from an untrusted client has no effect; limits apply per instance (assumption). |
| F9 | Output escaping in the web UI | Must | NFR-5 | Low | Every user-supplied value rendered in the web UI -- destinations, aliases, referrers, user-agents -- is HTML-escaped; a referrer or destination containing `<script>` renders as text and runs no script; destination links in the UI are only ever rendered for `http`/`https` URLs (F6). |

### Redirection and Click Tracking

| ID | Feature | Priority | Source | Complexity | Acceptance Criteria |
|---|---|---|---|---|---|
| F10 | Redirect with 302 | Must | FR-6, NFR-1, NFR-3 | Medium | GET on a live short URL returns HTTP 302 (never 301; D1) with `Location` set to the destination and `Cache-Control: private, no-store`; two requests from the same browser both reach the server and are both recorded (F12); redirect latency is under 100ms at p95, measured server-side, at 1,000 redirects per second on the reference host (verified by F32). |
| F11 | 404 for expired, deleted and unknown links | Must | FR-7 | Low | A request for an expired, deleted or never-created code returns 404; the response does not reveal which of the three it is (PRD-REVIEW L5); a link whose expiration passed one second ago returns 404; a 404 records no click; the 404 response also carries `Cache-Control: no-store` (assumption). |
| F12 | Click recording | Must | FR-8, NFR-9 | High | Every 302 redirect records one click with timestamp (UTC), referrer, user-agent and country (F13); a missing referrer is stored as empty, not as an error; the click is written durably to the database before the redirect response is sent (OQ-7, assumption), so after a hard kill of the app container every click whose redirect was answered is present (R6); if the click write fails, the redirect still succeeds and the failure is logged and counted (assumption -- a redirect is never blocked by analytics); if load tests (F32) show the synchronous write breaks NFR-1, OQ-7 must be revisited and NFR-9 relaxed to a stated loss window. |
| F13 | Country geolocation | Must | FR-8, FR-12 | Medium | The country is derived from the client IP (determined as in F8) at click time using MaxMind GeoLite2 with an operator-supplied license key (OQ-5, assumption); without a key, or for an IP with no match, the country is recorded as "Unknown"; the deployment docs cover obtaining the key and GeoLite2's attribution terms. Needs a third-party data source. |
| F14 | Click data privacy and retention | Must | FR-8 | Medium | The client IP is used only to derive the country and is never written to the database or to logs (OQ-4, assumption); user-agents and referrers are stored; raw click events are deleted after 13 months by a retention job, and per-day aggregates are kept indefinitely; both periods are operator-configurable; totals and timelines (F16, F17) stay correct after raw events are purged; the docs include a privacy note stating what is stored and for how long. |
| F15 | Bot and link-preview filtering | Should | FR-9, FR-10, FR-11, FR-12 | Medium | Clicks whose user-agent matches a maintained known-bot and link-preview list are recorded with a bot flag but excluded from all analytics views by default (OQ-9, assumption); the bot list is replaceable by the operator. Should, not Must: it is an assumption on top of the PRD's requirements, not a requirement itself. |

### Analytics

| ID | Feature | Priority | Source | Complexity | Acceptance Criteria |
|---|---|---|---|---|---|
| F16 | Total click count | Must | FR-9 | Low | Shows the total number of clicks for one short URL; a link with no clicks shows 0; analytics for a single code are public, with no token (OQ-1, assumption); analytics for an unknown, deleted or expired code return 404 (assumption, consistent with F11). |
| F17 | Click timeline | Must | FR-10 | Medium | Shows clicks per day, per week or per month for one short URL, bucketed in UTC (OQ-12, assumption); weeks start on Monday (ISO 8601, assumption); buckets with no clicks appear as 0 rather than being omitted; the UI labels the time zone as UTC. |
| F18 | Top referrers | Must | FR-11 | Low | Shows the referrers with the most clicks for one short URL, ordered by click count; clicks with no referrer are grouped as "Direct / none"; referrers are grouped by host (assumption); the list shows the top 10 (assumption). |
| F19 | Geographic breakdown | Must | FR-12 | Low | Shows clicks per country for one short URL; clicks with no resolvable country count as "Unknown"; the country counts sum to the total click count for the same filter. |
| F20 | Date-range filter | Must | FR-13 | Low | Every analytics view (F16-F19) accepts a start and end date (UTC, inclusive); all views use the same range so their totals agree; a start after the end returns 400; a range before the raw-retention window (F14) is served from daily aggregates. Demotion candidate to Should if the six weeks slip (OQ-11). |

### API

| ID | Feature | Priority | Source | Complexity | Acceptance Criteria |
|---|---|---|---|---|---|
| F21 | REST API for all operations | Must | FR-14 | Medium | The API exposes every URL management operation (F1-F5) and every analytics view (F16-F20); everything the web UI can do, the API can do; endpoints are under `/api/v1/` so a later accounts feature can change contracts without breaking v1 clients (R9, assumption); management and analytics endpoints respond in under 200ms at p95 (NFR-8, verified by F32). |
| F22 | JSON format and consistent error body | Must | FR-15 | Low | Requests and responses use `application/json`; every 4xx and 5xx response, including 404, 409, 429 and 500, has the same error body shape with a machine-readable code and a human-readable message (assumption on the exact fields; settled in the API RFC); a request with a non-JSON body returns 400 with that body, not a 500. |
| F23 | OpenAPI specification | Must | FR-17 | Low | An OpenAPI specification describes every endpoint in F21 with request, response and error schemas; it is served by the running instance; a contract test fails if an endpoint's behavior and the spec disagree (assumption). |
| F24 | Swagger UI | Must | FR-17 | Low | A browsable Swagger UI renders the OpenAPI spec (F23) from the running instance at a reserved path (for example `/docs`, reserved in F2). Demotion candidate to Should if the six weeks slip; the OpenAPI file itself stays Must (OQ-11). |

### Web UI

| ID | Feature | Priority | Source | Complexity | Acceptance Criteria |
|---|---|---|---|---|---|
| F25 | Shorten page | Must | FR-18, FR-1, FR-2, FR-3 | Medium | A user can paste a long URL, optionally set a custom alias and an expiration, and receive the short URL immediately; a copy-to-clipboard control copies it; the management token (F4) is shown once with a warning that it cannot be shown again; every failure in the Shorten journey -- invalid URL, blocklisted URL, alias taken, alias reserved, rate limit exceeded -- shows a clear, specific message and keeps the user's input; when the blocklist check is disabled or failed (F7), the page says the URL was not checked. |
| F26 | Analytics page | Must | FR-18, FR-9, FR-10, FR-11, FR-12, FR-13 | Medium | The analytics page for a short URL shows total clicks, a click timeline chart, top referrers and the geographic breakdown, with a date-range filter that updates all of them; the chart has a text or table equivalent (WCAG, F27); an unknown, deleted or expired code shows a not-found page. |
| F27 | Web UI quality bars | Must | FR-18 | Medium | Pages meet WCAG 2.1 AA (OQ-13, assumption); they work in the last two versions of Chrome, Firefox, Safari and Edge; they are usable with no horizontal scrolling at 360px width; the create page is interactive in under 2 seconds on a mid-range phone. |
| F28 | Delete from the web UI | Could | FR-4, FR-18 | Low | A user can delete a short URL in the UI by entering its management token; a wrong token shows an error and the link is kept. Could: the Delete journey allows the API or the UI, and FR-18 names only the Shorten and View Analytics journeys, so the API (F4, F21) satisfies the requirement. |
| F29 | Keep public pages out of search indexes | Should | FR-6, FR-18 | Low | Analytics pages and redirect responses send `X-Robots-Tag: noindex` (R11); analytics pages also carry a `noindex` robots meta tag. |

### Deployment and Operations

| ID | Feature | Priority | Source | Complexity | Acceptance Criteria |
|---|---|---|---|---|---|
| F30 | Docker Compose deployment | Must | NFR-7 | Medium | A single `docker compose up` (Compose v2; D2) on a fresh Docker install starts a working instance with its database; a first deployment takes under 5 minutes on the reference host (OQ-8, assumption) with images not yet pulled; all operator settings -- public host, admin token (F5), Safe Browsing key (F7), GeoLite2 key (F13), trusted proxies and limits (F8), retention periods (F14) -- are set through environment variables or one config file, and the instance starts with safe defaults when the optional ones are absent; the README documents each setting. |
| F31 | Storage for 10M short URLs | Must | NFR-6 | High | One instance stores at least 10M short URLs with their click data while still meeting NFR-1 and NFR-3 (OQ-3, assumption: up to 10,000 of them receive clicks in a month); code lookup is indexed; the click table is designed for its much larger growth (about 1,000 rows per second at NFR-3 rates); the datastore is chosen in the first RFC (R8 suggests PostgreSQL with a partitioned click table). |
| F32 | Performance verification | Must | NFR-1, NFR-2, NFR-3, NFR-8 | High | A repeatable load test on a 2 vCPU / 4 GB host (OQ-8, assumption) with 10M stored URLs shows: redirect p95 under 100ms server-side, and average under 50ms (Success Metrics), at a sustained 1,000 redirects per second; management and analytics endpoints p95 under 200ms; no failed redirects under that load. NFR-2 (99.9% uptime) is treated as a design target for LinkSnip itself, not a guarantee for operators, and the README says so (OQ-8, assumption). |
| F33 | Health check endpoint | Must | NFR-2, NFR-7 | Low | `/health` (reserved in F2) returns 200 when the app can reach its database and 503 when it cannot; the Compose file uses it as the container health check, so a failed instance is restarted. |
| F34 | Observability | Could | NFR-2 | Medium | Structured request logs (without client IPs, F14) and basic metrics: request counts and latencies per endpoint, click-write failures (F12), blocklist-check failures (F7), rate-limit rejections (F8). Could: no PRD requirement names it, but operators need it to see whether NFR-1 and NFR-2 hold. |
| F35 | Schema migrations and backup | Should | NFR-6, NFR-7 | Medium | Schema changes ship as versioned migrations that run on startup or with one command; upgrading an instance keeps its links and clicks; the README documents backing up and restoring the database volume (R10). |

### Out of Scope (v1.0)

| ID | Feature | Priority | Source | Complexity | Acceptance Criteria |
|---|---|---|---|---|---|
| F36 | User accounts and authentication | Won't | PRD Out of Scope | High | Not built in v1.0; all URLs are public. F4 and F5 use tokens instead of accounts, and the `/api/v1/` prefix (F21) leaves room to add accounts later. |
| F37 | Team workspaces and collaboration | Won't | PRD Out of Scope | High | Not built in v1.0. |
| F38 | Custom domains | Won't | PRD Out of Scope | Medium | Not built in v1.0; an instance serves short links on its one configured public host. |
| F39 | QR code generation | Won't | PRD Out of Scope | Low | Not built in v1.0. |
| F40 | Bulk URL import | Won't | PRD Out of Scope | Medium | Not built in v1.0. |
| F41 | Editing the destination of an existing short URL | Won't | PRD Out of Scope | Low | Not built in v1.0; a link's destination and expiration are fixed at creation. |
| F42 | Re-checking existing links against the blocklist | Won't | NFR-4 (OQ-2) | Medium | Not built in v1.0; links are checked only at creation (F7). |
| F43 | Destination reachability pre-check | Won't | FR-19 (OQ-14) | Low | Not built in v1.0: it adds latency, fails for links behind logins, and would let LinkSnip probe internal hosts (SSRF). |
| F44 | Per-user or local time zones | Won't | FR-3, FR-10 (OQ-12) | Low | Not built in v1.0; timelines and expirations are stored and shown in UTC. |

## Requirement Coverage

Every PRD requirement is the source of at least one feature. This table is derived from the Source column above.

| Requirement | Features |
|---|---|
| FR-1 | F1, F25 |
| FR-2 | F2, F25 |
| FR-3 | F3, F25, F44 |
| FR-4 | F4, F28 |
| FR-5 | F5 |
| FR-6 | F10, F29 |
| FR-7 | F11 |
| FR-8 | F12, F13, F14 |
| FR-9 | F16, F15, F26 |
| FR-10 | F17, F15, F26, F44 |
| FR-11 | F18, F15, F26 |
| FR-12 | F19, F13, F15, F26 |
| FR-13 | F20, F26 |
| FR-14 | F21, F1 |
| FR-15 | F22 |
| FR-16 | F8 |
| FR-17 | F23, F24 |
| FR-18 | F25, F26, F27, F28, F29 |
| FR-19 | F6, F43 |
| NFR-1 | F10, F32 |
| NFR-2 | F32, F33, F34 |
| NFR-3 | F10, F32 |
| NFR-4 | F7, F42 |
| NFR-5 | F6, F9 |
| NFR-6 | F31, F35 |
| NFR-7 | F30, F33, F35 |
| NFR-8 | F32 |
| NFR-9 | F12 |

## PRD-REVIEW High-Impact Findings

Every High-impact finding in PRD-REVIEW.md ends up in a feature or acceptance criterion:

| Finding | Where it is handled |
|---|---|
| H1 -- 301 redirects are cached, breaking tracking and expiry | F10 (302 with `Cache-Control: private, no-store`), F11 (no-store on 404), F12 (every redirect recorded) |
| H2 -- anyone can delete or list every link | F4 (per-link management token for delete), F5 (operator admin token for listing) |
| H3 -- contradictory scale targets (10,000 vs 10M) | F31 (10M stored, up to 10,000 active; OQ-3), F32 (load test with 10M stored URLs) |
| H4 -- click data is personal data with no retention policy | F14 (IP never stored, 13-month raw retention, aggregates kept, privacy note) |
| H5 -- blocklist provider unchosen and licensing-restricted | F7 (pluggable checker, Safe Browsing first, disabled without a key, licensing documented), F42 (no re-checking) |

## Implementation Complexity

### Third-party integrations

- **F7** -- Google Safe Browsing Lookup API v4 (API key, non-commercial terms; Google Web Risk for commercial deployments).
- **F13** -- MaxMind GeoLite2 (account and license key, attribution terms, periodic database updates).

### Significant technical challenges

- **F12 with F10** -- a durable synchronous click write on every redirect at 1,000 per second inside a 100ms p95 budget (OQ-7). This is the critical path: every performance requirement and every analytics feature depends on the redirect and click schema, so it should be built and load-tested first (F32).
- **F31** -- 10M URLs plus a click table growing at about 1,000 rows per second, with retention purges (F14) that must not disturb redirect latency.
- **F8** -- correct client-IP determination behind reverse proxies; getting it wrong either blocks whole offices or lets anyone bypass the limit.
- **F7** -- the fail-open behavior and the "not checked" signal must be consistent across API and UI.

### Dependencies

- F1 depends on F6, F7 and F4 (validation, blocklist, token in the create response); F2 and F3 extend F1.
- F10, F11 and F12 depend on the storage design (F31); F13 and F14 are part of F12's write path.
- F16-F20 depend on F12 (and F15 when built); F20 depends on F14's aggregates for old ranges.
- F21-F24 wrap F1-F5 and F16-F20; F25 and F26 use the same operations; F27 applies to both.
- F30, F32 and F33 depend on everything else being runnable; F32 must run early against F10 and F12 to settle OQ-7.

## Assumptions

PRD.md's open questions are assumptions already; features that rely on them cite the OQ. This file adds the following, each marked (assumption) where it is used:

- Reserved-word matching is case-insensitive even though aliases are case-sensitive (F2), so `API` cannot shadow `/api`.
- Expiration values without a time-zone offset are rejected (F3).
- Management tokens are stored hashed; deleted codes and aliases are never reissued (F4).
- Listing is paginated, and disabled when no admin token is configured (F5).
- Destination URLs are limited to 2,048 characters (F6, from R7).
- When the blocklist provider is unreachable, creation fails open with a log line and a "not checked" notice (F7). PRD-REVIEW R5 asks for this choice to be made; fail closed is the alternative.
- Rate limits are per instance (F8).
- A failed click write never fails the redirect (F12); 404 responses also carry `no-store` (F11).
- Analytics for unknown, deleted or expired codes return 404 (F16); weeks start on Monday (F17); referrers are grouped by host and the top 10 shown (F18).
- The API is versioned under `/api/v1/` (F21, from R9); the exact error-body fields are left to the API RFC (F22); an OpenAPI contract test guards the spec (F23).
- The reference host for the deployment-time target is the same 2 vCPU / 4 GB host as OQ-8 (F30).

## Self-check

- Counts recounted from the feature tables: 44 features (F1-F44, no gaps); Must 30, Should 3, Could 2, Won't 9; per-category totals 5 + 4 + 6 + 5 + 4 + 5 + 6 + 9 = 44. The two summary tables agree with each other and with the feature tables.
- Every FR-1 to FR-19 and NFR-1 to NFR-9 appears in at least one feature's Source column; the Requirement Coverage table was checked row by row against the Source column.
- Every PRD Out of Scope item has a Won't row (F36-F41), as do the exclusions in OQ-2, OQ-12 and OQ-14 (F42-F44).
- All five High-impact findings (H1-H5) map to features above.
- `trace-check.py` was run on the project (`python3 trace-check.py .`): 28 requirements, 44 features, 0 rules, 0 RFCs; 0 failures, 0 warnings. Priority counts were also recounted mechanically from the table rows (30 / 3 / 2 / 9).
