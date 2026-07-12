# RFC Master Index — URL Shortener

All RFCs in strict implementation order. Each RFC must be fully implemented and reviewed before starting the next.

## Implementation Roadmap

| Order | RFC | Title | Complexity | Builds Upon | Required By |
|-------|-----|-------|------------|-------------|-------------|
| 1 | [RFC-001](RFCs/RFC-001-Core-URL-Shortening.md) | Core URL Shortening and Redirection | Medium | — | RFC-002, RFC-003 |
| 2 | [RFC-002](RFCs/RFC-002-Click-Analytics.md) | Click Analytics | Medium | RFC-001 | — |
| 3 | [RFC-003](RFCs/RFC-003-Custom-Aliases-And-Expiration.md) | Custom Aliases and Expiration | Low | RFC-001 | — |

## Dependency Graph

```
RFC-001 (Core URL Shortening)
├── RFC-002 (Click Analytics)
└── RFC-003 (Custom Aliases and Expiration)
```

RFC-001 is the critical path: it establishes the database schema, API skeleton, and redirect flow that both later RFCs extend. RFC-002 and RFC-003 are independent of each other but are sequenced analytics-first because click tracking touches the redirect hot path built in RFC-001, and it is cheaper to harden that path before layering alias and expiration rules onto it.

## Feature Coverage

| RFC | Features Covered |
|-----|------------------|
| RFC-001 | F1 (Create short URL), F2 (Redirect), F4 (Delete), F8 (Docker deployment) |
| RFC-002 | F3 (Track clicks), F5 (Click count), F6 (Click timeline), F11 (Top referrers), F12 (Geographic breakdown) |
| RFC-003 | F9 (Custom aliases), F10 (Expiration dates), F13 (URL validation) |

Not yet assigned to an RFC: F7 (REST API polish incl. rate limiting), F14 (OpenAPI docs), and F15 (list URLs) — should/could-have features that would form an RFC-004 if promoted. Won't-have features (F16 user accounts, F17 custom domains, F18 QR codes) are out of scope for v1 — see [FEATURES.md](FEATURES.md).

## Status

| RFC | Status |
|-----|--------|
| RFC-001 | Not started |
| RFC-002 | Not started |
| RFC-003 | Not started |

Update this table as RFCs are implemented and reviewed (`/implement-rfc <id>` → `/review-rfc <id>`).
