# RFC-009: Web UI (Shorten and Analytics Pages)

**Features**: F9, F25, F26, F27, F29
**Depends on**: RFC-002, RFC-003, RFC-005, RFC-007
**Rules**: ARCH-1, ARCH-4, ARCH-7, ARCH-8, SEC-6, SEC-7, SEC-10, PERF-6, UI-1, UI-2, UI-3, UI-4, UI-5, UI-6, UI-7, TEST-2, TEST-6, TEST-7, TEST-8, NAME-1, COMP-1, COMP-2, ERR-4
**Complexity**: Medium

## Summary

Two server-rendered pages that cover the PRD's two UI journeys (FR-18): the shorten page at `/` (paste a URL, optional alias and expiry, get the short URL and the one-time management token, F25) and the analytics page at `/analytics/{code}` (total, timeline chart with an equivalent table, top referrers, countries, date-range filter, F26). Both meet the OQ-13 quality bars (F27), escape every user-supplied value (F9), and are kept out of search indexes along with redirects (F29). Pages call the same services as the API (ARCH-4); forms work without JavaScript (UI-4).

## Technical Approach

### Routes (`src/routes/web/`)

| Method | Path | Handler | Notes |
|---|---|---|---|
| GET | `/` | `shorten-page.ts` | Empty form |
| POST | `/shorten` | `shorten-page.ts` | `application/x-www-form-urlencoded` via `@fastify/formbody`; calls `createShortUrl` (RFC-002) |
| GET | `/analytics/:code` | `analytics-page.ts` | Query `from`, `to`, `interval`; calls `getAnalytics` (RFC-007) |

`shorten` and `analytics` are added to `RESERVED_ALIASES` (ARCH-8). `/static/js/` and `/static/css/` are served by RFC-001's static plugin.

### Shorten flow (F25)

```
POST /shorten (fields: url, alias, expiresAt)
  input = { url: url (as sent, not trimmed; RFC-002), alias: alias || undefined, expiresAt: toIso(expiresAt) }
  toIso(v):                         # <input type="datetime-local" step="1">, labelled "UTC"
     if v is undefined or "": return undefined          # blank field = no expiry
     if v matches ^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$: v = v + ":00"   # browsers omit seconds when they are zero
     return v + "Z"                 # anything else is passed through, and RFC-002 rejects it with INVALID_EXPIRATION
     # An API client must still send an offset (F3). In the UI, the "UTC" label is what makes the value unambiguous (UI-6).
  try result = createShortUrl(deps, input)
  catch ApiError e:
     reply.code(e.statusCode).view("shorten.eta", { values: submitted, error: messageFor(e.code), field: fieldFor(e.code) })
  reply.header("Cache-Control", "no-store").view("created.eta", result)       # UI-7; no redirect, so the token never sits in a URL
```

Messages (UI-5, F25) -- each tied to its field with `aria-describedby` (UI-1):

| Code | Field | Message |
|---|---|---|
| `INVALID_URL` | url | The service's message, which already says which rule failed (scheme, host, 2,048-character limit, spaces) |
| `SELF_LINK` | url | "Links to this LinkSnip instance are not allowed." |
| `BLOCKLISTED_URL` | url | "This URL is on a malware or phishing blocklist and can't be shortened." |
| `INVALID_ALIAS` | alias | "Aliases are 3–30 letters or digits." |
| `ALIAS_RESERVED` | alias | "That alias is reserved. Choose another." |
| `ALIAS_TAKEN` | alias | "That alias is already taken. Choose another." |
| `INVALID_EXPIRATION` | expiresAt | "Choose a date and time in the future (UTC)." |
| `RATE_LIMITED` | form | "Too many requests. Try again in a minute." (raised by RFC-010's limiter; mapped here) |
| `INVALID_BODY`, `VALIDATION_FAILED` | form | "Check the form fields and try again." |
| anything else (500) | form | "Something went wrong. Please try again." |

`src/routes/web/render-shorten-form.ts` exports `renderShortenForm(reply, values, error?, status = 200)`. The form handler uses it, and RFC-010 uses it for the 429 response.

The created page shows: the short URL in a read-only `<input>`, with an expiry line reading "Never expires" when `expiresAt` is null with a copy button (`static/js/copy.js`, hidden until JS loads since it only works with JS; UI-4), the destination, the expiry (UTC, UI-6), the management token in a `<code>` block with "Save this token now. It is the only way to delete this link and will not be shown again." (F25, UI-7), and, when `blocklistStatus` is `"unchecked"`, the notice "This URL was not checked against a malware blocklist." (F7, ERR-4). A link to its analytics page is included.

### Analytics page (F26)

```
GET /analytics/:code?from&to&interval
  try data = getAnalytics(deps, code, query)
  catch NOT_FOUND: 404 not-found.eta (same page as the redirect 404)
  catch INVALID_RANGE / RANGE_TOO_LARGE / VALIDATION_FAILED:
       400 analytics.eta in "error" mode: header, filter form (pre-filled with the submitted values), message; no totals, tables or chart
  # getAnalytics is RFC-007's service: the page passes the query strings from/to/interval straight through
  # (<input type="date"> already sends YYYY-MM-DD) and renders RFC-007's response object
  # (totalClicks, timeline[{start, clicks}], referrers[{host, clicks}], countries[{country, clicks}], from, to, interval).
  # The filter form is pre-filled from the response's resolved from/to/interval, so defaults are visible.
  render analytics.eta:
     header: short URL, destination (via the safe-link helper, SEC-7), "All times UTC" (UI-6)
     filter form (method="get"): from/to <input type="date">, interval <select>, submit
     total clicks
     timeline: <canvas aria-hidden="true"> + <table> with one row per bucket (UI-2)
     top referrers <table>: host or "Direct / none"
     countries <table>: country name (from a static ISO 3166-1 code → English-name map in src/views/countries.ts) or "Unknown"
     note: "Bot and link-preview traffic is excluded."
```

- Chart: `static/js/analytics-chart.js` reads the timeline `<table>` from the DOM and draws a Chart.js bar chart into the canvas; Chart.js is served from `/static/vendor/chart.umd.min.js`, copied from `node_modules/chart.js/dist/` by the build script, never a CDN (SEC-10). With JS off, the table alone conveys the data. No inline script and no data blob in the page (SEC-10).
- Only the analytics page loads Chart.js; the shorten page loads only `copy.js` (PERF-6: ≤ 10 KB gzipped JS on the create page).

### Escaping (F9)

- Eta `autoEscape: true` (SEC-6, RFC-001); `<%~` is never used with request or database values -- a lint test greps `src/views/` for `<%~` and allows it only for including partials.
- `src/views/helpers.ts` `safeHref(url)`: renders `<a href>` only if `new URL(url).protocol` is `http:` or `https:`, otherwise plain escaped text (SEC-7). Destinations, referrer hosts and any other stored value go through escaping; referrer hosts are never rendered as links (assumption: avoids a click-through to arbitrary sites from the analytics page).

### Search indexing (F29)

- The analytics page sends `X-Robots-Tag: noindex` and has `<meta name="robots" content="noindex">`.
- `src/routes/redirect.ts` (RFC-003) adds `X-Robots-Tag: noindex` to its 302 and 404 responses.

### Layout, CSS and accessibility (F27)

- `src/views/layout.eta` (from RFC-001) gains `lang="en"`, a skip link, `<main>`, a visible focus style, and the page `<title>`.
- `static/css/site.css`: mobile-first, base at 360 px, `min-width` queries for wider screens, no fixed width over 360 px (UI-3); text and focus contrast ≥ 4.5:1 / 3:1; errors shown with text and an icon, not colour alone (UI-1).
- Every input has a `<label for>`; required fields are marked in text; error summary at the top of the form with links to the fields.
- Browsers: last two versions of Chrome, Firefox, Safari and Edge (F27); no features beyond what they all support. `copy.js` uses `navigator.clipboard.writeText` and falls back to selecting the text.

### Error and not-found pages

`src/views/error.eta` and `src/views/not-found.eta` were created in RFC-001 and are restyled here with the layout. RFC-001's error handler already renders HTML for any non-`/api/` request. For a 500 the page shows "Something went wrong" and nothing internal. For a 404 it shows "This link doesn't exist or has expired."

### CSRF

The UI has no cookies, sessions or ambient credentials, so a cross-site form post can do nothing the attacker could not do by posting directly (assumption: no CSRF token needed in v1.0; revisit if accounts, F36, arrive).

## File Structure

```
src/routes/web/shorten-page.ts  src/routes/web/analytics-page.ts
src/views/layout.eta (modified)  src/views/shorten.eta  src/views/created.eta  src/views/analytics.eta
src/views/not-found.eta (modified)  src/views/error.eta (modified)  src/views/helpers.ts  src/views/countries.ts
src/views/messages.ts                    (error code → field + message map)
src/routes/web/render-shorten-form.ts
src/routes/redirect.ts                   (X-Robots-Tag added)
src/services/reserved-aliases.ts         (shorten, analytics added)
static/css/site.css  static/js/copy.js  static/js/analytics-chart.js
static/vendor/chart.umd.min.js           (build output copied from node_modules, git-ignored)
package.json                             (build step copying Chart.js)
test/integration/web-shorten.test.ts  test/integration/web-analytics.test.ts  test/unit/views-lint.test.ts
test/integration/js-budget.test.ts  test/unit/web-routes-no-validation.test.ts  test/e2e/keyboard.spec.ts  test/e2e/page-load.spec.ts
test/e2e/shorten.spec.ts  test/e2e/analytics.spec.ts  test/e2e/responsive.spec.ts
playwright.config.ts
```

## Implementation Considerations

- **Server-side validation only**: HTML `required`/`pattern` attributes may be added as conveniences, but the server is the authority (ARCH-4).
- **Page-load budget** (OQ-13): server-rendered HTML, one small CSS file and `copy.js`.
  - "Interactive" is defined as the `load` event, by which point the HTML, the CSS and `copy.js` have all loaded and been parsed. The page has no other script.
  - The mid-range phone stand-in (assumption) is applied through the Chrome DevTools Protocol, so this test runs in **Chromium only**:
    - CPU slowdown 4× (`Emulation.setCPUThrottlingRate`)
    - network emulation of 150 ms latency, 1.6 Mbps down and 750 kbps up (`Network.emulateNetworkConditions`)
    - cache disabled
  - The test asserts that `performance.getEntriesByType("navigation")[0].loadEventEnd` is below 2,000 ms. With these settings the test is meaningful even against localhost.
- **Testing**: TEST-7 (Chromium, Firefox, WebKit; axe with `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa`, zero violations), TEST-8 (360 px, `scrollWidth <= 360`), TEST-6 (`<script>` in referrer and destination render as text).
- **Compatibility**: no client framework (ARCH-7).
- **Third-party**: Chart.js (in RULES stack), served locally.

## Acceptance Criteria

**F25 -- shorten page**
1. `GET /` renders a form with labelled fields for URL (required), alias and expiry (UTC), which posts to `/shorten` and works with JavaScript disabled (UI-4).
2. A valid submission renders `created.eta` with the short URL, destination, expiry in UTC, the management token with the "will not be shown again" warning, and a link to the analytics page; the response has `Cache-Control: no-store`; the URL bar never contains the token (UI-7, F25).
3. With JS enabled, the copy button is shown in all three browsers. In Chromium, which is the only one where Playwright can grant clipboard permission, clicking it puts the short URL on the clipboard. In Firefox and WebKit, clicking it selects the URL text in the input (the fallback). Without JS the button is not shown.
4. Each failure re-renders the form: invalid URL (including a 2,049-character URL, which shows the service's length message), self link, blocklisted URL, alias taken, alias reserved, invalid alias, and past expiry. Each re-render uses the service error's HTTP status, keeps the user's values, and attaches the specific message from the table above to its field via `aria-describedby` (UI-5, UI-1). (The rate-limited case is verified in RFC-010.)
5. When `blocklistStatus` is `"unchecked"`, the created page shows "This URL was not checked against a malware blocklist." (F7).
6. `2026-12-31T23:59` and `2026-12-31T23:59:30` entered in the form are stored as `…T23:59:00Z` and `…T23:59:30Z`. A blank expiry creates a link with no expiry, and the created page shows "Never expires". The label says "UTC" (UI-6).
7. The form handler calls `createShortUrl` and contains no validation of its own: `test/unit/web-routes-no-validation.test.ts` fails if any file in `src/routes/web/` imports `src/services/validation.ts` or `RESERVED_ALIASES`, or contains a regular-expression literal (ARCH-4).

**F26 -- analytics page**
8. `GET /analytics/{code}` shows total clicks, a timeline chart plus a `<table>` with the same buckets (UI-2), top referrers ("Direct / none" for null), countries by name ("Unknown" for null), "All times UTC", and the bot-exclusion note.
9. The date-range filter is a GET form, pre-filled with the resolved range and interval. Submitting it updates all views with the same range. An invalid range returns status 400 and shows the message and the filter with the submitted values, but no totals, tables or chart.
10. Unknown, deleted and expired codes render the not-found page with 404.
11. Chart.js loads only on the analytics page, from `/static/vendor/`. `test/integration/js-budget.test.ts` parses the `<script src>` tags in `GET /`, gzips each referenced file with `node:zlib` at level 9, and fails if the total exceeds 10,240 bytes (PERF-6). Also, pages contain no inline `<script>` bodies or `on*=` attributes and the CSP `script-src 'self'` is not weakened (SEC-10).

**F9 -- escaping**
12. A destination `https://example.com/?q=<script>alert(1)</script>` is created through the form. A click whose `referrer_host` is `<script>alert(1)</script>` is inserted directly in the database, bypassing parsing, so that the raw string reaches the template. On the created and analytics pages, the visible text contains the literal `<script>alert(1)</script>`, the HTML source contains it only as `&lt;script&gt;`, and the DOM has no `script` element except the page's own `src` scripts. The test does not rely on dialogs, because the CSP would block an inline script even if escaping were broken (TEST-6, SEC-6).
13. `src/views/` uses `<%~` only for partial includes, enforced by `test/unit/views-lint.test.ts`; destination links are rendered only via `safeHref`, which renders non-http(s) values as text (SEC-7).

**F27 -- quality bars**
14. Playwright tests for both journeys pass in Chromium, Firefox and WebKit, and axe scans of `/`, the created page, the analytics page and the not-found page report zero violations for `wcag2a`, `wcag2aa`, `wcag21a`, `wcag21aa` (TEST-7).
15. At a 360 px viewport, `document.documentElement.scrollWidth <= 360` on every page (TEST-8, UI-3).
16. `test/e2e/page-load.spec.ts`, in Chromium with the throttling profile above, measures `loadEventEnd` below 2,000 ms for `/`.
17. `test/e2e/keyboard.spec.ts` completes the Shorten journey with the keyboard only (Tab to each field, type, Enter to submit) and asserts that each focused element has a non-`none` computed `outline` or `box-shadow`. The axe scans in AC 14 cover colour contrast. Error states include text, so no information is conveyed by colour alone (UI-1).

**F29 -- noindex**
18. The analytics page response has `X-Robots-Tag: noindex` and a `<meta name="robots" content="noindex">`; redirect 302 and 404 responses have `X-Robots-Tag: noindex`.

**Shared**
19. `shorten` and `analytics` are in `RESERVED_ALIASES` and the ARCH-8 route test passes.
20. Every listed file exists; integration and e2e tests are named with their feature ID (`"F25: ..."`, etc.) (TEST-2); the UTC-append, throttling profile, CSRF and non-linked-referrer assumptions carry comments citing this RFC (COMP-2).
