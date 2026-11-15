# RFC-008: Delete with Management Token and Operator Listing

**Features**: F4, F5
**Depends on**: RFC-002, RFC-003, RFC-007
**Rules**: ARCH-3, ARCH-4, ARCH-6, DATA-4, DATA-8, API-1, API-2, API-3, API-4, API-5, API-7, API-9, NAME-4, NAME-5, SEC-4, SEC-5, SEC-13, PRIV-4, ERR-1, LOG-2, OPS-4, TEST-2, COMP-2, PRIV-1
**Complexity**: Medium

## Summary

Closes PRD-REVIEW H2 (anyone can delete or enumerate every link) with the OQ-1 ownership model. `DELETE /api/v1/urls/{code}` soft-deletes a link when the caller presents the management token issued at creation (RFC-002); the link then returns 404 everywhere and its code is never reissued (F4, DATA-4). `GET /api/v1/urls` lists links with keyset pagination, only for the operator's admin token, and is disabled when none is configured (F5, SEC-5). Total clicks per row come from RFC-007's `totalClicksFor`.

## Technical Approach

### Delete (F4)

`DELETE /api/v1/urls/{code}` with `Authorization: Bearer <managementToken>` (API-5; never a query or body field).

```
deleteShortUrl(deps, code, presentedToken | null):
  # params schema: code is a plain string, so Fastify validation never answers before this handler
  if code does not match ^[0-9A-Za-z]{3,30}$: throw ApiError(404, NOT_FOUND)   # same as unknown, like the redirect
  row = db.findLiveLinkByCode(code)                   # deleted_at IS NULL
  if !row or (row.expires_at != null and row.expires_at <= clock.now()):
       throw ApiError(404, NOT_FOUND)                 # unknown, deleted or expired (API-4)
  if presentedToken is null or not well-formed base64url of 43 chars:
       throw ApiError(403, FORBIDDEN, "A valid management token is required.")
  if !tokensMatch(hashToken(presentedToken), row.management_token_hash):    # timingSafeEqual (SEC-4)
       throw ApiError(403, FORBIDDEN, same message)
  updated = db.softDelete(row.id, clock.now())
        -- UPDATE short_urls SET deleted_at = $2 WHERE id = $1 AND deleted_at IS NULL
  if updated == 0: throw ApiError(404, NOT_FOUND)     # lost a race with another delete
  log.info({event:"link_deleted", code})              # never the token (PRIV-4)
  → 204 No Content
```

- Order: existence is checked before the token, so a wrong token on an unknown code is 404 and on a live code is 403. Codes are public, so this reveals nothing new (assumption).
- **Expired links return 404 for DELETE** (cold read; API-4 gives 404 for expired codes). The redirect and analytics already return 404 for them, so DELETE cannot be used to tell expired links apart from deleted ones.
- Bearer parsing (`src/services/tokens.ts` `parseBearer(headers)`): exactly one `Authorization` header with the value `<scheme> <token>`. The scheme is matched case-insensitively against `Bearer`, separated by exactly one space, and the token must match `^[A-Za-z0-9_-]{43}$` for management tokens or be any non-empty string for the admin token. Anything else, including repeated `Authorization` headers, means no valid token, which gives 403, not 400 (assumption: one answer for every bad credential).
- Delete is idempotent in effect: a second delete returns 404 and changes nothing.
- The row and its clicks are kept (DATA-4); analytics for the code return 404 from then on (RFC-007), and the code can never be created again because the row still holds the unique `code` (F4).

### List (F5)

`GET /api/v1/urls?limit=50&cursor=<opaque>` with `Authorization: Bearer <LINKSNIP_ADMIN_TOKEN>`.

```
# Authorization runs in this route's preValidation hook, before Fastify validates the querystring (cold read:
# otherwise ?limit=0 with no token would answer 400 instead of 403):
adminAuth(request):
  if config.adminToken unset/empty: throw ApiError(403, FORBIDDEN, "Listing is disabled on this instance.")   # SEC-5
  if !presentedToken or !timingSafeEqual(sha256(presentedToken), sha256(config.adminToken)): throw 403 FORBIDDEN
       # hashing both sides gives equal-length buffers without leaking the admin token's length (SEC-4)

listShortUrls(deps, {limit = 50, cursor}):
  if limit not integer 1..100: throw 400 VALIDATION_FAILED       (API-7; schema-enforced, after auth)
  afterId = cursor ? decodeCursor(cursor) : null
     # cursor = base64url of the decimal id. It is unsigned on purpose: any cursor that decodes to an integer
     # 1..9223372036854775807 is a valid position (only the operator can list, so a forged position exposes
     # nothing). Not base64url, not decimal, <= 0, or > bigint max → 400 INVALID_CURSOR
  rows = db.listLiveLinks(afterId, limit + 1)
        -- SELECT id, code, destination, created_at, expires_at FROM short_urls
        --  WHERE deleted_at IS NULL AND ($1::bigint IS NULL OR id < $1) ORDER BY id DESC LIMIT $2
  page = rows[0:limit]; nextCursor = rows.length > limit ? encodeCursor(page.last.id) : null
  totals = analytics.totalClicksFor(page.ids)                    # RFC-007
  → 200 { items: [{ code, shortUrl, destination, createdAt, expiresAt, totalClicks }], nextCursor }
```

- Newest first (assumption). Deleted links are excluded. Expired links are included with their `expiresAt` so the operator can see them (assumption). `expiresAt` is always present, and `null` when the link has none. `shortUrl` is built as in RFC-002: `${LINKSNIP_PUBLIC_SCHEME}://${LINKSNIP_PUBLIC_HOST}/${code}`.
- `managementToken` and its hash are never in the response (F5).
- RFC-001 defines the partial index `short_urls_live_idx` as `ON short_urls (id) WHERE deleted_at IS NULL`. It is a btree on `id`, and PostgreSQL scans it backwards for `ORDER BY id DESC LIMIT n`, so each page reads about `n` index entries even at 10M rows (NFR-8).

### Errors added to `src/errors.ts`

| Code | Status | When |
|---|---|---|
| `FORBIDDEN` | 403 | Missing, malformed or wrong management/admin token; listing disabled |
| `INVALID_CURSOR` | 400 | Cursor not produced by this API |

### Configuration (src/config.ts, `.env.example`, README; OPS-4)

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `LINKSNIP_ADMIN_TOKEN` | no | unset (listing disabled) | Operator token for `GET /api/v1/urls`. Only unset or empty disables listing (F5, SEC-5). A token shorter than 32 characters is accepted but logs `admin_token_weak` at startup (assumption; cold read: exiting would contradict F5) |

Secret: environment only (SEC-13); redacted from logs because it travels only in `Authorization` (PRIV-1, PRIV-4).

## File Structure

```
src/routes/api/delete-url.ts  src/routes/api/list-urls.ts
src/services/short-url-service.ts   (deleteShortUrl, listShortUrls)
src/services/tokens.ts              (bearer parsing helper)
src/db/short-urls.ts                (softDelete, listLiveLinks; findLiveLinkByCode reused from RFC-003)
src/errors.ts  src/config.ts  .env.example  README.md
test/integration/delete-url.test.ts  test/integration/list-urls.test.ts
```

## Implementation Considerations

- **Edge cases**: two concurrent deletes with the right token give one 204 and one 404. A token for link A presented for link B gives 403. A token with trailing whitespace gives 403, because tokens are not trimmed (assumption).
- **Security**: constant-time comparison (SEC-4); token only in the header (API-5); 403 bodies are identical for missing and wrong tokens so a caller cannot distinguish them.
- **Rate limiting** (RFC-010) slows online token guessing; a 256-bit token makes guessing infeasible regardless.
- **Testing**: create via the API to get a real token; assert redirect and analytics return 404 after delete; list with and without the admin token configured; paginate across 120 links.
- **Third-party**: none.

## Acceptance Criteria

**F4 -- delete**
1. `DELETE /api/v1/urls/{code}` with `Authorization: Bearer <token from create>` returns 204 with no body; afterwards `GET /{code}` and the analytics endpoint return 404 (F4, F11).
2. Without an `Authorization` header, with a malformed header, or with a wrong token, the response is 403 `FORBIDDEN` with identical bodies, and the link still redirects with 302 (R2).
3. Deleting an unknown code, a code already deleted, an expired code (even with its correct token), or a malformed code (`a-b`) returns 404 `NOT_FOUND` with identical bodies and changes nothing (API-4).
4. The deleted row remains in `short_urls` with `deleted_at` set and its clicks remain; creating a link with the deleted code as alias returns 409 `ALIAS_TAKEN` (DATA-4, F4).
5. `Authorization: bearer <token>` (lower-case scheme) is accepted. These give 403: `Bearer  <token>` (two spaces), `Token <token>`, and two `Authorization` headers.
6. Token comparison uses `crypto.timingSafeEqual` on SHA-256 digests (SEC-4). The test builds the app with RFC-001's real logger configuration, captures every line from create and delete (including `link_deleted`), and finds neither token in any of them (PRIV-4). A token supplied as `?token=` or in a JSON body is ignored, and the request returns 403 (API-5).

**F5 -- list**
7. With `LINKSNIP_ADMIN_TOKEN` unset or empty, `GET /api/v1/urls` returns 403 `FORBIDDEN` for every request: one bearing any token, and one with an invalid `limit=0` (auth runs before validation) (SEC-5).
8. With it set, a request without it or with a wrong token returns 403; with it, 200 and `items` each containing exactly `code`, `shortUrl`, `destination`, `createdAt`, `expiresAt`, `totalClicks` -- no token or hash (F5).
9. `limit` defaults to 50, accepts 1..100, and 0, 101 or a non-integer returns 400 `VALIDATION_FAILED` (API-7).
10. With 120 live links, following `nextCursor` returns pages of 50, 50 and 20, newest first. The last page has `nextCursor: null`, and no link appears twice or is skipped. These cursors return 400 `INVALID_CURSOR`: `!!!`, base64url of `abc`, of `0`, and of `9223372036854775808`.
11. Deleted links are not listed; expired links are listed with their `expiresAt`.
12. For live, non-expired links, `totalClicks` equals the analytics endpoint's full-life `totalClicks`. For listed expired links, it equals a ground-truth non-bot `count(*)` taken directly in the database.
13. A `LINKSNIP_ADMIN_TOKEN` of 10 characters still enables listing, and `admin_token_weak` is logged once at startup without the token. The variable is in `src/config.ts`, `.env.example` and the README table (OPS-4).
14. Both routes declare TypeBox schemas for every response status they can return, including 429 (RFC-010) (API-2). GET performs no write (API-9).
15. Every listed file exists; tests are named `"F4: ..."` / `"F5: ..."` (TEST-2); assumptions (existence before token, newest-first, unsigned cursor, weak-token warning) carry comments citing this RFC (COMP-2).
