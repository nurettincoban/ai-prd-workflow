# RFC-006: Click Rollup and Retention

**Features**: F14
**Depends on**: RFC-001, RFC-003
**Rules**: DATA-1, DATA-2, DATA-5, DATA-6, DATA-7, DATA-8, ARCH-2, ARCH-9, PRIV-1, PRIV-3, LOG-2, ERR-2, NAME-3, NAME-5, OPS-4, TEST-1, TEST-2, COMP-2, COMP-3
**Complexity**: Medium

## Summary

Raw click events are personal data (user-agent, referrer) and are kept 13 months by default (OQ-4); per-day aggregates are kept indefinitely so totals and timelines survive the purge. This RFC adds the `click_daily` aggregate table and a watermark, a rollup job that aggregates every completed UTC day, and a retention job that drops whole monthly `clicks` partitions once they are past the retention window and fully rolled up (DATA-6, DATA-7). It also writes the README privacy note. RFC-007's analytics read from both tables using the watermark defined here. The client-IP half of F14 (never stored or logged) is already enforced by RFC-001 and RFC-003; this RFC re-verifies it end to end.

## Technical Approach

### Schema (new migration `migrations/<timestamp>_create-click-daily.ts`)

```sql
CREATE TABLE click_daily (
  short_url_id   bigint  NOT NULL REFERENCES short_urls(id),
  day            date    NOT NULL,          -- UTC calendar day (NAME-3)
  referrer_host  text    NOT NULL,          -- '' = direct / none
  country        char(2) NULL,              -- NULL = Unknown
  is_bot         boolean NOT NULL,
  clicks         bigint  NOT NULL,
  CONSTRAINT click_daily_key UNIQUE NULLS NOT DISTINCT (short_url_id, day, referrer_host, country, is_bot)
);
CREATE INDEX click_daily_url_day_idx ON click_daily (short_url_id, day);

CREATE TABLE click_rollup_state (
  id              boolean PRIMARY KEY DEFAULT true CHECK (id),   -- single row
  rolled_up_through date NULL                                   -- last UTC day fully aggregated; NULL = none
);
INSERT INTO click_rollup_state DEFAULT VALUES;
```

The dimensions (referrer host, country, bot flag) are exactly what RFC-007 needs to answer every view -- total, timeline, top referrers, countries -- from aggregates alone, so a date range older than the raw window gives the same answers as one inside it (F20). Full referrer and user-agent strings are deliberately **not** aggregated: they are the personal data that the 13-month window exists to limit. Bot clicks are aggregated with their flag rather than dropped, so a later "include bots" option stays possible.

### Rollup job (`src/services/click-rollup.ts`, `src/db/click-daily.ts`)

```
rollup(clock, hooks = {}):                    # scheduler job "click-rollup": every 15 min, runAtStart: true
  GRACE = 15 minutes                          # (assumption; see the finality note below)
  last  = SELECT rolled_up_through FROM click_rollup_state
  start = last ? last + 1 day : utcDate(min(clicked_at) from clicks) ?? (stop: nothing to do)
  for day in start .. while (day + 1 day 00:00Z) + GRACE <= clock.now():     # completed days, with grace
     if the clicks partition containing day does not exist:                   # cold read: guard against re-aggregating a
        log.warn({event:"rollup_skipped_no_raw", day}); stop                 # dropped day, which would wipe its aggregates
     BEGIN
       DELETE FROM click_daily WHERE day = $day           # makes a re-run of a day safe
       INSERT INTO click_daily (short_url_id, day, referrer_host, country, is_bot, clicks)
         SELECT short_url_id, $day, referrer_host, country, is_bot, count(*)
         FROM clicks WHERE clicked_at >= $dayStart AND clicked_at < $dayEnd
         GROUP BY short_url_id, referrer_host, country, is_bot
       UPDATE click_rollup_state SET rolled_up_through = $day
     COMMIT
     log.info({event:"click_rollup_completed", day, rows})
     hooks.afterDayCommitted?.(day)          # test seam for crash injection (AC 4)
```

The `clicks` columns read here come from RFC-001. `referrer_host` is `NOT NULL DEFAULT ''`, `country` is nullable, and `is_bot` is `NOT NULL`, so the insert into `click_daily` cannot violate a constraint.

- **Finality** (cold read): a click's `clicked_at` is taken before its insert commits, so a click stamped 23:59:59.9 can commit a moment after midnight. The insert is bounded at 2 s (RFC-003), and rollup waits a 15-minute grace period after a day ends. A day is therefore final when it is rolled up, provided app clocks are within 15 minutes of each other. `clicked_at` comes from the app clock, not the database clock, so app hosts must keep accurate time (assumption: they run NTP); skew between instances is ignored.
- The `DELETE` of the day is scoped to one day, inside the transaction; it is not a raw-click delete and does not conflict with DATA-6.
- The first run on an instance with a long history rolls up day by day; each day is its own transaction so progress survives a crash.

### Retention job (`src/services/click-retention.ts`, `src/db/partitions.ts`)

```
retain(clock, retentionMonths):               # scheduler job "click-retention": every 24 h, runAtStart: true
  await withAdvisoryLock("click-rollup", () => rollup(clock))   # catch up first, so a restart after downtime
                                                               # does not block on days that simply have not been rolled up yet
  cutoffMonth = firstDayOfMonth(utcDate(clock.now())) - retentionMonths months
  partitions = SELECT c.relname FROM pg_inherits i JOIN pg_class c ON c.oid = i.inhrelid
               WHERE i.inhparent = 'clicks'::regclass         # attached partitions, read from the catalog
  for each name matching ^clicks_y(\d{4})m(\d{2})$ whose month's upper bound <= cutoffMonth:
     # the bound is derived from the name: only RFC-001's code creates partitions, and it names them
     # from their bounds. RFC-001 creates no default partition.
     if rolled_up_through is NULL or rolled_up_through < (upper bound - 1 day):
        log.warn({event:"retention_blocked_not_rolled_up", partition}); continue      # DATA-7
     BEGIN; SET LOCAL lock_timeout = '2s'
       ALTER TABLE clicks DETACH PARTITION <name>; DROP TABLE <name>                   # DATA-6, one transaction
     COMMIT   -- on lock_timeout: ROLLBACK, log {event:"retention_lock_timeout", partition}, retry on the next run
     log.info({event:"retention_partition_dropped", partition})
  # orphan sweep: a table named clicks_y…m… that is not attached (e.g. left behind by a manual detach) and
  # is past the cutoff is dropped the same way, so raw data never outlives retention
```

- With the default 13 months, on 2026-11-15 the cutoff is 2025-10-01; partitions up to and including `clicks_y2025m09` are dropped. A click is therefore kept at least 13 and at most 14 months (whole-partition granularity; assumption, documented in the privacy note).
- `DETACH PARTITION` without `CONCURRENTLY` needs a lock on `clicks`. `lock_timeout = '2s'` keeps it from queueing behind inserts and stalling redirects for long, which is why DATA-6 exists. On timeout the drop is retried the next day. Detach and drop share one transaction, so a crash cannot leave a detached table behind. (`DETACH ... CONCURRENTLY` cannot run in a transaction block, so it is not used.)
- Partition names come from the catalog and are checked against `^clicks_y\d{4}m\d{2}$` before being placed in DDL (DATA-8 intent).

### Aggregate retention

F14 says both periods are operator-configurable. `LINKSNIP_AGGREGATE_RETENTION_MONTHS` (default unset = keep forever). When it is set, the retention job also runs `DELETE FROM click_daily WHERE day < $cutoff`, where `$cutoff = utcDate(clock.now()) - N calendar months`, day-aligned (e.g. N = 24 on 2026-11-15 gives 2024-11-15). The value must be an integer from 1 to 1200 and at least `LINKSNIP_CLICK_RETENTION_MONTHS`. This is a row delete on the aggregate table, not on raw clicks, so DATA-6 does not apply; PRIV-3 says aggregates are never purged by the retention job. Read literally, this opt-in purge contradicts it. The plan follows FEATURES.md F14, which has higher authority and requires both periods to be configurable. The purge is off by default and logged as its own event, `aggregate_retention_purged`. RFCS.md **flags PRIV-3** for correction (assumption until then).

### Configuration (src/config.ts, `.env.example`, README; OPS-4)

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `LINKSNIP_CLICK_RETENTION_MONTHS` | no | `13` | Months of raw click events kept (integer 1-120) |
| `LINKSNIP_AGGREGATE_RETENTION_MONTHS` | no | unset (forever) | Months of daily aggregates kept; integer 1-1200, ≥ the raw value, when set |

### Privacy note (README `## Privacy and data retention`, COMP-3)

States: per click LinkSnip stores time (UTC), full referrer, user-agent, country code, and a bot flag; the client IP is used only to look up the country and is never stored or logged; raw clicks are kept for `LINKSNIP_CLICK_RETENTION_MONTHS` (13 by default; dropped a whole month at a time, so up to one month longer); daily counts by referrer host, country and bot flag are kept indefinitely unless `LINKSNIP_AGGREGATE_RETENTION_MONTHS` is set; operators are the data controller and should describe this in their own privacy notice.

## File Structure

```
migrations/<timestamp>_create-click-daily.ts
src/db/click-daily.ts            (rollup SQL, watermark read/write, aggregate purge)
src/db/partitions.ts             (list/detach/drop added)
src/services/click-rollup.ts  src/services/click-retention.ts
src/server.ts                    (jobs registered with the scheduler)
src/config.ts  .env.example  README.md
test/integration/click-rollup.test.ts  test/integration/click-retention.test.ts
test/integration/privacy.test.ts
```

## Implementation Considerations

- **Edge cases**: no clicks ever → watermark stays NULL until the first click, then starts from that click's day; rollup lagging (job stopped for weeks) → retention refuses to drop un-rolled partitions and logs `retention_blocked_not_rolled_up` every run until rollup catches up; changing `LINKSNIP_CLICK_RETENTION_MONTHS` downward takes effect at the next daily run.
- **Testing**: real PostgreSQL (TEST-1) with a fake clock (ARCH-9); create clicks across three months, roll up, drop, and assert totals from `click_daily` equal totals counted from raw beforehand.
- **Performance**: rollup scans one day's slice of one partition through the `(short_url_id, clicked_at, id)` PK; at ~86M clicks/day worst case (1,000/s sustained) it is a large scan, but NFR-3 is a peak rate, not a daily average (assumption). The job runs off the request path and takes no lock on `short_urls`.
- **Compliance**: GDPR storage limitation is the reason for the window (OQ-4).
- **Third-party**: none.

## Acceptance Criteria

1. The migration creates `click_daily` (with the `NULLS NOT DISTINCT` unique key and `(short_url_id, day)` index) and the single-row `click_rollup_state` (DATA-1, NAME-3).
2. Clicks exist on 2026-11-13 and 2026-11-14. With a fake clock at 2026-11-15T00:10Z, a rollup run rolls up only 2026-11-13, because 2026-11-14 is still inside its grace period. At 2026-11-15T00:16Z it also rolls up 2026-11-14. The rows are grouped by `short_url_id, referrer_host, country, is_bot`, `rolled_up_through` ends at `2026-11-14`, and 2026-11-15 is never touched (DATA-7).
3. Re-running rollup for an already rolled-up day (watermark reset in the test) produces identical `click_daily` contents (no double counting).
4. With an `afterDayCommitted` hook that throws after day N, the run stops with `rolled_up_through = N`, and the next run resumes at N+1 without double counting.
4a. When the raw partition for the day after the watermark has been dropped, rollup logs `rollup_skipped_no_raw` and writes nothing, so no aggregate is deleted.
5. With retention set to 13 months and a fake clock on 2026-11-15, the retention job drops every partition whose upper bound is ≤ 2025-10-01. Each drop is a `DETACH PARTITION` and `DROP TABLE` in one transaction with `lock_timeout` 2s, and logs `retention_partition_dropped`. An instrumented pool records every statement, and none matches `/DELETE\s+FROM\s+clicks/i` (DATA-6, PRIV-3).
5a. While another connection holds a conflicting lock on `clicks`, the drop gives up after about 2 s, logs `retention_lock_timeout`, and leaves the partition attached. A detached orphan `clicks_y2025m01` is dropped by the sweep.
6. When rollup cannot catch up (the test holds the `click-rollup` lock), a partition past the window that contains a day after `rolled_up_through` is not dropped, and `retention_blocked_not_rolled_up` is logged at warn (DATA-7). Without that obstruction, retention runs rollup first and then drops.
7. After raw partitions are dropped, the per-link total and per-day counts computed from `click_daily` equal those computed from raw clicks before the drop (F14 "totals and timelines stay correct").
8. With `LINKSNIP_AGGREGATE_RETENTION_MONTHS` unset, no statement deletes from `click_daily` during retention. With it set to 24 and a clock on 2026-11-15, rows with `day < 2024-11-15` are deleted and `aggregate_retention_purged` is logged. Startup exits naming the variable when the value is below `LINKSNIP_CLICK_RETENTION_MONTHS`, above 1200, or not an integer.
9. A unit test of the job list that `startServer` registers checks: `click-rollup` runs every 900,000 ms with `runAtStart: true`, and `click-retention` runs every 86,400,000 ms with `runAtStart: true`. Each job's advisory-lock key is its own name (RFC-001).
10. `test/integration/privacy.test.ts` sends redirects with `inject({ remoteAddress: "203.0.113.9" })` through the full app. The fake `GeoLookup` asserts it was called with `203.0.113.9`, which proves the IP reached the app. The test then runs rollup and asserts that `203.0.113.9` appears in no column of `short_urls`, `clicks` or `click_daily` and in no captured log line (PRIV-1, F14).
11. README `## Privacy and data retention` contains every statement listed in the Privacy note section (COMP-3).
12. The two variables are in `src/config.ts`, `.env.example` and the README table; the OPS-4 test passes.
13. Tests are named `"F14: ..."` (TEST-2); the 13-to-14-month granularity and the aggregate-purge reading of PRIV-3 carry comments citing this RFC (COMP-2).
