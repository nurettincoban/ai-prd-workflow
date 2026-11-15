# PRD Review: LinkSnip URL Shortener

Reviewed: `PRD.md` as committed in "Start from the v2.0 PRD". The improved version replaces it in the same directory; `git diff` shows every change.

This run was non-interactive: no person was available to answer questions. Gaps only the user can close are recorded in PRD.md's Open Questions marked **(assumption)**, never as Decisions.

## Product Type

Web app + service/API (recorded in PRD.md's Product Type section). Skipped: binary size, offline sync, sessions (no accounts in v1.0). The service/API row's UI/accessibility/responsive skips were not taken because the web-app half needs them.

## Step 0: Grounding

- **Existing implementation:** the PRD names none (no prototype or "extracted from" source), so there was nothing to diff against.
- **Technology claims checked against known behavior:**
  - *HTTP 301* is cached permanently by browsers. This contradicts per-click tracking, zero click loss, and expiry/deletion returning 404 (finding H1).
  - *`docker-compose up`* is the Compose v1 command; Compose v1 reached end of life in 2023 and current Docker ships `docker compose` (finding L1).
  - *7-character base62* gives 62^7 ≈ 3.5 × 10^12 codes -- ample for 10M URLs; random generation with collision retry is fine at that density.
  - *Malware/phishing blocklists:* Google Safe Browsing's free Lookup API is limited to non-commercial use; commercial use needs Google Web Risk (finding H5).
  - *Country-level geolocation:* self-hosted lookup normally uses MaxMind GeoLite2, which requires a MaxMind account and license key (finding M2).
  - *OpenAPI/Swagger:* no issue.
- **Not verified in this run** (stated, not assumed true): the provider terms above were checked from documented behavior known to the reviewer, not re-read live; the performance figures (p95 < 100ms, average < 50ms, 1,000 redirects/s, API < 200ms) cannot be verified without stated hardware or a load test; the 99.9% uptime target cannot be verified for a self-hosted single instance; "deploy in under 5 minutes" depends on image size and network and is unverified.

## 1. Summary of Findings

### High impact (5)

| ID | Finding | Resolution in PRD.md |
|---|---|---|
| H1 | Redirects use HTTP 301, which browsers cache: repeat clicks are never seen (breaks click tracking and "zero data loss") and deleted or expired links keep redirecting from cache (breaks the 404 requirement). | D1: 302 with `Cache-Control: private, no-store` (FR-6). Settled by the PRD's own requirements. |
| H2 | No accounts, yet "delete a short URL" and "list all created short URLs" are open to everyone: anyone can delete any link or enumerate every link (including private destinations). | OQ-1 (assumption): per-link management token for delete; admin token for list-all. |
| H3 | Contradictory scale targets: Goals say "10,000+ active short URLs", NFRs say "10M+ URLs". "Active" is undefined. | OQ-3 (assumption): design for 10M stored; ≤ 10,000 active. NFR-6 keeps 10M. |
| H4 | Click records (IP-derived country, user-agent, referrer) are personal data; no privacy or retention policy exists, and retention was an open question. | OQ-4 (assumption): discard IP after country lookup; 13-month raw retention, aggregates kept; operator-configurable. |
| H5 | The security NFR depends on a blocklist provider that is not chosen; the obvious free option (Safe Browsing Lookup API) is non-commercial only and needs an API key, so the NFR is unimplementable as written. | OQ-2 (assumption): pluggable checker, Safe Browsing first, disabled without a key. NFR-4 rewritten. |

### Medium impact (9)

| ID | Finding | Resolution in PRD.md |
|---|---|---|
| M1 | "Zero data loss on click tracking" vs "< 100ms p95 redirect" at 1,000/s: a durable write per redirect competes with the latency budget; the trade-off is unstated. | NFR-9 added; OQ-7 (assumption): synchronous write, revisit after load test. |
| M2 | Country geolocation has no data source; GeoLite2 needs a license key; behavior without one is undefined. | OQ-5 (assumption); FR-12 counts unresolved as "Unknown". |
| M3 | Rate limit (100/min/IP) scope is undefined -- applied to redirects it blocks whole offices behind NAT; client IP behind a reverse proxy is undefined (spoofable `X-Forwarded-For`). | OQ-6 (assumption): API and UI writes only; trusted-proxy list. |
| M4 | Custom aliases (3-30 alphanumerics) can collide with generated 7-char codes and with UI/API routes (`api`, `docs`); case sensitivity unstated. | D3 (shared namespace, reserved words, FR-2); OQ-15 (assumption): case-sensitive. |
| M5 | "Sanitize all inputs" does not say what a valid destination is: `javascript:`/`data:` URLs (XSS in the UI) and self-links (redirect loops) are accepted. | D5; FR-19 added. |
| M6 | 99.9% uptime and the throughput figures have no reference hardware and cannot be guaranteed by a self-hosted single instance. | OQ-8 (assumption): reference host for load tests; NFR-2 as a design target. |
| M7 | Link-preview crawlers and bots inflate click analytics, misleading the Marketer persona. | OQ-9 (assumption): record but exclude known bots by default. |
| M8 | Requirements had no IDs and no prioritization, so features and RFCs could not cite them and nothing could be cut if the six weeks slip. | D6 (FR-1..19, NFR-1..9); D4 (all In Scope = Must); OQ-11 proposed demotions. |
| M9 | Web UI quality bars missing: accessibility, browser support, responsive layout, page-load budget. The UI itself was implied but never a requirement. | FR-18 added (UI follows from Goals/Journeys); OQ-13 (assumption) for the targets. |

### Low impact (10)

| ID | Finding | Resolution in PRD.md |
|---|---|---|
| L1 | `docker-compose up` is the end-of-life Compose v1 command. | D2: `docker compose up` (NFR-7). |
| L2 | Two latency targets (p95 < 100ms in NFRs, average < 50ms in Success Metrics) without saying both apply. | Success Metrics now says the average target is in addition to NFR-1. |
| L3 | Team size, budget and license unstated, so the six-week timeline cannot be assessed. | OQ-10 (assumption). |
| L4 | Time zone of timeline buckets and expiration unstated. | FR-3, FR-10 use UTC; OQ-12 (assumption). |
| L5 | Expired links return 404; 410 Gone would be more precise. Kept 404 as written -- it hides whether a code ever existed. | No change (FR-7 also covers deleted links). |
| L6 | No API versioning policy. | Recommendation R9; left to the API RFC. |
| L7 | No testing, upgrade, migration or backup requirements. | Recommendation R10; left to /test-strategy and RFCs. |
| L8 | No datastore named, though NFR-3/NFR-6 depend on it. | Recommendation R8; left to the RFCs. |
| L9 | Original open question on pre-validating reachability. | OQ-14 (assumption): no, also avoids SSRF. |
| L10 | SEO for public pages: per-link analytics pages are public and could be indexed. | Recommendation R11. |

### Overall assessment

The PRD is short, coherent in intent, and well scoped for a six-week v1.0, with clear personas and journeys. Its most serious problem is a technical contradiction -- 301 redirects defeat both click tracking and expiry -- followed by a missing authorization story for delete/list in an account-less product and an unresolved privacy and blocklist story. Once the open questions are answered it is implementation-ready.

## 2. Specific Recommendations

- **R1 (H1)** Use 302 with no-store caching. Example rewrite: "Redirect with HTTP 302 and `Cache-Control: private, no-store`" instead of "Redirect via HTTP 301".
- **R2 (H2)** Decide the ownership model before any API is designed. The management-token model keeps "no accounts" while making delete safe. Example acceptance criterion: "DELETE /api/urls/{code} without a valid management token returns 403 and the link still redirects."
- **R3 (H3)** Replace both scale numbers with one: "stores 10M short URLs; up to 10,000 receive clicks in any month."
- **R4 (H4)** Write a data-retention paragraph: which fields are kept, for how long, and that the IP is never stored. Operators in the EU need it to deploy at all.
- **R5 (H5)** Name the blocklist provider and its licensing, and state what happens when it is unreachable (assumed: fail open with a log line, or fail closed -- pick one; this is part of OQ-2).
- **R6 (M1)** Make NFR-9 testable: "after a hard kill of the app container, every click whose redirect was answered is present in the database."
- **R7 (M3, M5)** Make validation and limits concrete: allowed schemes, maximum URL length (suggest 2,048 characters), reserved aliases, rate-limited endpoints, trusted proxies.
- **R8 (L8)** Pick a datastore in the first RFC; PostgreSQL with an index on code and a partitioned click table fits 10M URLs and 1,000 writes/s on modest hardware. SQLite would make "single `docker compose up`" simplest but its single writer is a risk at NFR-3 rates.
- **R9 (L6)** Prefix the API with `/api/v1/` so a later accounts feature can change contracts without breaking v1 clients.
- **R10 (L7)** Add a load test for NFR-1/NFR-3/NFR-8, a migration tool for schema changes, and a documented backup of the database volume.
- **R11 (L10)** Send `X-Robots-Tag: noindex` on analytics pages and redirect responses.
- **Implementation sequence / critical path:** URL validation and storage (FR-1, FR-19, NFR-6) → redirect and click recording (FR-6..FR-8, NFR-1, NFR-9) → ownership model (OQ-1) → custom aliases and expiry (FR-2, FR-3) → analytics (FR-9..FR-13) → UI (FR-18) → rate limiting and blocklist (FR-16, NFR-4) → OpenAPI docs and Docker (FR-17, NFR-7). The redirect path is the critical path: every performance NFR and every analytics feature depends on its schema.

## 3. Why each change was made

| Change in PRD.md | Why |
|---|---|
| Product Type section | So downstream commands apply the same checks without reclassifying; skips are visible. |
| FR/NFR IDs | Features and RFCs cite them; `trace-check.py` reads them. |
| FR-6 302 + no-store (D1) | H1. |
| FR-2 shared namespace and reserved words (D3) | M4. |
| FR-3 UTC, future-only | L4; a past expiry would create a dead link at birth. |
| FR-4/FR-5 point to OQ-1 | H2 -- the user must choose the ownership model. |
| FR-8, FR-12 "Unknown" country | M2, H4. |
| FR-14 includes analytics | "REST API for all operations" in Scope covers analytics, not only management. |
| FR-15 consistent error body | Needed for the error outcomes added to the Shorten journey. |
| FR-18 web UI | M9; implied by Goals and Journeys but never a requirement. |
| FR-19 validation (D5) | M5. |
| NFR-1 to NFR-9 | Original NFRs given IDs; NFR-8/NFR-9 promoted from Success Metrics so they can be tested. |
| NFR-7 `docker compose` (D2) | L1. |
| Delete journey, error outcomes in Shorten journey | Delete had no journey; failures had no user-visible outcome. |
| Decisions section | Records D1-D6 with what was rejected, so later edits do not undo them. |
| Open Questions OQ-1..OQ-15 | Every user-only gap, marked (assumption) because nobody could be asked. |

## 4. Quality Assessment

| Dimension | Original | Improved | Note |
|---|---|---|---|
| Completeness | 5/10 | 7/10 | Ownership, privacy, validation and UI bars were missing; now present as requirements or explicit open questions. Capped until the open questions are answered. |
| Clarity | 6/10 | 8/10 | Contradictory scale numbers and untestable metrics remain open (OQ-3, OQ-8). |
| Feasibility | 6/10 | 7/10 | Six weeks is plausible for the scope; NFR-1 vs NFR-9 is unproven until a load test. |
| User-Focus | 7/10 | 8/10 | Good personas and journeys; bot filtering and error outcomes now serve them. |

## Self-check

- Counts recounted from the tables above: 5 High, 9 Medium, 10 Low; PRD.md defines FR-1 to FR-19 and NFR-1 to NFR-9 (28 requirements), D1-D6, OQ-1 to OQ-15.
- Every finding's cross-reference to a D/OQ/FR/NFR was checked against PRD.md.
- `trace-check.py` was run on the project (`python3 trace-check.py .`): 28 requirements, 0 features, 0 rules, 0 RFCs; 0 failures, 0 warnings. Feature coverage is not checked yet because FEATURES.md does not exist.
