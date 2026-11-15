# Product Requirements Document: LinkSnip URL Shortener

## Overview
LinkSnip is a web-based URL shortening service that converts long URLs into short, shareable links and provides click analytics. It targets individual developers and small teams who need a simple, self-hostable alternative to commercial URL shorteners.

## Product Type
**Web app + service/API.** LinkSnip has a web UI (create links, view analytics) and a public REST API that does everything the UI does, so it takes the checks of both types.

Checks applied: authorization per resource, data model and migrations, accessibility, responsive layout, browser support, page-load budget, SEO for public pages (web app); API contracts and versioning, authentication and authorization, rate limiting and abuse, idempotency and retries, observability, data retention and privacy, SLOs and scaling (service/API).

Skipped checks:
- **Binary size** -- a server-rendered/self-hosted web service ships no client binary.
- **Offline sync** -- every operation needs the server; there is no offline client.
- **Sessions** -- v1.0 has no user accounts (see Out of Scope), so there are no login sessions to probe. Authorization of destructive operations is still checked (see OQ-1).
- **UI / responsive design / accessibility skips from the service/API row are NOT taken** -- the web-app half of the product needs them.

## Goals and Objectives
- Provide fast, reliable URL shortening with sub-100ms redirect latency (NFR-1)
- Deliver basic click analytics (total clicks, referrers, geographic data)
- Support the storage scale in NFR-6 (see OQ-3: the original text said both "10,000+ active short URLs" and "10M+ URLs")
- Offer a clean, minimal UI and a REST API for programmatic access

## Scope

### In Scope (v1.0)
- URL creation (generate short code or accept custom alias)
- URL redirection with click tracking
- Click analytics dashboard
- Expiration dates for short URLs
- REST API for all operations
- Rate limiting and basic abuse prevention

### Out of Scope (v1.0)
- User accounts and authentication (all URLs are public)
- Team workspaces and collaboration features
- Custom domains
- QR code generation
- Bulk URL import
- Editing the destination of an existing short URL

## User Personas

### Developer Dave
- Builds side projects, wants quick URL shortening via API
- Values: simplicity, speed, self-hosting capability
- Pain points: commercial tools are bloated and expensive for personal use

### Marketer Maria
- Shares links on social media, needs to track engagement
- Values: click analytics, custom aliases for branded links
- Pain points: needs basic analytics without complex enterprise tools

## Functional Requirements

Priorities: every item below is **Must** for v1.0, because the PRD's In Scope list commits to all of them (see D4). Proposed demotions are in OQ-11.

### URL Management
- **FR-1**: Create a short URL from a long URL, with an auto-generated 7-character base62 code (`[0-9A-Za-z]`, case-sensitive). Codes are generated randomly and retried on collision with any existing code or alias.
- **FR-2**: Create a short URL with a custom alias of 3-30 alphanumeric characters. The alias must be unique across all existing codes and aliases and must not be a reserved path used by the UI or API (for example `api`, `docs`, `static`, `health`); a conflict returns an error and never overwrites the existing link (see D3).
- **FR-3**: Set an optional expiration date-time on a short URL at creation time. The value is stored in UTC and must be in the future.
- **FR-4**: Delete a short URL. Who may delete is an open question (OQ-1).
- **FR-5**: List created short URLs with metadata (code, destination, created, expires, total clicks). Who may list is an open question (OQ-1).

### Redirection
- **FR-6**: Redirect a short URL to its original URL with HTTP **302** (not 301; see D1). Responses carry `Cache-Control: private, no-store` so that browsers and proxies do not cache the redirect.
- **FR-7**: Return 404 for expired, deleted or non-existent short URLs.
- **FR-8**: Record click metadata on each redirect: timestamp (UTC), referrer, user-agent, and country. How the country is derived and whether the client IP is kept are open questions (OQ-4, OQ-5).

### Analytics
- **FR-9**: View total click count per URL.
- **FR-10**: View a click timeline per URL (clicks per day/week/month), bucketed in UTC unless OQ-12 decides otherwise.
- **FR-11**: View top referrers per URL.
- **FR-12**: View a geographic breakdown of clicks per URL (country level; clicks with no resolvable country count as "Unknown").
- **FR-13**: Filter all analytics views by date range.

### API
- **FR-14**: REST API covering every URL management operation (FR-1 to FR-5) and every analytics view (FR-9 to FR-13).
- **FR-15**: JSON request and response format, with a consistent error body for every 4xx/5xx response.
- **FR-16**: Rate limiting of 100 requests per minute per client IP. Which endpoints it covers, and how the client IP is determined behind a reverse proxy, are open (OQ-6).
- **FR-17**: API documentation published as an OpenAPI specification, with a browsable Swagger UI.

### Web UI
- **FR-18**: A web UI that supports the two user journeys below: shorten a URL (FR-1 to FR-3) and view analytics for a short URL (FR-9 to FR-13). Follows from the Goals ("clean, minimal UI") and the "Shorten a URL" journey, which starts in the web UI.

### Input validation
- **FR-19**: Accept only absolute `http` and `https` destination URLs. Reject other schemes (`javascript:`, `data:`, `file:`, ...), malformed URLs, and URLs that point back at the LinkSnip instance itself (redirect loops). Follows from NFR-5 (see D5).

## Non-Functional Requirements
- **NFR-1**: Performance -- redirect latency < 100ms at p95, measured server-side, on the reference hardware named in OQ-8.
- **NFR-2**: Availability -- 99.9% uptime target for the redirect endpoint. What this means for a single self-hosted instance is open (OQ-8).
- **NFR-3**: Scalability -- handle 1,000 redirects per second per instance while meeting NFR-1.
- **NFR-4**: Security -- check destination URLs against a malware/phishing blocklist at creation time and reject listed URLs. The provider is open (OQ-2).
- **NFR-5**: Security -- validate and sanitize all inputs (URLs, aliases, query parameters); escape all user-supplied values (destinations, referrers, user-agents) when rendered in the web UI.
- **NFR-6**: Storage -- store at least 10M short URLs per instance, with their click data, while meeting NFR-1 and NFR-3. (Original text; the competing 10,000 figure is OQ-3.)
- **NFR-7**: Deployment -- Docker-based; a single `docker compose up` starts a working instance, and a first deployment takes under 5 minutes (see D2).
- **NFR-8**: API response time < 200ms at p95 for all management and analytics endpoints (promoted from Success Metrics so it can be tested).
- **NFR-9**: Click-tracking durability -- no recorded click is lost once the redirect response has been sent. Whether this can hold alongside NFR-1 is open (OQ-7).

## User Journeys

### Shorten a URL
1. User opens the web UI or calls the API
2. Pastes a long URL, optionally sets a custom alias and expiration
3. Receives a short URL immediately, or a clear error (invalid URL, blocklisted URL, alias taken or reserved, rate limit exceeded)
4. Copies and shares the short URL

### View Analytics
1. User navigates to the analytics page for a specific short URL
2. Sees total clicks, click timeline chart, top referrers, and geographic breakdown
3. Filters by date range to analyze specific campaigns

### Delete a URL
1. User calls the delete endpoint (or uses the UI) for a short URL, presenting whatever credential OQ-1 settles on
2. The short URL returns 404 from then on (FR-7)

## Success Metrics
- Average redirect latency < 50ms (in addition to the p95 bound in NFR-1)
- API response time < 200ms for all endpoints (NFR-8)
- Zero data loss on click tracking (NFR-9)
- Successful deployment in under 5 minutes via Docker (NFR-7)

## Timeline
- **Week 1-2**: Core URL shortening and redirection
- **Week 3-4**: Click analytics and dashboard
- **Week 5**: Custom aliases, expiration, and polish
- **Week 6**: API documentation, Docker setup, and launch

Team size and budget are not stated (OQ-10).

## Decisions

- **D1 -- Redirect with 302, not 301.** HTTP 301 is a permanent redirect that browsers cache, often indefinitely, so repeat clicks from the same browser never reach the server. That would break FR-8 (track every redirect), NFR-9 (zero data loss on click tracking), and FR-7 (an expired or deleted link would keep redirecting from cache). The PRD's own requirements settle it. Rejected: 301 (cache breaks tracking and expiry); 307 (also fine technically, but 302 is the conventional choice for shorteners and behaves identically for GET).
- **D2 -- `docker compose up`, not `docker-compose up`.** The hyphenated `docker-compose` is Compose v1, which Docker stopped supporting in 2023; current Docker ships Compose v2 as the `docker compose` plugin. The intent (one command to run) is unchanged. Rejected: keeping the v1 command, which fails on a fresh Docker install.
- **D3 -- Aliases share one namespace with generated codes and exclude reserved paths.** FR-1 and FR-2 both produce paths at the same URL root, so a 7-character alias can collide with a future generated code, and an alias like `api` would shadow the API. Uniqueness across both, plus a reserved-word list, follows from the PRD. Rejected: separate path prefixes for aliases (makes branded links longer, against Maria's need).
- **D4 -- Everything In Scope is Must for v1.0.** The PRD lists them all as in scope for v1.0 with a six-week timeline. This records the PRD's commitment rather than a new prioritization; OQ-11 proposes demotions for the user to accept or reject.
- **D5 -- Only http/https destinations; no self-links.** NFR-5 requires validating all inputs; a shortener that accepts `javascript:` URLs or links to itself becomes an XSS or redirect-loop vector. Rejected: accepting any URI scheme.
- **D6 -- Requirements carry permanent IDs (FR-n, NFR-n).** Added so features and RFCs can cite them. Never renumber; retire an ID instead of reusing it.

## Open Questions

Items marked **(assumption)** were not answered by a person in this review (it ran non-interactively). Each states the assumption downstream work should make until answered, and what it changes.

- **OQ-1 (assumption) -- Who may delete and list URLs?** With no accounts and "all URLs are public", FR-4 lets anyone delete anyone's link and FR-5 lets anyone enumerate every link. *Assumption:* creating a URL returns a secret management token, shown once; delete requires that token; listing all URLs requires an operator admin token set in configuration; analytics for a single code stays public. *Changes:* adds a token to the create response and the delete call, and an admin credential to deployment config.
- **OQ-2 (assumption) -- Which malware/phishing blocklist?** *Assumption:* a pluggable checker interface, with Google Safe Browsing (Lookup API v4) as the first implementation using an operator-supplied API key; if no key is configured, the check is disabled and the UI/API say so. Safe Browsing's terms restrict the free API to non-commercial use, so a commercial deployment needs Google Web Risk or another provider. Links are checked only at creation; re-checking existing links is out of scope. *Changes:* NFR-4 becomes conditional on configuration.
- **OQ-3 (assumption) -- Which scale target: 10,000 active URLs or 10M stored URLs?** The original Goals said "10,000+ active short URLs" and the NFRs said "10M+ URLs". *Assumption:* design storage for 10M stored URLs (NFR-6); "active" (receiving clicks in a given month) is assumed to be at most 10,000. *Changes:* index and storage design; a 10M-row click table per year at NFR-3 rates is far larger than the URL table.
- **OQ-4 (assumption) -- What click data is personal data, and how long is it kept?** Click records with IP addresses and user-agents are personal data under GDPR and similar laws. *Assumption:* the client IP is used to derive the country at click time and is then discarded, never stored; user-agents are stored; raw click events are kept 13 months and per-day aggregates indefinitely, both configurable by the operator. *Changes:* FR-8 storage schema, a retention job, and a privacy note in the docs. Replaces the original "retain indefinitely or TTL?" question.
- **OQ-5 (assumption) -- Where does country data come from?** Self-hosted IP geolocation usually means MaxMind GeoLite2, which needs a free MaxMind account and license key to download and carries attribution terms. *Assumption:* the operator supplies a GeoLite2 license key; without one, country is recorded as "Unknown". *Changes:* FR-12 degrades gracefully; deployment docs.
- **OQ-6 (assumption) -- What does the rate limit cover, and what is the client IP?** At 100 requests/minute per IP on redirects, one office behind a NAT could be blocked from following links. *Assumption:* FR-16 applies to `/api/*` and UI form submissions, not to redirects; redirects get a separate, much higher abuse limit. The client IP is taken from `X-Forwarded-For` only when the request comes from a proxy listed in configuration. *Changes:* rate-limiter configuration and deployment docs.
- **OQ-7 (assumption) -- Can "zero click loss" (NFR-9) coexist with < 100ms p95 redirects (NFR-1)?** A synchronous, durable database write on every redirect at 1,000/s competes with the latency budget. *Assumption:* the click is written synchronously to the database within the redirect request; if load tests show this breaks NFR-1, revisit with a durable queue. *Changes:* if a buffered write is chosen instead, NFR-9 must be relaxed to a stated loss window.
- **OQ-8 (assumption) -- What hardware and measurement back NFR-1, NFR-2 and NFR-3?** For a self-hosted single instance, uptime depends on the operator. *Assumption:* NFR-1/NFR-3 are verified by a load test on a 2 vCPU / 4 GB host; NFR-2 is a design target (no single-request failure mode in LinkSnip itself), not a guarantee LinkSnip can make for operators. *Changes:* test strategy and the README's claims.
- **OQ-9 (assumption) -- Should bot and link-preview traffic count as clicks?** Social platforms fetch links to build previews, inflating Maria's numbers. *Assumption:* clicks whose user-agent matches a known-bot list are recorded but excluded from analytics by default. *Changes:* FR-9 to FR-12 query logic.
- **OQ-10 (assumption) -- Team, budget and license.** Not stated. *Assumption:* one or two developers, no budget for paid services, released under an open-source license chosen before launch. *Changes:* the six-week timeline is only credible for this scope with a small, focused team and no paid integrations.
- **OQ-11 (assumption) -- Should anything be demoted from Must?** *Assumption, if the six weeks slip:* FR-13 (date-range filter) and FR-17's Swagger UI (keeping the OpenAPI file) become Should. *Changes:* Week 4 and Week 6 scope.
- **OQ-12 (assumption) -- Time zone for timelines and expiration.** *Assumption:* everything is stored and shown in UTC in v1.0. *Changes:* FR-3 and FR-10 display.
- **OQ-13 (assumption) -- Web UI quality bars.** No accessibility, browser-support, responsive-layout or page-load target is stated. *Assumption:* WCAG 2.1 AA, the last two versions of evergreen browsers, usable at 360px width, and the create page interactive in under 2 seconds on a mid-range phone. *Changes:* FR-18 acceptance criteria.
- **OQ-14 (assumption) -- Should destinations be checked for reachability before shortening?** (Original question.) *Assumption:* no -- it adds latency, fails for links behind logins, and lets LinkSnip be used to probe internal hosts (SSRF). *Changes:* none to v1.0.
- **OQ-15 (assumption) -- Alias case sensitivity.** *Assumption:* aliases are case-sensitive like generated base62 codes (`Promo` and `promo` are different links). *Changes:* FR-2 lookup; case-insensitive aliases would need a normalized unique index.
