# RFC-010: Rate Limiting and Client IP

**Features**: F8
**Depends on**: RFC-002, RFC-003, RFC-009
**Rules**: SEC-8, SEC-9, API-3, API-4, ARCH-6, NAME-5, PRIV-1, LOG-2, TEST-6, TEST-2, OPS-4, STACK-5, COMP-2, UI-5, ARCH-9
**Complexity**: Medium

## Summary

Implements FR-16 as OQ-6 assumes: every `/api/*` request and every UI form submission shares a budget of 100 requests per minute per client IP; redirects have their own, much higher abuse limit (`LINKSNIP_REDIRECT_RATE_LIMIT`, default 6,000/min); `/health`, `/static/*` and the Swagger UI are not limited (SEC-9). The client IP is `request.ip` with Fastify's `trustProxy` set only to the configured proxies, so a forged `X-Forwarded-For` from an untrusted client has no effect (SEC-8). Limits are per instance and kept in memory (STACK-5, F8).

## Technical Approach

### Client IP (SEC-8)

- `LINKSNIP_TRUSTED_PROXIES`: comma-separated IPs/CIDRs (e.g. `10.0.0.0/8,172.16.0.0/12`). Parsed in `src/config.ts`; every entry is validated as an IPv4/IPv6 address or CIDR, else startup exits naming the variable. Passed to Fastify as `trustProxy: string[]`; unset → `trustProxy: false`. Never `true`.
- All code reads the client IP only from `request.ip` (RFC-003 already does). A unit test greps `src/` for `x-forwarded-for` (case-insensitive) and allows it only in the logger's redact list.

### Limiter

`@fastify/rate-limit` provides two budgets (assumption: "100 requests per minute per client IP" means one shared budget across the API and UI writes, not 100 per endpoint):

| Budget | Routes | Max | Window | Key |
|---|---|---|---|---|
| `api` | every route under `/api/` (all methods, including unmatched `/api/` paths), `POST /shorten` | `LINKSNIP_API_RATE_LIMIT` (default 100) | 1 minute | `request.ip` |
| `redirect` | `GET`/`HEAD /:code` | `LINKSNIP_REDIRECT_RATE_LIMIT` (default 6,000) | 1 minute | `request.ip` |

**Mechanism** (decided after the cold read): the routes are registered in two encapsulated Fastify contexts, and each context registers `@fastify/rate-limit` with `global: true`. A global registration uses one store and one `keyGenerator` (`request.ip`) for every route in its context:
- **context `api`**: every `/api/` route, `POST /shorten`, and the `/api/` not-found handler (registered with `setNotFoundHandler({ preHandler: app.rateLimit() }, ...)`, so unmatched `/api/...` paths count too). `max: LINKSNIP_API_RATE_LIMIT` (default 100).
- **context `redirect`**: `GET /:code` and its automatic `HEAD` route, which share one counter. `max: LINKSNIP_REDIRECT_RATE_LIMIT`.

Everything else (`/`, `/analytics/:code`, `/health`, `/static/*`, `/docs*`) sits outside both contexts and is never limited.

AC 2 is the definition of the shared budget. If the pinned plugin version turns out to key its counters per route even in global mode, replace the plugin with a small fixed-window limiter in `src/rate-limit.ts`: a `Map<key, {count, resetAt}>` driven by the injected `Clock` (ARCH-9), with no new dependency. That case also needs a RULES change, because SEC-9 names the plugin, so record it in RFCS.md.

**Hook position**: the `api` context sets the plugin option `hook: "preHandler"`, so the limiter runs after body parsing. `POST /shorten` can then re-render the form with the submitted values. Requests rejected by body parsing or validation never reach the limiter and are not counted (assumption).

**Window in tests**: `buildApp` accepts `deps.rateLimitWindowMs` (default 60,000). Tests pass a short window, e.g. 500 ms, rather than faking the plugin's internal timer. This is not a configuration variable. `GET` UI pages (`/`, `/analytics/:code`) are not limited, per OQ-6's "UI form submissions" (assumption; they are reads that cost about what an API analytics call does, and are exposed to the same abuse -- flagged in RFCS.md).

### Responses on limit

Both contexts set the plugin's `errorResponseBuilder` to return `new ApiError(429, "RATE_LIMITED", "Rate limit exceeded: <max> requests per minute. Retry after <N> seconds.")`. `<max>` is the context's own limit, so the redirect budget never shows "100". The plugin sets `Retry-After`. RFC-001's error handler gains a 429 branch that formats the error by surface:
- **`/api/` routes:** the JSON error body with code `RATE_LIMITED` (API-3, API-4). `RATE_LIMITED` is added to `src/errors.ts`.
- **`POST /shorten`:** `renderShortenForm(reply, request.body, RATE_LIMITED, 429)` from RFC-009. The body is available because the hook runs at `preHandler` (UI-5).
- **Redirect:** `src/views/rate-limited.eta`, a minimal HTML "Too many requests" page, with `Cache-Control: no-store`. No click is recorded.

**Logging:** `src/rate-limit.ts` keeps a `Map<"budget:ip", windowEnd>`. A rejection logs `{event: "rate_limited", budget, route}` at `info` only when the key is absent or its `windowEnd` has passed, so each IP is logged at most once per window per budget. The log never carries the IP (PRIV-1, LOG-2). Entries whose window has passed are evicted on every insert, which bounds memory.
- `X-RateLimit-*` headers are sent on limited routes (the plugin default), so API clients can pace themselves.

### Configuration (src/config.ts, `.env.example`, README; OPS-4)

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `LINKSNIP_TRUSTED_PROXIES` | no | unset (no proxy trusted) | Proxies whose `X-Forwarded-For` is believed |
| `LINKSNIP_REDIRECT_RATE_LIMIT` | no | `6000` | Redirects per minute per IP (SEC-9); integer 1-10,000,000 |
| `LINKSNIP_API_RATE_LIMIT` | no | `100` | Shared API and form-post budget per minute per IP. The default is FR-16's value. It exists so load tests (RFC-011) can make the limiter inert, and the README says not to change it in production. Integer 1-1,000,000. RFCS.md flags this against FR-16's fixed number (assumption). |

`LINKSNIP_TRUSTED_PROXIES` entries are trimmed. An empty entry (`a,,b`, or a trailing comma) is an error, and so is a non-integer or out-of-range limit. Each error exits at startup naming the variable.

The README explains that behind a reverse proxy the operator **must** set `LINKSNIP_TRUSTED_PROXIES`, otherwise every request appears to come from the proxy and shares one budget; and that limits are per instance, so N instances allow N× the rate.

## File Structure

```
src/rate-limit.ts                (plugin registration, budgets, onExceeded logging, 429 formatting)
src/app.ts                       (register; trustProxy from config)
src/app.ts                       (two encapsulated contexts, 429 branch in the error handler)
src/views/rate-limited.eta
src/errors.ts  src/config.ts  .env.example  README.md
test/integration/rate-limit.test.ts  test/unit/client-ip-usage.test.ts
test/e2e/shorten-rate-limit.spec.ts
```

## Implementation Considerations

- **Edge cases**: IPv6 clients each get their own counter per full address (assumption: no /64 aggregation in v1.0; noted as a weakness against IPv6 address rotation); restart resets counters (in-memory).
- **Testing**: Fastify `inject` with `remoteAddress` to simulate clients; forged `X-Forwarded-For` from a non-trusted address; trusted proxy (`remoteAddress` in the configured CIDR) forwarding two different client IPs that get separate budgets.
- **Interaction with load tests**: RFC-004 sets `LINKSNIP_REDIRECT_RATE_LIMIT` and RFC-011 sets `LINKSNIP_API_RATE_LIMIT` to inert values in `load/compose.load.yaml`.
- **Third-party**: `@fastify/rate-limit` (RULES stack).

## Acceptance Criteria

1. From one client IP, 100 requests to `/api/v1/...` within a minute succeed (or fail for their own reasons) and request 101 returns 429 with `Retry-After` and the error body with code `RATE_LIMITED` (F8, SEC-9).
2. The budget is shared: 60 `POST /api/v1/urls` + 40 `GET /api/v1/urls/{code}/analytics` + 1 `POST /shorten` from one IP in a minute → the 101st request is 429.
3. A different client IP has its own fresh budget. With `deps.rateLimitWindowMs = 500`, the first client can make requests again after waiting 600 ms.
4. Request 101 of `POST /shorten` re-renders the shorten form with status 429, `Retry-After`, the user's values and the "Too many requests" message (F25, UI-5).
5. Budgets are separate. After one IP has exhausted its `api` budget (101st API request is 429), 1,000 redirects from that IP in the same window still return 302. With `LINKSNIP_REDIRECT_RATE_LIMIT=10`, the 11th redirect in a window returns 429 with `Retry-After` and the `rate-limited.eta` page, records no click, and the message says "10 requests per minute". GET and HEAD on `/:code` count against the same redirect counter.
6. With `LINKSNIP_API_RATE_LIMIT=5` and `LINKSNIP_REDIRECT_RATE_LIMIT=5`, 200 requests from one IP within one window to each of `/health`, `/static/css/site.css`, `/docs`, `/` and `/analytics/{code}` all return a non-429 status (SEC-9).
6a. Unmatched `/api/v1/nope` requests count against the `api` budget. With `LINKSNIP_API_RATE_LIMIT=5`, the 6th returns 429.
7. With `LINKSNIP_TRUSTED_PROXIES` unset, a request from `203.0.113.5` with `X-Forwarded-For: 198.51.100.7` is keyed on `203.0.113.5`; repeating it with different forged headers does not reset the budget (TEST-6, SEC-8).
8. With `LINKSNIP_TRUSTED_PROXIES=10.0.0.0/8`, requests from `10.0.0.2` carrying `X-Forwarded-For: 198.51.100.7` and `198.51.100.8` get separate budgets.
9. An invalid entry in `LINKSNIP_TRUSTED_PROXIES` exits at startup naming the variable; `trustProxy` is never `true`.
10. `test/unit/client-ip-usage.test.ts` fails if the string `x-forwarded-for` (case-insensitive) appears in any file under `src/` other than `src/logger.ts`, which holds the redact list. Comments count, so don't mention it elsewhere.
11. Five rejected requests from one IP in one window produce exactly one `rate_limited` line, which carries the budget and route and not the IP (PRIV-1). The next window's first rejection logs again.
12. All three variables are in `src/config.ts`, `.env.example` and the README table. The README explains trusted proxies and per-instance limits, and says `LINKSNIP_API_RATE_LIMIT` is for load testing only (OPS-4). `a,,b` in `LINKSNIP_TRUSTED_PROXIES`, `LINKSNIP_REDIRECT_RATE_LIMIT=0` and `LINKSNIP_API_RATE_LIMIT=1.5` each make startup exit, naming the variable.
13. Tests are named `"F8: ..."` (TEST-2); the shared-budget, unlimited-GET-pages and IPv6 assumptions carry comments citing OQ-6 / this RFC (COMP-2).
