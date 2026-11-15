# RFC-005: Malware and Phishing Blocklist (Google Safe Browsing)

**Features**: F7
**Depends on**: RFC-002
**Rules**: ARCH-5, ARCH-6, NAME-5, API-6, SEC-11, SEC-13, PERF-5, ERR-2, ERR-4, LOG-2, PRIV-4, TEST-4, TEST-2, OPS-4, COMP-2, COMP-3, LOG-1
**Complexity**: Medium

## Summary

Adds the first real `UrlChecker`: Google Safe Browsing Lookup API v4, used when the operator sets `LINKSNIP_SAFE_BROWSING_API_KEY` (OQ-2). A listed destination is rejected with `BLOCKLISTED_URL`; with no key, or when the provider fails or times out, the link is created and reported as `blocklistStatus: "unchecked"` (fail open; R5, PERF-5). The interface, the no-op checker and the `BLOCKLISTED_URL` error already exist (RFC-002). Existing links are never re-checked (F42). F7's UI half, where the shorten page says a URL was not checked, is built and tested in RFC-009 (AC 5) from the `blocklistStatus` this RFC produces.

## Technical Approach

### Checker

`src/integrations/blocklist/safe-browsing-checker.ts` implements `UrlChecker`. Its constructor takes `{ apiKey, logger, fetch = globalThis.fetch, timeoutMs = 2000, makeSignal = (ms) => AbortSignal.timeout(ms) }`:
- `logger` is a child of `app.log`, so it is still Fastify's pino logger (LOG-1).
- `fetch` and `makeSignal` are injected so tests can capture the URL and fire the timeout deterministically. Fake timers do not control `AbortSignal.timeout`.
- `url` is the normalized destination, meaning the `href` returned by RFC-002's `validateDestination`. That is the same string that is stored and redirected to, so the verdict applies to what users are actually sent to.

```
check(url):
  body = {
    client: { clientId: "linksnip", clientVersion: APP_VERSION },
    threatInfo: {
      threatTypes: ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
      platformTypes: ["ANY_PLATFORM"],
      threatEntryTypes: ["URL"],
      threatEntries: [{ url }]
    }
  }
  try:
    res = await fetch("https://safebrowsing.googleapis.com/v4/threatMatches:find",
                      { method: "POST", headers: { "Content-Type": "application/json",
                                                    "X-Goog-Api-Key": apiKey },
                        body: JSON.stringify(body), signal: makeSignal(timeoutMs) })   # PERF-5
    if !res.ok: logger.warn({event:"blocklist_check_failed", status: res.status, host: new URL(url).hostname}); return "unchecked"
    json = await res.json()
    return (json.matches?.length ?? 0) > 0 ? "listed" : "clean"     # empty object {} = no match
  catch e:
    logger.warn({event:"blocklist_check_failed", reason: e.name, host: new URL(url).hostname}); return "unchecked"   # ERR-4, fail open
```

- The key is sent **only** in the `X-Goog-Api-Key` header, never in a `?key=` query string, so it cannot appear in a URL (PRIV-4, API-5's reasoning). Google APIs accept this header. There is no runtime fallback to the query string (cold read: a fallback would be a second request, against PERF-5). If Google rejects the header, the result is an HTTP error, which means `"unchecked"` and a log line, and the operator sees `blocklist_check_failed` in the logs.
- Failure logs carry the destination's **hostname** only, not the full URL, which is enough to investigate (ERR-2) without logging paths or query strings. They never carry the key.
- `APP_VERSION` comes from `src/version.ts`, which the `build` script generates from `package.json`'s `version`, so it exists in the runtime image. A unit test checks that it equals `package.json`.
- No retry within the request (PERF-5). The request goes only to `safebrowsing.googleapis.com` (SEC-11).
- `src/deps.ts` exports `buildDeps(config, logger)`, which `startServer` calls. A key that is set and non-empty after trimming gives a `SafeBrowsingChecker`. A key that is unset, empty or whitespace-only gives a `NoopChecker` (ARCH-5), and `blocklist_disabled` is logged once at startup.

### Configuration (added to `src/config.ts`, `.env.example`, README table; OPS-4)

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `LINKSNIP_SAFE_BROWSING_API_KEY` | no | unset | Google Safe Browsing API key; unset disables the check |

Secret: environment only (SEC-13).

### Contract effect

No change to the RFC-002 response shape: `blocklistStatus` is now `"clean"` when the provider answered with no match, and `"unchecked"` when disabled or failed. A listed URL returns 400 `BLOCKLISTED_URL` with message "This URL is on a malware or phishing blocklist and cannot be shortened." and creates no row.

### Documentation

`README.md` gets a `### Malware and phishing check` subsection: how to obtain a key, that Safe Browsing's free API is for non-commercial use only and commercial deployments need Google Web Risk or another provider (a new `UrlChecker` implementation), that the check is skipped when no key is set or the provider fails (and how that shows in the API and UI), and that links are checked only at creation (COMP-3, F42).

## File Structure

```
src/integrations/blocklist/safe-browsing-checker.ts
src/deps.ts                            (buildDeps: checker selection)
src/version.ts                         (generated at build from package.json)
src/config.ts  .env.example  README.md (variable and docs)
test/unit/safe-browsing-checker.test.ts
test/integration/create-url-blocklist.test.ts
```

## Implementation Considerations

- **Testing without network** (TEST-4): the unit test injects a `fetch` function (constructor parameter) and covers: match → `listed`; `{}` → `clean`; HTTP 400/403/429/500 → `unchecked` + log; thrown network error → `unchecked`; abort after 2 s → `unchecked` (fake timers). Integration tests use a fake `UrlChecker`.
- **Latency**: with a key configured, creation can wait up to 2 s on Google, against NFR-8's 200 ms p95 for all endpoints. This plan measures NFR-8 with the no-op checker, which excludes third-party time LinkSnip cannot control, and records that in RFC-011's result. This redefines a PRD requirement, so RFCS.md **flags NFR-8** for a PRD decision (assumption until then).
- **Licensing**: Safe Browsing terms (non-commercial) documented, not enforced.
- **Failure mode**: fail open is the FEATURES.md assumption (R5 asked for a choice); switching to fail closed later is a one-line change in the checker plus a README change.
- **Third-party**: Google Safe Browsing Lookup API v4; no new npm dependency (`fetch` is built into Node 26).

## Acceptance Criteria

1. `buildDeps` returns a `SafeBrowsingChecker` instance (`instanceof`) when `LINKSNIP_SAFE_BROWSING_API_KEY` is set. When it is unset, `""` or `"   "`, it returns a `NoopChecker` and `blocklist_disabled` is logged once (F7, ARCH-5).
2. A provider response with a non-empty `matches` array makes `POST /api/v1/urls` return 400 `BLOCKLISTED_URL` and creates no row.
3. A provider response of `{}` yields 201 with `blocklistStatus: "clean"`.
4. Each of these yields `"unchecked"` and exactly one `blocklist_check_failed` line carrying the destination hostname: HTTP 400, 403, 429 or 500; a thrown network error; and the injected signal aborting (the test fires it, standing in for the 2 s timeout). The injected `fetch` is called exactly once, so there is no retry (PERF-5, ERR-4). Through the API, the same cases give 201 with `blocklistStatus: "unchecked"`. A separate test checks that the default `makeSignal` is `AbortSignal.timeout(2000)`.
5. The request body asks for threat types `MALWARE`, `SOCIAL_ENGINEERING`, `UNWANTED_SOFTWARE` and `POTENTIALLY_HARMFUL_APPLICATION` on `ANY_PLATFORM`. Its `threatEntries[0].url` equals the `destination` in the create response (e.g. input `https://EXAMPLE.com` is checked as `https://example.com/`). `clientVersion` equals `package.json`'s version.
6. The API key appears in no log line, error message or response, and in no URL passed to `fetch`: every captured `fetch` URL is exactly `https://safebrowsing.googleapis.com/v4/threatMatches:find`, with no query string. The key appears only in the `X-Goog-Api-Key` header (PRIV-4).
7. Every request the checker makes, as captured by the injected `fetch`, goes to `safebrowsing.googleapis.com`. The checker never requests the destination itself (SEC-11; the MaxMind download in RFC-003 is a separate, allowed request).
8. The variable is in `src/config.ts`, `.env.example` and the README table; the OPS-4 test passes.
9. README `### Malware and phishing check` states: how to get a key; Safe Browsing's free API is non-commercial only and commercial deployments need Google Web Risk or another provider; behavior when disabled or failing; links are checked only at creation (COMP-3, F42).
10. Tests are named `"F7: ..."` (TEST-2); fail-open carries a comment citing R5 / FEATURES.md Assumptions (COMP-2).
