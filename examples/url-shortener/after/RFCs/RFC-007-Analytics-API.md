# RFC-007: Analytics API

**Features**: F16, F17, F18, F19, F20
**Depends on**: RFC-003, RFC-006
**Rules**: ARCH-2, ARCH-3, ARCH-4, ARCH-9, DATA-2, DATA-4, DATA-5, DATA-7, DATA-8, API-1, API-2, API-3, API-4, API-8, API-9, NAME-4, ERR-1, TEST-1, TEST-2, COMP-2
**Complexity**: Medium

## Summary

One public, read-only endpoint returns every analytics view for one short URL over one date range: total clicks (F16), a timeline by day, week or month (F17), top referrers (F18) and countries (F19), all filtered by the same inclusive UTC date range (F20). Bot clicks are excluded (F15, OQ-9). Days already rolled up are read from `click_daily`, later days from raw `clicks`, using RFC-006's watermark, so results are identical before and after raw retention runs. The service functions here are what the analytics page (RFC-009) and the list endpoint's total-click column (RFC-008) call (ARCH-4).

## Technical Approach

### API contract

`GET /api/v1/urls/{code}/analytics?from=YYYY-MM-DD&to=YYYY-MM-DD&interval=day|week|month`

No token: analytics for a single code are public (OQ-1). One endpoint rather than one per view so every view is guaranteed the same range and the UI needs one call (assumption; FR-14 is satisfied because every view is reachable through the API).

Parameters:
- `code`: path, `^[0-9A-Za-z]{3,30}$`, else 400 `VALIDATION_FAILED`.
- Where validation happens (cold read): the TypeBox querystring schema declares `from`, `to` and `interval` as optional plain strings, with no pattern or enum. It satisfies API-2 but rejects nothing. The service validates all three, so every bad value returns this endpoint's specific code rather than `VALIDATION_FAILED`.
- `from`, `to`: optional `YYYY-MM-DD` UTC dates, inclusive (F20).
  - Defaults: `to` = today (UTC, from the `Clock`); `from` = the UTC date of the link's `created_at`, or `to` if that is earlier, so `?to=<a date before creation>` gives zeros instead of an error.
  - Each of these returns 400 `INVALID_RANGE`: an explicit `from > to`; a malformed or impossible date (`2026-02-30`); `from` before `2000-01-01`; `to` more than 366 days after today. The two bounds keep bucket counts finite (assumption).
- `interval`: optional, `day`, `week` or `month`. Any other value (`year`) returns 400 `INVALID_RANGE` with a message naming the allowed values.
  - The range length is the inclusive day count `to - from + 1`.
  - Default: `day` when the length is ≤ 92, `week` when it is ≤ 731, otherwise `month` (assumption).
  - Whether the interval was given or defaulted, more than 400 buckets returns 400 `RANGE_TOO_LARGE` (assumption: keeps responses and charts bounded).

`200 OK`:

```json
{
  "code": "Promo2026",
  "from": "2026-11-01",
  "to": "2026-11-15",
  "interval": "week",
  "timeZone": "UTC",
  "excludesBots": true,
  "totalClicks": 1234,
  "timeline": [ { "start": "2026-10-26", "clicks": 10 }, { "start": "2026-11-02", "clicks": 0 }, { "start": "2026-11-09", "clicks": 1224 } ],
  "referrers": [ { "host": "t.co", "clicks": 600 }, { "host": null, "clicks": 300 }, ... ],
  "countries": [ { "country": "DE", "clicks": 700 }, { "country": null, "clicks": 34 }, ... ]
}
```

- `timeline`: one entry per bucket overlapping `[from, to]`, in order, including zero buckets (F17). `start` is the bucket's first day: the day itself; the ISO-week Monday (F17 assumption); or the first of the month. The first and last buckets may be partial: they count only days inside `[from, to]` (so the sum of `timeline` equals `totalClicks`).
- `referrers`: top 10 by clicks, ties broken by host ascending with `null` sorting after every host (assumption). `host: null` stands for a stored `referrer_host` of `''`, meaning no referrer or an unparseable one, which the UI labels "Direct / none" (F18). Grouped by host (`referrer_host`), not full URL.
- `countries`: every country with ≥ 1 click, descending, ties by code, with `null` after every code. `country: null` is SQL `NULL` and means Unknown (F19). `sum(countries.clicks) == totalClicks`.
- All numbers are integers.

Every response, including errors, carries `Cache-Control: no-store`.

Errors: 404 `NOT_FOUND` for unknown, deleted or expired codes (F16 assumption, consistent with F11) -- same body for all three; 400 `INVALID_RANGE`, `RANGE_TOO_LARGE`, `VALIDATION_FAILED`. New codes go into `src/errors.ts`.

### Query strategy

```
getAnalytics(deps, code, query):
  link = db.findLiveLinkByCode(code); if !link or expired(link, clock): throw NOT_FOUND
  {from, to, interval} = resolveRange(query, link.created_at, clock)
  BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY   # the watermark is read inside the same snapshot
  w = db.getRolledUpThrough()                      # date or null (RFC-006)
  # when w is null, or w < from, the aggregate side of each UNION is omitted entirely and raw covers all days;
  # when w >= to, the raw side is omitted
  aggDays = [from, min(to, w)]                     # empty if w is null or w < from
  rawDays = [max(from, w + 1 day), to]             # empty if w >= to
  # each of the four aggregates is one SQL statement of the form:
  #   SELECT <dim>, sum(clicks) FROM (
  #       SELECT <dim>, clicks FROM click_daily
  #         WHERE short_url_id=$1 AND day BETWEEN $aggFrom AND $aggTo AND NOT is_bot
  #     UNION ALL
  #       SELECT <dim>, count(*) FROM clicks
  #         WHERE short_url_id=$1 AND clicked_at >= $rawStart AND clicked_at < $rawEndExclusive AND NOT is_bot
  #         GROUP BY <dim>
  #   ) t GROUP BY <dim>
  # where <dim> is: nothing (total) | bucket(day) | referrer_host | country
  total     = sum query
  timeline  = bucket query, then fill missing buckets with 0 in the service
  referrers = referrer_host query ORDER BY sum DESC, host LIMIT 10
  countries = country query ORDER BY sum DESC, country NULLS LAST
  COMMIT
  return response    # SQL bigint and sum() arrive from pg as strings: converted with Number() after asserting
                     # <= Number.MAX_SAFE_INTEGER (always true at these volumes)
```

- Raw-side timestamps: `rawStart = rawDays.from 00:00:00Z`, `rawEndExclusive = (rawDays.to + 1 day) 00:00:00Z`; the filter on `clicked_at` keeps partition pruning (DATA-5).
- Buckets are computed with `date_trunc('week'|'month', ...)` on the UTC date (`(clicked_at AT TIME ZONE 'UTC')::date` on the raw side, `day` on the aggregate side). PostgreSQL's `date_trunc('week', ...)` starts weeks on Monday, matching ISO 8601.
- The watermark read and the four statements run on one pooled connection inside a single `REPEATABLE READ READ ONLY` transaction, so the views agree even while clicks arrive and the watermark moves (F20, "totals agree").
- All values are bound parameters (DATA-8). No write occurs (API-9).

### Shared function for RFC-008

`src/services/analytics-service.ts` also exports `totalClicksFor(deps, shortUrlIds: bigint[]): Promise<Map<bigint, number>>`. It returns all-time non-bot clicks per id, using two queries in the same kind of snapshot transaction:
- the aggregate side, through the watermark
- the raw side, `clicked_at >= (w + 1 day or, when w is null, the earliest created_at among the ids) AND clicked_at < clock.now() + 1 day`

Both bounds are explicit so partition pruning applies (DATA-5). Counts are converted as above. Deleted links are allowed (the caller decides what to list), and so are expired ones.

## File Structure

```
src/routes/api/analytics.ts
src/services/analytics-service.ts      (getAnalytics, resolveRange, totalClicksFor)
src/db/analytics.ts                    (the four aggregate queries + totals by id)
src/errors.ts                          (INVALID_RANGE, RANGE_TOO_LARGE)
test/unit/resolve-range.test.ts
test/integration/analytics.test.ts
```

## Implementation Considerations

- **Edge cases**:
  - A link created today with no clicks gives `totalClicks: 0`, one zero bucket, and empty `referrers` and `countries`.
  - An explicit range entirely before the link existed gives all zeros, not an error.
  - `to` up to 366 days in the future is allowed, and future buckets are 0 (assumption).
  - The snapshot transaction prevents the watermark from advancing between statements.
- **Bots**: always excluded, with no toggle in v1.0. F15 says "by default", but no feature asks for a way to include them. `excludesBots: true` in the response makes the behavior visible and leaves room to add a parameter under API-8. RFCS.md flags F15's wording (assumption).
- **Performance**: NFR-8 (< 200 ms p95). Aggregate side reads `click_daily` by `(short_url_id, day)`; raw side reads at most the days since the watermark (normally today only, ≤ ~1 day of rows for one link). RFC-011 load-tests it.
- **Caching**: none in v1.0; responses carry `Cache-Control: no-store` (assumption: analytics change on every click).
- **Testing**: real PostgreSQL; fixtures with clicks split across a rolled-up day and today; a test that runs rollup between two calls and asserts identical responses; a test that drops a raw partition (after rollup) and asserts identical responses.
- **Third-party**: none.

## Acceptance Criteria

**F16 -- total**
1. `GET /api/v1/urls/{code}/analytics` for a link with no clicks returns 200 with `totalClicks: 0` and requires no token (OQ-1).
2. Unknown, deleted and expired codes each return 404 `NOT_FOUND` with identical bodies (F16, DATA-4).
3. Clicks with `is_bot = true` are excluded from `totalClicks`, `timeline`, `referrers` and `countries`; the response has `excludesBots: true` (F15).

**F17 -- timeline**
4. `interval=day` over 2026-11-01..2026-11-07 returns exactly 7 entries `2026-11-01`..`2026-11-07`, zero-click days included as `clicks: 0`.
5. `interval=week` buckets start on Mondays; a range 2026-11-05 (Thursday)..2026-11-12 returns buckets `2026-11-02` and `2026-11-09`, each counting only days inside the range.
6. `interval=month` buckets start on the 1st; a click at 2026-11-30T23:59:59Z counts in November and one at 2026-12-01T00:00:00Z in December (UTC, OQ-12).
7. Range length is inclusive. With no `interval`, 92 days gives `day`, 93 gives `week`, 731 gives `week`, and 732 gives `month`. `interval=day` over 400 days returns 200, and over 401 days returns 400 `RANGE_TOO_LARGE`. `interval=year` returns 400 `INVALID_RANGE`. `from=1999-12-31` and a `to` 367 days after today each return 400 `INVALID_RANGE`. The response has `timeZone: "UTC"`.
7a. For a link created 2026-11-10, `?to=2026-11-05` with no `from` returns 200 with `from: "2026-11-05"` and all zeros.

**F18 -- referrers**
8. Referrers are grouped by host and ordered by clicks descending, then host ascending, with `null` last among equal counts. There are at most 10 entries. Clicks with no referrer appear as `host: null`.

**F19 -- countries**
9. Countries are listed with ISO codes, `null` for Unknown, and `sum(countries[].clicks) == totalClicks` for the same request.

**F20 -- date range**
10. `from` and `to` are inclusive UTC dates and apply to all four views. For every tested range, `sum(timeline[].clicks) == totalClicks`, `sum(countries[].clicks) == totalClicks`, and `sum(referrers[].clicks) <= totalClicks`. The last is `==` when the link has 10 or fewer referrer hosts.
11. `from > to`, a malformed date, or an impossible date returns 400 `INVALID_RANGE`.
12. Defaults: `from` = the link's creation date (UTC), `to` = today per the injected `Clock` (ARCH-9).
13. For a range spanning rolled-up days and today, the result equals a ground-truth count from raw clicks; after rollup runs and after the oldest raw partition is dropped, the same request returns the same body (F14, F20, DATA-7).
14. An instrumented pool shows that each request issues `BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY`, then the watermark read and the four aggregate statements on the same client, then `COMMIT`. No statement writes (API-9).

**Shared**
15. For live links, `totalClicksFor` equals the endpoint's full-life `totalClicks`. For an expired and a deleted link, it equals a ground-truth `count(*)` of their non-bot clicks taken directly in the database. Its raw-side query has both a lower and an upper `clicked_at` bound.
16. The route declares TypeBox schemas for params, querystring and the 200, 400, 404, 429 (RFC-010) and 500 responses (API-2). Field names are camelCase (NAME-4). Responses, errors included, carry `Cache-Control: no-store`.
17. Every listed file exists; tests are named `"F16: ..."`..`"F20: ..."` (TEST-2); the interval defaults, 400-bucket cap, top-10 tie-break and bot exclusion carry comments citing this RFC or FEATURES.md (COMP-2).
