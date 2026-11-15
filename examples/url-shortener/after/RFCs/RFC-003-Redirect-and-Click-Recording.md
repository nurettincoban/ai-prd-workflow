# RFC-003: Redirect and Click Recording

**Features**: F10, F11, F12, F13, F15
**Depends on**: RFC-001, RFC-002
**Rules**: ARCH-1, ARCH-2, ARCH-6, ARCH-9, DATA-4, DATA-5, DATA-8, DATA-9, API-9, SEC-8, SEC-11, SEC-12, PRIV-1, PRIV-2, PERF-1, PERF-2, PERF-4, ERR-2, ERR-3, LOG-2, OPS-5, STACK-4, TEST-1, TEST-2, TEST-4, COMP-2, OPS-4
**Complexity**: High

## Summary

The hot path. `GET /{code}` looks up a live short URL and answers 302 to its destination with `Cache-Control: private, no-store` (F10), or 404 for expired, deleted and unknown codes without saying which (F11). Before answering a 302 it durably inserts one click with timestamp, referrer, user-agent, country and a bot flag (F12, F15); the country comes from an in-process GeoLite2 lookup on the client IP, which is then discarded (F13). Analytics never break a redirect (ERR-3).

## Technical Approach

### Request flow

```
GET /:code      (a plain parameter route with no Fastify constraint)
  if code does not match ^[0-9A-Za-z]{3,30}$: reply notFound()      # same response as an unknown code; no DB query
  now = clock.now()
  try link = await db.findLiveLinkByCode(code)  # one indexed read (PERF-1)
        -- SELECT id, destination, expires_at FROM short_urls WHERE code = $1 AND deleted_at IS NULL
  catch e:                                       # cold read: a lookup failure was unhandled
       request.log.error({event:"redirect_lookup_failed", code, err: e.message})
       reply 503, Retry-After: 5, Cache-Control: no-store, minimal HTML page   # no destination, so no redirect is possible
       # the pool's connectionTimeoutMillis (1 s, RFC-001) bounds the wait for a connection
  if !link or (link.expires_at != null and link.expires_at <= now):
       reply 404 not-found page, Cache-Control: no-store; record nothing           (F11)
  if request.method == "HEAD":
       reply 302 with the same headers, no body; record nothing                   (assumption below)
  click = {
     short_url_id: link.id,
     clicked_at:   now,
     referrer:      truncate(header "referer" ?? "", 2048),
     referrer_host: hostOf(referer) ?? "",          # lower-cased URL.hostname; "" if missing/unparseable
     user_agent:    truncate(header "user-agent" ?? "", 1024),
     country:       safe("geo_lookup_failed", () => geo.countryOf(request.ip), null),
     is_bot:        safe("bot_check_failed", () => botDetector.isBot(userAgent), false)
  }
  # safe(event, fn, fallback): try fn(); on throw, request.log.warn({event, code, err: e.name}) and return fallback (ERR-2, ERR-3)
  try: await withTimeout(db.insertClick(click), 2000)   # awaited before the 302 (PERF-2, NFR-9)
  catch e: request.log.error({event: e is timeout ? "click_write_timeout" : "click_write_failed", code, err: e.message})
     # still redirect (ERR-3). F12's "counted": failures are counted by counting these events in the logs (LOG-2);
     # a metrics counter is F34, which is deferred.
     # The 2 s bound (assumption) stops a stalled database from hanging redirects. A timed-out insert may still
     # commit later; that is harmless, because it can only make stored clicks outnumber answered redirects.
  reply 302, Location: link.destination, Cache-Control: private, no-store
```

- `Location` comes only from the stored `destination` (SEC-12); no part of the request path or query is appended (assumption: query strings on the short URL are dropped, not forwarded -- forwarding would let anyone add parameters to someone else's link).
- The client IP is read only from `request.ip` (SEC-8; RFC-010 configures `trustProxy`) and passed only to `geo.countryOf` (PRIV-2). It is never assigned to `click`, logged, or put in an error (PRIV-1).
- **HEAD** (assumption): Fastify exposes HEAD for GET routes; a HEAD returns the same 302/404 status and headers but records no click, because link checkers and preview fetchers use HEAD and FR-8 is about visits. Stated in the README in RFC-012.
- Only GET and HEAD are routed; other methods on `/:code` return 404.
- `/` itself is not a code (RFC-009 serves the shorten page there). A path with more segments (`/{code}/x`) does not match `/:code` and gets the RFC-001 not-found handler, a 404.
- `notFound()` is the one 404 response for unknown, deleted, expired and malformed codes. It renders `not-found.eta` with status 404 and `Cache-Control: no-store`, so these cases differ in nothing except the `Date` header.
- The 404 page is `src/views/not-found.eta` from RFC-001; this RFC only sets its headers.

Queries in `src/db/clicks.ts` and `src/db/short-urls.ts` use bound parameters (DATA-8). `findLiveLinkByCode` relies on the unique index on `code`.

### Country lookup (F13)

- `src/integrations/geo/geo-lookup.ts`: `export interface GeoLookup { countryOf(ip: string): string | null }` returning an ISO 3166-1 alpha-2 code (upper-case) or `null` (PRIV-2).
- `src/integrations/geo/maxmind-geo.ts`: holds a `maxmind` `Reader<CountryResponse>` opened once with `maxmind.open(path)` (PERF-4). `countryOf(ip)`: if `ip` matches `^::ffff:(\d{1,3}(\.\d{1,3}){3})$` (case-insensitive), use the captured IPv4 address. Then return `reader.get(ip)?.country?.iso_code ?? null`, which is `null` for private and reserved addresses and for invalid input.
- `src/integrations/geo/null-geo.ts`: always `null`. Used when no license key is configured, until the database has downloaded, and in tests (TEST-4).
- `src/integrations/geo/geolite2-download.ts` (OPS-5). This runs only when `LINKSNIP_GEOLITE2_LICENSE_KEY` is set:
  - **Endpoint** (decided after the cold read; assumption, based on MaxMind's direct-download documentation): `GET https://download.maxmind.com/geoip/databases/GeoLite2-Country/download?suffix=tar.gz` with HTTP basic auth `<LINKSNIP_GEOLITE2_ACCOUNT_ID>:<LINKSNIP_GEOLITE2_LICENSE_KEY>`, following redirects (MaxMind answers with a redirect to a storage URL) and using `AbortSignal.timeout(60000)`. Requests go only to MaxMind and the host it redirects to (SEC-11). If MaxMind's documented endpoint differs when this is implemented, change this RFC first. `LINKSNIP_GEOLITE2_ACCOUNT_ID` is required whenever the license key is set; a key without an account ID makes startup exit, naming the account-ID variable. The base URL is a constructor parameter of the downloader, not a config variable, so tests point it at a local HTTP server.
  - **Processing**: gunzip with `node:zlib`, then extract the single `*.mmdb` entry with the minimal ustar reader in `src/integrations/geo/tar-extract.ts` (512-byte headers; no new dependency, STACK-4). Write it to `<LINKSNIP_GEOLITE2_DIR>/GeoLite2-Country.mmdb.tmp`, rename it to `GeoLite2-Country.mmdb` (atomic), and swap the reader.
  - **Lifecycle** (cold read): at startup, if `GeoLite2-Country.mmdb` exists it is opened immediately, before `listen`, even if stale. Its age is `clock.now() - file mtime`. If there is no file, or it is 7 days old or more, a download starts **after** `listen`, so startup never waits on MaxMind. During a download the current reader, if any, keeps serving. Countries are `null` only while no file has ever been loaded. A scheduler job, `geolite2-refresh`, runs every 24 h (`runAtStart: false`) and downloads when the file is 7 days old or more. MaxMind's GeoLite2 license requires keeping the data current; weekly refresh is an assumption. Any failure logs `geoip_download_failed` without the key or account ID and keeps the current reader.
  - OPS-5 says "downloaded at startup". Here the download is *triggered* at startup and completes after `listen`. RFCS.md flags OPS-5 for rewording to match.
- The mmdb is never committed or baked into the image (OPS-5); `.gitignore` and `.dockerignore` gain `*.mmdb`.

### Bot detection (F15)

- `src/integrations/bots/bot-detector.ts`: `export interface BotDetector { isBot(userAgent: string): boolean }`.
- Default implementation uses the `isbot` package's default list (RULES stack, 5.2.3). An empty user-agent counts as a bot (assumption: real browsers always send one; isbot's own default for empty strings must be checked and overridden if it differs).
- `LINKSNIP_BOT_PATTERNS_FILE` (optional): path to a UTF-8 file with one regular-expression source per line. Blank lines and lines starting with `#` are ignored. When set, it **replaces** the default list. Each line is compiled with `new RegExp(line, "i")` (case-insensitive) and `isBot(ua)` is `patterns.some(r => r.test(ua))`. This path does not use isbot at all (cold read: the isbot export name was unverified). Startup exits, naming the variable, if the file is unreadable, a pattern is invalid, or the file has no patterns: an empty list would silently count every bot as a human (assumption). An empty user-agent is a bot whichever list is in use.
- The flag is computed once at click time and stored in `clicks.is_bot`; analytics exclude bot clicks (RFC-006, RFC-007). The bot check is in-process and does no I/O (PERF-1).

### Configuration added (also added to `.env.example` and the README table, OPS-4)

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `LINKSNIP_GEOLITE2_LICENSE_KEY` | no | unset | MaxMind license key; unset → every country is Unknown |
| `LINKSNIP_GEOLITE2_ACCOUNT_ID` | when the license key is set | unset | MaxMind account ID |
| `LINKSNIP_GEOLITE2_DIR` | no | `/var/lib/linksnip/geoip` | Directory for the downloaded `.mmdb`. `compose.yaml` mounts the named volume `linksnip-geoip` here, so restarts reuse the file instead of downloading it again. A volume is not baked into the image, so OPS-5 is respected. The Dockerfile creates the directory owned by `node`. |
| `LINKSNIP_BOT_PATTERNS_FILE` | no | unset | Replacement bot pattern list |

### Wiring

`AppDeps` gains `geo: GeoLookup` (a mutable holder so the downloader can swap the reader) and `botDetector: BotDetector`. `src/routes/redirect.ts` registers the route; it is registered after all other routes so fixed paths (`/health`, `/api/...`, `/static/...`, `/docs`) win (Fastify matches static segments before parameters anyway; the order makes intent explicit).

### Durability and latency

The awaited insert (PERF-2) is the NFR-9 guarantee: a 302 is never sent for a click that is not committed (the insert runs in autocommit; PostgreSQL's default `synchronous_commit = on` must not be changed). RFC-004 load-tests whether this meets NFR-1; if it does not, OQ-7 is reopened -- this RFC must not quietly buffer writes.

## File Structure

```
src/routes/redirect.ts
src/db/clicks.ts                      (insertClick)
src/db/short-urls.ts                  (findLiveLinkByCode added)
src/integrations/geo/geo-lookup.ts  src/integrations/geo/maxmind-geo.ts  src/integrations/geo/null-geo.ts
src/integrations/geo/geolite2-download.ts  src/integrations/geo/tar-extract.ts
src/integrations/bots/bot-detector.ts
src/config.ts  .env.example  README.md   (variables added)
compose.yaml  Dockerfile                (linksnip-geoip volume and directory)
.gitignore  .dockerignore                (*.mmdb)
test/unit/tar-extract.test.ts  test/unit/bot-detector.test.ts  test/unit/referrer-host.test.ts
test/integration/redirect.test.ts  test/integration/click-recording.test.ts  test/integration/geolite2-download.test.ts
test/fixtures/GeoLite2-Country-Test.mmdb   # MaxMind's published test database (from the MaxMind-DB repo's test-data), not real data
```

The test `.mmdb` fixture is MaxMind's own test database, which is licensed for this use; it is the only `.mmdb` committed (assumption: it does not fall under OPS-5, which is about the real GeoLite2 data). If its license is unclear when implementing, generate the fixture instead and record the choice here.

## Implementation Considerations

- **Edge cases**: `Referer` that is not a URL (`android-app://...` parses; `garbage` does not) → `referrer` kept as sent, `referrer_host` `""`; IPv6 clients; IPv4-mapped IPv6 (`::ffff:1.2.3.4`) must resolve like the IPv4 address; a code that exists but whose month partition is missing → insert fails, `click_write_failed`, 302 still sent.
- **Expiry boundary**: `expires_at <= now` is expired; tests set the fake clock to exactly `expires_at` and to 1 ms before it.
- **Testing**: real PostgreSQL (TEST-1); fake `GeoLookup` returning fixed countries; a test that drops the current partition to force an insert failure; a test using the MaxMind test database for `maxmind-geo.ts`; the downloader is tested against a local HTTP server serving a tar.gz built in the test (TEST-4: no real network).
- **Performance**: one read + one insert; no per-request file I/O (PERF-4); bot regex compiled once.
- **Privacy/compliance**: no IP stored or logged (PRIV-1); GeoLite2 attribution and license terms documented in RFC-012.
- **Third-party**: `maxmind` and `isbot` (both in RULES stack); MaxMind's download service.

## Acceptance Criteria

**F10 -- redirect**
1. `GET /{code}` for a live link returns 302, `Location` equal to the stored destination, `Cache-Control: private, no-store`, and never 301 (D1).
2. A query string on the request (`/{code}?utm=x`) does not change `Location` (SEC-12). `/{code}/x` returns 404.
3. Two consecutive GETs for the same code from the same client both return 302 and create two `clicks` rows (F10, F12).
4. `HEAD /{code}` returns the same status and headers as GET and creates no `clicks` row.
5. Each GET 302 performs exactly one `short_urls` read and one `clicks` insert, counted through an instrumented pool. Spies on `globalThis.fetch`, `node:http.request`, `node:https.request` and `node:net.connect` (other than the pool's own connections) record zero calls during the request (PERF-1).

**F11 -- 404**
6. An unknown code, a code with `deleted_at` set, a code whose `expires_at` equals or precedes now, and a malformed code (`/ab`) each return 404 with an identical body and identical headers apart from `Date`, including `Cache-Control: no-store` (F11, DATA-4).
6a. If `findLiveLinkByCode` throws (the test stops the database), the response is 503 with `Retry-After: 5` and `Cache-Control: no-store`, `redirect_lookup_failed` is logged, and no click is attempted.
7. With a fake clock 1 ms before `expires_at` the link redirects; at exactly `expires_at` it returns 404.
8. A 404 records no click.
9. `/{x}` where `x` does not match `^[0-9A-Za-z]{3,30}$` (e.g. `/ab`, `/a-b`) returns 404 without querying the database.

**F12 -- click recording**
10. Each GET 302 inserts one row with `clicked_at` = the clock's now (UTC), `referrer` = the `Referer` header (or `''`), `referrer_host` = its lower-cased hostname (or `''`), `user_agent` (or `''`), `country`, `is_bot`.
11. The insert completes before the 302 is sent: a test that pauses the insert observes no response until it resumes (PERF-2, NFR-9).
12. If the insert throws (the test drops the month's partition), the response is still 302 to the destination, and one log line with `event: "click_write_failed"` and the code is written. If the insert takes longer than 2 s (the test wraps the pool with a delay), the 302 is sent after about 2 s and `click_write_timeout` is logged (ERR-3, LOG-2).
13. Referrer values over 2,048 characters and user-agents over 1,024 are truncated, not rejected.
14. No `clicks` column, log line or error message produced by this route contains the client IP. The test sends requests with Fastify `inject({ remoteAddress: "203.0.113.9" })` and searches the stored row and every captured log line for `203.0.113.9` (PRIV-1, DATA-9).

**F13 -- country**
15. With a `GeoLookup` returning `"DE"`, the click's `country` is `DE`; with `null`, it is SQL `NULL` (PRIV-2).
16. A geo lookup that throws yields `country = NULL` and logs `geo_lookup_failed`. A bot detector that throws yields `is_bot = false` and logs `bot_check_failed`. In both cases the redirect still succeeds (ERR-2, ERR-3).
17. Without `LINKSNIP_GEOLITE2_LICENSE_KEY` the app starts, makes no request to MaxMind, and records every country as `NULL` (OPS-5).
18. With a key and an account ID set and the downloader pointed at a local test server: if there is no file, the download starts after `listen`, sends basic auth `<account>:<key>`, extracts `GeoLite2-Country.mmdb`, and swaps the reader. A corrupt archive or an HTTP error logs `geoip_download_failed` (with neither secret in the line) and keeps the previous reader. With a fake clock, a file whose mtime is 6 days old is opened and not downloaded; at 7 days the `geolite2-refresh` job downloads it again. A license key without an account ID makes startup exit, naming `LINKSNIP_GEOLITE2_ACCOUNT_ID`.
19. `maxmind-geo.ts` against the MaxMind test database resolves a known test IPv4 and its IPv4-mapped IPv6 form to the same country, and a private address to `null`.
20. `*.mmdb` is in `.gitignore` and `.dockerignore`; no real GeoLite2 database is committed or in the image (OPS-5).

**F15 -- bots**
21. A request with a known crawler user-agent (e.g. `facebookexternalhit/1.1`, `Twitterbot/1.0`, `Slackbot-LinkExpanding 1.0`) is recorded with `is_bot = true`; a current desktop Chrome user-agent with `false`; an empty user-agent with `true`.
22. With `LINKSNIP_BOT_PATTERNS_FILE` pointing at a file containing `^MyCrawler`, both `MyCrawler/2` and `mycrawler/2` are bots and `facebookexternalhit/1.1` is not, because the file replaces the default list. An empty user-agent is still a bot. An unreadable file, an invalid regex, or a file with only comments and blank lines exits at startup naming the variable.

**Shared**
23. The new variables are in `src/config.ts`, `.env.example` and the README table, and the OPS-4 test passes.
24. Every listed file exists; tests are named with their feature ID (`"F10: ..."` .. `"F15: ..."`) (TEST-2); each implemented assumption (HEAD, dropped query strings, empty UA = bot, weekly refresh) has a comment citing it (COMP-2).
