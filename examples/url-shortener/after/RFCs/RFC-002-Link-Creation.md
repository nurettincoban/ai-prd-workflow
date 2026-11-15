# RFC-002: Link Creation (Generated Codes, Aliases, Expiration, Validation)

**Features**: F1, F2, F3, F6
**Depends on**: RFC-001
**Rules**: ARCH-3, ARCH-4, ARCH-5, ARCH-8, ARCH-9, NAME-4, DATA-2, DATA-3, DATA-8, API-1, API-2, API-3, API-4, API-6, API-9, SEC-1, SEC-2, SEC-3, SEC-4, SEC-11, ERR-1, ERR-2, LOG-2, PRIV-4, TEST-1, TEST-2, TEST-6, COMP-2, PRIV-1, TEST-4, ERR-4
**Complexity**: Medium

## Summary

`POST /api/v1/urls` creates a short URL: it validates the destination (F6), optionally accepts a custom alias (F2) and an expiration (F3), generates a 7-character base62 code when no alias is given (F1), issues a one-time management token stored only as a hash, and reports whether the destination was blocklist-checked. This RFC defines the `UrlChecker` interface and ships only the no-op checker (every link is `"unchecked"`); RFC-005 adds Google Safe Browsing behind the same interface. The service function written here is the one the web UI (RFC-009) also calls (ARCH-4).

## Technical Approach

### Components

- `src/services/validation.ts`: `validateDestination(input: string, publicHost: string): string` (SEC-1) and `validateAlias(input: string): string` (SEC-2); both throw `ApiError`.
- `src/services/code-generator.ts`: `generateCode(): string` -- 7 characters, each `ALPHABET[crypto.randomInt(62)]`, `ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"` (SEC-3).
- `src/services/tokens.ts`: `issueManagementToken(): { token: string; hash: Buffer }` -- `crypto.randomBytes(32)` → base64url (43 chars), hash = SHA-256 of the token's UTF-8 bytes (SEC-4); `hashToken(token)` and `tokensMatch(hashA, hashB)` (`crypto.timingSafeEqual` on two 32-byte buffers). RFC-008 uses these for delete.
- `src/integrations/blocklist/url-checker.ts`: `export interface UrlChecker { check(url: string): Promise<"clean" | "listed" | "unchecked"> }` (ARCH-5); `src/integrations/blocklist/noop-checker.ts`: always `"unchecked"`. `AppDeps` gains `urlChecker`; `src/server.ts` wires the no-op checker in this RFC.
- `src/services/short-url-service.ts`: `createShortUrl(deps, input: CreateInput): Promise<CreatedShortUrl>`.
- `src/db/short-urls.ts`: `insertShortUrl(pool, row): Promise<InsertResult>` returning the row, or `{ conflict: true }` on SQLSTATE `23505` for `short_urls_code_key`.
- `src/routes/api/create-url.ts`: the route with TypeBox schemas (API-2).
- Service dependencies (cold read): `createShortUrl(deps, input)` receives `deps = { config, pool, clock, urlChecker, logger, generateCode, reservedAliases }`. `logger` is the request's child logger (`request.log`), passed in by the route as a plain logger object, which ARCH-3 allows because it is not the request. `generateCode` defaults to `code-generator.ts`'s function and `reservedAliases` defaults to `RESERVED_ALIASES`. Tests inject both to force collisions (AC 3) and reserved-word hits (AC 4).

### Request validation (cold read: Fastify's default Ajv would hide errors)

Fastify's default Ajv setup coerces types and can strip unknown properties, so `{"url": 123}` would become `"123"` and an `"alais"` typo would vanish. `src/app.ts` therefore installs `setValidatorCompiler` with two Ajv instances, chosen by `httpPart`:
- `body`: `coerceTypes: false`, `removeAdditional: false`, `useDefaults: false`, `allErrors: false`
- `querystring` and `params`: `coerceTypes: true` (query values are always strings), `removeAdditional: false`

The body schema is deliberately shallow: `{ url: string, alias?: string | null, expiresAt?: string | null }` with `additionalProperties: false`, and no `pattern`, `format` or `maxLength`. Those checks belong to the service, so that each failure gets its specific code (`INVALID_URL`, `INVALID_ALIAS`, `INVALID_EXPIRATION`) instead of a generic `VALIDATION_FAILED`. The OpenAPI descriptions (RFC-011) document the constraints in prose. An empty string or `null` for `alias` or `expiresAt` means the field is absent. The web form sends empty strings for blank fields, and treating them as absent keeps the API and UI consistent. (assumption)

### API contract

`POST /api/v1/urls` with `Content-Type: application/json`:

```json
{ "url": "https://example.com/long/path?q=1", "alias": "Promo2026", "expiresAt": "2026-12-31T23:59:59Z" }
```

- `url` (string, required). `alias` (string, optional). `expiresAt` (string, optional, RFC 3339 date-time **with** an offset: `Z` or `±hh:mm`). Unknown fields → 400 `VALIDATION_FAILED` (`additionalProperties: false`), so a typo such as `"alais"` is not silently ignored (assumption).

`201 Created`:

```json
{
  "code": "Promo2026",
  "shortUrl": "https://lnk.example.com/Promo2026",
  "destination": "https://example.com/long/path?q=1",
  "createdAt": "2026-11-15T10:00:00.000Z",
  "expiresAt": "2026-12-31T23:59:59.000Z",
  "managementToken": "3q2-7wEXAMPLEexampleEXAMPLEexampleEXAMPLEab",
  "blocklistStatus": "unchecked"
}
```

`expiresAt` is `null` when not set. `destination` is the normalized form returned by the WHATWG `URL` parser's `href` (e.g. host lower-cased) -- this is what the redirect sends. `shortUrl` = `${LINKSNIP_PUBLIC_SCHEME}://${LINKSNIP_PUBLIC_HOST}/${code}`. All timestamps are UTC ISO 8601 ending in `Z` (DATA-2). The response carries `Cache-Control: no-store` because it contains the token (assumption, mirrors UI-7).

Errors (all with the RFC-001 body; codes added to `src/errors.ts`):

| Code | Status | Condition |
|---|---|---|
| `INVALID_URL` | 400 | Not parseable by `new URL()`, protocol not exactly `http:`/`https:`, empty host, or longer than 2,048 characters (message says which) |
| `SELF_LINK` | 400 | Destination host equals `LINKSNIP_PUBLIC_HOST` (redirect loop, D5) |
| `INVALID_ALIAS` | 400 | Alias does not match `^[0-9A-Za-z]{3,30}$` |
| `ALIAS_RESERVED` | 400 | `alias.toLowerCase()` is in `RESERVED_ALIASES`; message says the alias is reserved |
| `ALIAS_TAKEN` | 409 | Unique violation on insert for a custom alias |
| `INVALID_EXPIRATION` | 400 | Not a valid date-time, has no offset, or is `<=` now |
| `BLOCKLISTED_URL` | 400 | Checker returns `"listed"` (reached only once RFC-005 ships a real checker; defined here so the UI can map it) |
| `INVALID_BODY` / `VALIDATION_FAILED` | 400 | From RFC-001 |

### Algorithm

```
createShortUrl(deps, {url, alias?, expiresAt?}):
  destination = validateDestination(url, config.publicHost)          # throws INVALID_URL / SELF_LINK
  if alias given: code = validateAlias(alias)                        # throws INVALID_ALIAS / ALIAS_RESERVED
  expires = expiresAt ? parseExpiration(expiresAt, deps.clock) : null # throws INVALID_EXPIRATION
  try verdict = await deps.urlChecker.check(destination)
  catch e: deps.logger.warn({event:"blocklist_check_failed", reason: e.name}); verdict = "unchecked"
     # checkers should not throw (ARCH-5), but the service defends so a buggy checker fails open (ERR-4)
  if verdict == "listed": throw ApiError(400, BLOCKLISTED_URL, ...)
  {token, hash} = issueManagementToken()
  now = deps.clock.now()
  if alias given:
     r = insertShortUrl({code: alias, destination, is_alias: true, hash, verdict, now, expires})
     if r.conflict: throw ApiError(409, ALIAS_TAKEN, ...)            # never overwrites (D3)
  else:
     for attempt in 1..5:
        code = generateCode()
        if code.toLowerCase() in RESERVED_ALIASES: continue          # a 7-char reserved word is possible later
        r = insertShortUrl({code, ..., is_alias: false})
        if not r.conflict: break
        log.warn({event:"code_collision_retry", attempt})
     if still conflict: log.error({event:"code_generation_failed"}); throw ApiError(500, INTERNAL_ERROR)
  return {..., managementToken: token, blocklistStatus: verdict}     # verdict is "clean" or "unchecked"

validateDestination(input, publicHost):
  if input.length > 2048: throw INVALID_URL("longer than 2,048 characters")
  # cold read: the WHATWG parser is lenient -- it trims whitespace, removes tabs and newlines, treats "\" as "/",
  # and accepts "http:example.com". Reject these up front so that what is stored is what the user typed (assumption):
  if /[\s\x00-\x1F\x7F\\]/.test(input): throw INVALID_URL("URL contains spaces, control characters or backslashes")
  if !/^https?:\/\//i.test(input): throw INVALID_URL("only http:// and https:// URLs are allowed")
  try u = new URL(input) catch: throw INVALID_URL("not a valid absolute URL")
  if u.protocol not in {"http:", "https:"}: throw INVALID_URL("only http and https URLs are allowed")
  if u.hostname == "": throw INVALID_URL("URL has no host")
  if u.host.toLowerCase() == publicHost: throw SELF_LINK          # u.host omits default ports already
  return u.href

parseExpiration(s, clock):            # RFC 3339 date-time, as decided after the cold read (assumption)
  m = /^(\d{4})-(\d{2})-(\d{2})[Tt](\d{2}):(\d{2}):(\d{2})(\.\d+)?([Zz]|[+-]\d{2}:\d{2})$/.exec(s)
  if !m: throw INVALID_EXPIRATION            # seconds required; offset required; T/Z either case (RFC 3339 §5.6)
  check ranges: month 1-12; day 1..daysInMonth(year, month) (leap years included); hour 0-23; minute 0-59;
                second 0-59 (leap second 60 rejected); offset hours 0-23, minutes 0-59 -- else INVALID_EXPIRATION
                # explicit, because new Date("2026-02-31T...") silently rolls over into March
  fraction: any number of digits, truncated (not rounded) to milliseconds
  d = Date.UTC(fields) minus the offset
  if d <= clock.now(): throw INVALID_EXPIRATION("must be in the future")
  return d
```

Note on the 2,048 limit: it is measured on the input string before parsing (assumption: the user-visible length, F6). Because whitespace is rejected rather than trimmed, `" https://example.com"` returns 400 `INVALID_URL`.

Generated-code collision probability at 10M stored codes is about 10^7 / 3.5×10^12 ≈ 3×10^-6 per attempt, so five attempts never realistically fail; the bound exists so a bug cannot loop forever.

### Idempotency

`POST /api/v1/urls` is not idempotent: a client that retries after a timeout may create two links (assumption; no Idempotency-Key header in v1.0). This is acceptable because links are cheap and the client keeps whichever token it received; stated in the OpenAPI description (RFC-011).

### Logging

`link_created` at `info` with `code`, `isAlias`, `blocklistStatus` -- never the token (PRIV-4) or the client IP (PRIV-1). Validation rejections are not logged individually (they are counted in request logs by status).

## File Structure

```
src/services/validation.ts  src/services/code-generator.ts  src/services/tokens.ts
src/services/short-url-service.ts
src/integrations/blocklist/url-checker.ts  src/integrations/blocklist/noop-checker.ts
src/db/short-urls.ts
src/routes/api/create-url.ts
src/app.ts                            (per-httpPart Ajv validator compiler)
src/errors.ts                         (codes added)
test/unit/validation.test.ts  test/unit/code-generator.test.ts  test/unit/tokens.test.ts
test/integration/create-url.test.ts
```

## Implementation Considerations

- **Edge cases**: IDN hosts (`https://bücher.example/`) are accepted and normalized to punycode by `URL`; `http://localhost/` and private IPs are accepted (no reachability check, SEC-11, F43) -- LinkSnip never fetches them; userinfo (`https://user:pass@host/`) is accepted as a valid absolute URL (assumption; the PRD does not forbid it); a URL with leading or trailing whitespace is rejected with `INVALID_URL`, never trimmed (assumption: the input is used exactly as sent).
- **Self-link on other hostnames** (an IP or alternate DNS name for the same instance) is not detected; only `LINKSNIP_PUBLIC_HOST` is compared (SEC-1). A loop through such a name still terminates in the browser's redirect limit.
- **Testing**: property test (fast-check) that every `generateCode()` result matches `^[0-9A-Za-z]{7}$`; integration tests with a fake `UrlChecker` returning each verdict (TEST-4); a collision test that pre-inserts the code returned by a stubbed generator and asserts a retry; TEST-6 cases for `javascript:`, `data:`, `file:` and self-links; reserved aliases in any case (`API`, `Docs`).
- **Security**: tokens never logged; `Math.random` absent (SEC-3); no outbound request to the destination (SEC-11).
- **Rate limiting** of this endpoint arrives in RFC-010.
- **Third-party**: none new.

## Acceptance Criteria

**F1 -- generated codes**
1. `POST /api/v1/urls {"url":"https://example.com/a"}` returns 201 with `code` matching `^[0-9A-Za-z]{7}$`, `shortUrl` = scheme + public host + `/` + code, `destination`, `createdAt` (ISO 8601, `Z`), `expiresAt: null`, a 43-character base64url `managementToken`, and `blocklistStatus: "unchecked"` (no-op checker) (F1, API-6).
2. Codes are case-sensitive: creating aliases `Abc1234` and `abc1234` both return 201, and two rows exist, each with its own destination (DATA-3). Retrieval through the redirect is tested in RFC-003.
3. When the generator's first output collides with an existing code or alias, the insert's unique violation triggers a retry with a new code; the existing link is unchanged; the response carries the new code. After 5 consecutive collisions the request fails with 500 `INTERNAL_ERROR` and logs `code_generation_failed` (F1, DATA-3).
4. With `reservedAliases` injected as `["zzzzzzz"]` and a generator that returns `ZZZZZZZ` and then `abc1234`, the response code is `abc1234`, and no row with `ZZZZZZZ` exists.
5. `generateCode` uses `crypto.randomInt` (SEC-3); a fast-check property test asserts the format over 10,000 samples.
6. `management_token_hash` equals SHA-256 of the returned token. A search of every `text` column of `short_urls` for the token string finds nothing, and neither does a search of every log line captured during the request (SEC-4, PRIV-4).
7. The 201 response carries `Cache-Control: no-store`.

**F2 -- custom alias**
8. `alias: "Promo2026"` returns 201 with `code: "Promo2026"`; `Promo2026` and `promo2026` can both be created as different links (OQ-15).
9. Aliases of 2 or 31 characters, or containing any character outside `[0-9A-Za-z]` (e.g. `pro-mo`, `promo!`, `prömo`), return 400 `INVALID_ALIAS` (SEC-2).
10. Aliases `api`, `API`, `Docs`, `static`, `HEALTH` return 400 `ALIAS_RESERVED` with a message saying the alias is reserved (SEC-2, ARCH-8).
11. An alias equal to any existing code or alias (exact case) returns 409 `ALIAS_TAKEN` and the existing row is byte-for-byte unchanged (D3).

**F3 -- expiration**
12. `expiresAt: "2026-12-31T23:59:59+02:00"` is stored as `2026-12-31T21:59:59Z` and returned with `Z` (DATA-2).
13. An `expiresAt` equal to now or in the past returns 400 `INVALID_EXPIRATION`. So does each of: no offset (`2026-12-31T23:59:59`), a date only (`2026-12-31`), no seconds (`2026-12-31T23:59Z`), an impossible date (`2026-02-31T10:00:00Z`, `2026-02-29T10:00:00Z`), second `60`, and garbage. These are accepted: `2028-02-29T10:00:00Z` (a leap year), `2026-12-31t23:59:59z` (lower case), and `2026-12-31T23:59:59.123456Z` (stored as `.123`). Tests use a fake `Clock` (ARCH-9).
13a. `alias: ""`, `alias: null`, `expiresAt: ""` and `expiresAt: null` are treated as absent (201, generated code, `expiresAt: null`).
14. After the app is built, its route table has no `PUT` or `PATCH` route and no route other than `POST` on `/api/v1/urls` that writes to `short_urls` (F41).

**F6 -- destination validation**
15. `javascript:alert(1)`, `data:text/html,x`, `file:///etc/passwd`, `ftp://example.com/` return 400 `INVALID_URL` (TEST-6).
16. These return 400 `INVALID_URL`: `example.com`, `/relative`, `https://`, `http://exa mple.com`, `http:example.com`, `https:\\\\example.com\\x`, `" https://example.com"` (leading space) and `"https://example.com/\n"`.
17. A URL of exactly 2,048 characters is accepted; 2,049 is rejected with 400 `INVALID_URL`.
18. With `LINKSNIP_PUBLIC_HOST=lnk.example.com`, `https://LNK.example.com/x` and `http://lnk.example.com:80/x` return 400 `SELF_LINK`; `https://other.example.com/x` is accepted (SEC-1, D5).
19. `{"url": 123}` (not coerced to a string), a missing `url`, and `{"url":"https://e.com","alais":"x"}` (unknown field, not stripped) each return 400 `VALIDATION_FAILED`, never 500 and never 201. A non-JSON body returns 400 `INVALID_BODY` (F6, F22).
20. Creating a link makes no outbound network request (SEC-11). The integration test spies on `globalThis.fetch`, `node:http.request` and `node:https.request` and asserts zero calls during `POST /api/v1/urls`.

**Shared**
21. `UrlChecker` is the interface in `src/integrations/blocklist/url-checker.ts`; `createShortUrl` depends only on it; a fake checker returning `"listed"` makes the endpoint return 400 `BLOCKLISTED_URL` and creates no row; `"clean"` yields `blocklistStatus: "clean"` (ARCH-5). A checker that throws yields 201 with `blocklistStatus: "unchecked"` and a log line with `event: "blocklist_check_failed"`.
22. `createShortUrl` lives in `src/services/short-url-service.ts` and does not import `fastify`. A grep test finds `INSERT INTO short_urls` only in `src/db/short-urls.ts`, and finds `insertShortUrl` imported only by `short-url-service.ts` (ARCH-3, ARCH-4).
23. The route declares TypeBox schemas for body and for every response status (201, 400, 409, 500) (API-2).
24. Every listed file exists; tests are named with the feature ID (`"F1: ..."`, `"F2: ..."`, `"F3: ..."`, `"F6: ..."`) (TEST-2).
