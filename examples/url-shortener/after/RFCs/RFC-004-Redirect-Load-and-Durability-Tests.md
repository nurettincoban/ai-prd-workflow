# RFC-004: Redirect Load and Durability Tests

**Features**: F32
**Depends on**: RFC-003
**Rules**: TEST-9, TEST-10, PERF-1, PERF-2, PERF-3, LOG-3, STACK-4, STACK-5, COMP-2, ARCH-2, STACK-2
**Complexity**: High

## Summary

This RFC builds the load-test harness in `load/` and runs it against the redirect path as soon as that path exists. The reason for doing it this early is that the whole design rests on an unproven assumption (OQ-7, PERF-2): that a synchronous, durable click insert on every redirect fits inside 100 ms p95, at 1,000 redirects per second, over 10M stored URLs (NFR-1, NFR-3, NFR-6). FEATURES.md asks for this ("F32 must run early against F10 and F12 to settle OQ-7").

Scope:
- **Covered here:** F32's redirect latency, throughput, no-failed-redirects and durability criteria.
- **Covered in RFC-011:** F32's management and analytics latency scenario, which needs endpoints that do not exist yet. RFC-011 also lists F32. The split is deliberate and recorded in RFCS.md.

## Technical Approach

### Reference host (cold read: hardware and storage were unspecified)

**App host** (assumption, refining OQ-8; the storage requirement matters because a synchronous commit's latency is set by fsync):
- 2 vCPU, 4 GB RAM, Linux, Docker Engine with Compose v2
- SSD-backed storage that honours fsync, for example a cloud general-purpose SSD volume with at least 3,000 baseline IOPS
- runs both the app and PostgreSQL through `compose.yaml`

**Load generator:**
- k6 runs on a **separate** machine in the same region or LAN.
- Only a run with that separate generator gives a verdict.
- A run with k6 on the app host is labelled "informational, co-located" in `RESULT.md`.

### Seeding (cold read: duplicates, COPY needing an unlisted dependency, connection details)

The seed is pure SQL, run through `psql` inside the `db` container. It needs no npm dependency (STACK-4), and the database port does not need to be published.

`load/seed.sh`:
```
usage: load/seed.sh [--count N] [--force]      (default N = 10,000,000)
existing = SELECT count(*) FROM short_urls
if existing > 1000 and not --force: exit 1 "refusing to seed a non-empty database"
if --force: TRUNCATE clicks, short_urls RESTART IDENTITY CASCADE     # --force means "wipe and reseed"
docker compose exec -T db psql -U linksnip -d linksnip -v count=N -f - < load/seed.sql
docker compose exec -T db psql -U linksnip -d linksnip -At \
   -c "SELECT code FROM short_urls ORDER BY random() LIMIT 10000" > load/data/active-codes.txt   # the active set (OQ-3)
```

`load/seed.sql`:
```
CREATE OR REPLACE FUNCTION pg_temp.seed_code() RETURNS text VOLATILE LANGUAGE sql AS $$
  SELECT string_agg(substr('0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
                           1 + floor(random() * 62)::int, 1), '')
  FROM generate_series(1, 7) $$;
-- loop in batches of 1,000,000 until count(*) = :count
INSERT INTO short_urls (code, destination, is_alias, management_token_hash, blocklist_status, created_at)
  SELECT c, 'https://example.com/' || c, false, gen_random_bytes(32), 'unchecked', now()
  FROM (SELECT pg_temp.seed_code() AS c FROM generate_series(1, <batch>)) s
  ON CONFLICT (code) DO NOTHING;        -- a few of the 10M random codes collide; they are skipped and the loop tops up
```

Notes:
- The loop is a `DO` block, or a `psql` `\gexec` loop, that recomputes the remaining count each round, so the final count is exact.
- `gen_random_bytes` requires the `pgcrypto` extension, and `seed.sql` creates it if it is missing. If adding the extension is unwanted, use `decode(md5(random()::text) || md5(random()::text), 'hex')` instead; that is 32 bytes, and the seed's hashes never need to be secure.
- `random()` is acceptable here: SEC-3 governs `src/`, and seeded tokens never need to be unpredictable.
- `load/` is outside `src/`, so ARCH-2 does not apply to it (assumption, flagged in RFCS.md). No request value reaches the SQL.

### Redirect scenario

`load/compose.load.yaml` is an override for `compose.yaml`. It makes three changes:
- `LINKSNIP_REDIRECT_RATE_LIMIT=1000000` on `app`, so RFC-010's limiter is inert. The variable is ignored until RFC-010 exists.
- A `k6` service from `grafana/k6:2.4.0`, used only for informational co-located runs.
- Any recorded PostgreSQL tuning, applied as `command: postgres -c ...` on `db`; see Allowed tuning.

`load/redirect.js` defines two scenarios:
- `warmup`: `ramping-arrival-rate` from 0 to 1,000 iterations/s over 60 s.
- `steady`: `constant-arrival-rate` at 1,000 iterations/s for 10 minutes, with `startTime: "60s"`, `preAllocatedVUs: 200` and `maxVUs: 1000`.

Each iteration GETs `/<random active code>` with `redirects: 0` and a desktop-Chrome `User-Agent`, and uses `responseCallback: http.expectedStatuses(302)`.

Gating thresholds, all on `{scenario:steady}`: `http_req_failed` `rate==0` and `dropped_iterations` `count==0`. The script also *reports* client-side `p(95)` and `avg` but does not gate on them. Warm-up samples are excluded from every figure.

### Server-side latency (cold read: capture method and fields unstated; which figure decides)

NFR-1 is measured server-side, so server-side figures decide the verdict:
1. `load/run-redirect.sh` records the UTC start and end of the steady phase.
2. It captures the app log for exactly that window with `docker compose logs app --since <start> --until <end> --no-log-prefix > load/results/<run>/app.log`.
3. It runs `npx tsx load/server-latency.ts load/results/<run>/app.log --route "/:code" --p95 100 --avg 50`.
4. `server-latency.ts` reads the `request_completed` lines defined in RFC-001 (fields `route`, `statusCode`, `responseTimeMs`) and prints the count, p95 and average.
5. It exits non-zero when p95 ≥ 100 ms or the average ≥ 50 ms.

A run where k6's client-side p95 is over 100 ms but the server-side figures pass is recorded as "NFR-1 pass (server-side); client-side over budget". That is a pass, not a stop.

### Durability test (TEST-10, NFR-9, R6)

`load/durability.sh` runs against the seeded database. It does not truncate anything.
```
code = first line of load/data/active-codes.txt; id = SELECT id FROM short_urls WHERE code = :code
for run in 1..3:
   before = SELECT count(*) FROM clicks WHERE short_url_id = :id
   start k6 load/durability.js in the background: 500 GETs/s to /<code> for 60 s, counting 302 responses
       in the counter "redirects_302" and writing a summary JSON
   sleep a random 15-45 s; docker compose kill -s SIGKILL app; docker compose up -d app
   wait for k6 to finish
   after = SELECT count(*) FROM clicks WHERE short_url_id = :id
   FAIL if redirects_302 > after - before      # an answered redirect without a stored click
   (after - before > redirects_302 is allowed: a click was committed but its response was lost in the kill)
```
The test is repeated three times, at random kill times, so a single lucky instant cannot pass it. k6 runs on the load machine, as above.

### Results

`load/results/<YYYY-MM-DD>-<git short sha>/` holds:
- the k6 JSON summaries and `app.log`
- the server-side summary
- the host description: CPU, RAM, storage type, and whether k6 was co-located
- `seed` table and index sizes
- the tuning applied
- `RESULT.md`, with pass or fail for each criterion

### If the thresholds fail (OQ-7)

**The write path does not change in this RFC.** If the server-side p95 is 100 ms or more, or the steady rate cannot be sustained with the synchronous insert, the implementer:
1. records the numbers in `RESULT.md` and in this RFC's Implementation Notes
2. stops

The fix needs a new RFC that also relaxes NFR-9 to a stated loss window (PERF-2, OQ-7), and that is the user's decision.

**Allowed tuning** (cold read: the earlier text left room to break NFR-9):
- `LINKSNIP_DB_POOL_SIZE`
- PostgreSQL `shared_buffers`, `effective_cache_size`, `work_mem`, `wal_buffers` and `max_connections`

Any tuning kept is copied into `compose.yaml` so that production matches.

**Forbidden in this RFC:**
- `synchronous_commit = off`, `fsync = off` and `full_page_writes = off`, because each breaks NFR-9
- dropping the `clicks` foreign key or any other schema change; if the foreign key is the bottleneck, record it and stop

## File Structure

```
load/compose.load.yaml  load/seed.sh  load/seed.sql
load/redirect.js  load/run-redirect.sh  load/server-latency.ts
load/durability.js  load/durability.sh
load/README.md          # reference host, how to run each scenario, where results go
load/data/.gitignore    # active-codes.txt is generated, not committed
load/results/<run>/RESULT.md (+ JSON summaries, app.log)
package.json            (scripts: load:seed, load:redirect, load:durability)
```

## Implementation Considerations

- **Seeding 10M rows** with set-based SQL takes minutes. The data comes to about 2-3 GB with indexes. Record the sizes.
- **Click volume:** a run writes about 660,000 click rows (warm-up plus steady), plus three durability runs of about 30,000 each.
- **Measurement honesty:** a verdict requires the reference host and a separate generator (AC 6). Any other run is labelled with what it was.
- **Third-party:** the `grafana/k6:2.4.0` image (RULES stack). No new npm dependency: `server-latency.ts` uses only Node built-ins and runs with `tsx`.
- **Security:** the seed's token hashes are random and no plain token exists, so seeded links cannot be deleted. That is intended.

## Acceptance Criteria

1. `load/seed.sh --count 10000000` leaves exactly 10,000,000 rows in `short_urls`, with colliding random codes skipped and topped up, and writes 10,000 distinct active codes to `load/data/active-codes.txt`. It refuses to run when the table has more than 1,000 rows unless `--force` is given, which truncates and reseeds. `active-codes.txt` is git-ignored. No npm dependency is added.
2. `load/redirect.js` warms up for 60 s and then holds 1,000 redirects/s for 10 minutes against the active codes. On the steady phase it fails unless there are zero failed requests (302 counts as success) and zero dropped iterations (F32, NFR-3). It reports the client-side p95 and average.
3. `load/server-latency.ts`, run on the steady-window `app.log`, exits non-zero unless the server-side redirect p95 is under 100 ms and the average is under 50 ms (NFR-1, TEST-9). `RESULT.md` records both server-side and client-side figures. Server-side decides the verdict.
4. `load/durability.sh` runs three times, each with one SIGKILL of the app at a random point between 15 and 45 s. It fails if, in any run, the number of 302 responses k6 received exceeds the increase in that code's `clicks` rows (TEST-10, NFR-9).
5. `load/README.md` documents the reference host (2 vCPU, 4 GB RAM, fsync-honouring SSD, separate k6 machine), how to seed, how to run each scenario, and where results go.
6. A run on any host can complete this RFC if `RESULT.md` labels it ("reference" / "not reference hardware" / "co-located"). The **verdict** run on the reference host with a separate generator is required before release, and RFC-011 AC 10 checks that it exists.
7. If any gating threshold fails on the reference host, the write path and schema are unchanged. The numbers are recorded in `RESULT.md` and in this RFC's Implementation Notes, and the implementer stops for a decision on OQ-7.
8. `load/compose.load.yaml` sets `LINKSNIP_REDIRECT_RATE_LIMIT=1000000`, and `RESULT.md` records it. No forbidden setting (`synchronous_commit`, `fsync`, `full_page_writes`) appears in either compose file, and a grep test checks this. Any tuning recorded in `RESULT.md` is also present in `compose.yaml`.
