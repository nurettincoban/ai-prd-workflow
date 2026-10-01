# Features: LinkSnip URL Shortener

## Summary

| Priority | Count |
|----------|-------|
| Must Have | 8 |
| Should Have | 4 |
| Could Have | 3 |
| Won't Have (v1) | 3 |

---

## Must Have

### URL Management
| ID | Feature | Complexity | Acceptance Criteria |
|----|---------|-----------|-------------------|
| F1 | Create short URL with auto-generated code | Low | Given a valid long URL, return a unique 7-char base62 short URL in < 200ms |
| F2 | Redirect short URL to original | Low | HTTP 301 redirect with < 100ms p95 latency; return 404 for invalid/expired URLs |
| F3 | Track click metadata on redirect | Medium | Capture timestamp, referrer, user-agent, and country for every redirect without adding > 10ms latency |
| F4 | Delete a short URL | Low | Deleted URLs return 404 immediately; associated analytics data is also removed |

### Analytics
| ID | Feature | Complexity | Acceptance Criteria |
|----|---------|-----------|-------------------|
| F5 | View total click count per URL | Low | Accurate count displayed on analytics page and returned via API |
| F6 | View click timeline (daily/weekly/monthly) | Medium | Chart showing click distribution over time with date range filtering |

### API & Infrastructure
| ID | Feature | Complexity | Acceptance Criteria |
|----|---------|-----------|-------------------|
| F7 | REST API for all URL operations | Medium | CRUD endpoints with JSON format, proper error codes, rate limiting (100 req/min/IP) |
| F8 | Docker deployment | Low | Single `docker-compose up` starts the full stack; service is accessible within 60 seconds |

## Should Have

| ID | Feature | Complexity | Acceptance Criteria |
|----|---------|-----------|-------------------|
| F9 | Custom aliases for short URLs | Low | Users can specify a 3-30 char alphanumeric alias; return error if alias is taken |
| F10 | Expiration dates | Low | URLs return 404 after expiration; expired URLs are cleaned up automatically |
| F11 | Top referrers per URL | Medium | Analytics page shows top 10 referrers sorted by click count |
| F12 | Geographic breakdown of clicks | Medium | Country-level click distribution via GeoIP lookup on redirect |

## Could Have

| ID | Feature | Complexity | Acceptance Criteria |
|----|---------|-----------|-------------------|
| F13 | URL validation against malware blocklists | Medium | Reject URLs flagged by blocklist service; check happens at creation time |
| F14 | OpenAPI/Swagger documentation | Low | Auto-generated API docs accessible at /docs endpoint |
| F15 | List all short URLs with metadata | Low | Paginated endpoint returning all URLs with creation date, click count, expiration |

## Won't Have (v1)

| ID | Feature | Notes |
|----|---------|-------|
| F16 | User accounts and authentication | Planned for v2 |
| F17 | Custom domains | Requires DNS integration; planned for v2 |
| F18 | QR code generation | Nice-to-have for v2 |
