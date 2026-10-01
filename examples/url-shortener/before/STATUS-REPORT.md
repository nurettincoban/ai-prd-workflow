# Workflow Status: LinkSnip URL Shortener

Checked 2026-10-01. The project is still in planning. PRD.md, FEATURES.md, RULES.md and three RFCs exist, and there is no source code.

**In short:** stages 1, 3 and 4 are done and stage 5 is half done. Stage 2 (Verify PRD) was skipped, so everything after it rests on an unverified PRD. No RFC is implemented or reviewed, and no review is owed yet. `trace-check.py` reports **2 failures and 4 warnings**. Reading the documents against each other found problems a mechanical check cannot see: requirements assigned to an RFC that the RFC does not deliver, and documents that contradict each other. There are 20 inconsistencies below, and the two FAILs are items 1 and 2.

`trace-check.py` output:

```
  0 requirements, 18 features, 0 rules, 3 RFCs
  FAIL  F7 (Must have) is not assigned to any RFC
  FAIL  RFCs exist but the RFCS.md index does not
  WARN  PRD.md: no requirement IDs (FR-n / NFR-n), so coverage from PRD to features cannot be checked
  WARN  RULES.md: rules have no IDs, so RFCs, reviews and change requests cannot cite them
  WARN  F14 (Could have) is not assigned to any RFC -- fine if RFCS.md defers it
  WARN  F15 (Could have) is not assigned to any RFC -- fine if RFCS.md defers it
  2 failure(s), 4 warning(s)
```

## 1. Status table

| # | Stage | Artifact | Status | Notes |
|---|-------|----------|--------|-------|
| 0 | Document an existing codebase | — | N/A | No code existed. The project took the new-project path (stages 1, 3, 4) |
| 1 | Create PRD | PRD.md | Done | 3 Open Questions still unanswered (PRD.md:101-104). No requirement IDs |
| 2 | Verify PRD | PRD.md (improved) + PRD-REVIEW.md | **Missing** | Never run, though stages 3–5 were built on the PRD |
| 3 | Extract features | FEATURES.md | Done | F1–F18 (8 Must, 4 Should, 3 Could, 3 Won't). The summary counts match the tables. Goes stale once stage 2 changes the PRD |
| 4 | Generate rules | RULES.md | Done | Rules have no IDs. Recheck after stage 2 |
| 5 | Generate RFCs | RFCs/ + RFCS.md | **In progress** | 3 RFC files exist. The RFCS.md index is missing, F7 (Must Have) is in no RFC, and no RFC covers the UI |
| 6 | Testing strategy | TEST-STRATEGY.md | Missing | Needed before the first `/implement-rfc` |
| 7 | Implement RFCs | Code | Missing | Not started, as expected at this point. There are no source files of any kind |
| 8 | Review implementations | reviews/ | Missing | Nothing is implemented, so no review is owed yet |
| 9 | Manage changes | changes/ | N/A | No change requests raised, none pending |
| 10 | Status check | STATUS-REPORT.md | Done | This report |

## 2. Per-RFC progress

```
RFC-001  implemented ❌   reviewed ❌
RFC-002  implemented ❌   reviewed ❌
RFC-003  implemented ❌   reviewed ❌
```

- **No Status column to start from.** RFCS.md does not exist, so I worked out each RFC's status from the files themselves:
  - The project contains no source code.
  - All 20 acceptance criteria in the three RFC files are unchecked.
  - There is no `reviews/` folder.

  No RFC is marked Implemented or Reviewed, so there was nothing to check against code.
- **Declared order:** RFC-001 depends on nothing, and RFC-002 and RFC-003 each list only RFC-001. RFC-003 also needs RFC-002 (item 13), so the order that works is RFC-001, then RFC-002, then RFC-003.
- **Code drift:** there is no code yet, so none of the code checks apply. No code can contradict the PRD or RULES.md, no RFC can have been implemented out of order, and no deviation can be missing from the Implementation Notes.

## 3. Inconsistencies

### Reported by trace-check

1. **FAIL: RFCS.md is missing although three RFCs exist** (`RFCs/`). Without it:
   - `/implement-rfc` and `/review-rfc` have no Status column to keep current.
   - Nothing records the order the RFCs should be built in.
   - Nothing records whether F14 and F15 are deferred.
2. **FAIL: F7 (Must Have) is assigned to no RFC** (FEATURES.md:33).
   - As a result, no RFC mentions rate limiting. It is in v1 scope (PRD.md:20, PRD.md:65), and RULES.md requires it twice (RULES.md:31, RULES.md:52).
   - RFC-001 defines the URL endpoints (RFC-001:31-35) but claims only F1, F2, F4 and F8 (RFC-001:7).
   - F7 also promises "CRUD", yet no RFC has an update endpoint.
3. **WARN: neither PRD.md nor RULES.md has IDs.**
   - Without FR-n/NFR-n IDs on PRD requirements, trace-check cannot confirm that every requirement became a feature. Checking by hand found items 5–10.
   - Without rule IDs, reviews and change requests cannot cite a rule.

### Skipped stage

4. **The PRD was never verified** (there is no PRD-REVIEW.md), yet FEATURES.md, RULES.md and the RFCs were all built on it. Its Open Questions (PRD.md:101-104) are still open. Later documents answered two of them without updating the PRD:
   - Retention (PRD.md:104): RFC-003:22 and FEATURES.md:22 delete a URL's click data when the URL itself is deleted or expires.
   - Blocklist provider (PRD.md:103): RFC-003:26 makes the check "Optional", so no provider is ever chosen.

### Requirements that look covered but are not

5. **No RFC builds any user interface.**
   - The PRD puts an analytics dashboard in v1 scope (PRD.md:17) and promises a "clean, minimal UI" (PRD.md:10). Both user journeys start in that UI (PRD.md:79, PRD.md:85-87).
   - RULES.md picks React 18 + Vite for the dashboard (RULES.md:8) and Playwright for e2e tests (RULES.md:9).
   - F5, F6 and F11 require an "analytics page" and a "chart" (FEATURES.md:27, 28, 42). RFC-002 claims all three (RFC-002:7), so trace-check does not flag them. But every acceptance criterion in RFC-002 tests only the API (RFC-002:52-58).
   - FEATURES.md has no feature for a web page to create short links.
6. **URL validation is incomplete and comes too late.**
   - RFC-003 claims F13, blocklist validation (RFC-003:7). But it makes the blocklist check "Optional" (RFC-003:26), and none of its acceptance criteria covers it (RFC-003:35-41). The PRD lists blocklist validation as a security requirement (PRD.md:72).
   - Basic URL format checks are in RFC-003 too (RFC-003:25-27). That leaves RFC-001's `POST /api/urls` (RFC-001:32) with two bad options. It can ship without validation, which breaks RULES.md:51, or it can do RFC-003's work early.
7. **Date-range filtering covers only the timeline.**
   - The PRD asks to "Filter analytics by date range" (PRD.md:60, PRD.md:87). FEATURES.md:28 limits that to F6.
   - RFC-002 gives `from`/`to` parameters only to the timeline endpoint (RFC-002:35, RFC-002:55).
   - The summary, referrer and country endpoints (RFC-002:34, 36, 37) cannot be filtered by date.
8. **Half of F4 is tested nowhere.** F4 says that deleting a URL also removes its analytics (FEATURES.md:22).
   - RFC-001's acceptance criterion covers only removing the URL and invalidating the cache (RFC-001:46).
   - The clicks table and its `ON DELETE CASCADE` arrive in RFC-002 (RFC-002:17), which has no criterion about deletion.
   - RFC-001 also adds an `is_active` column (RFC-001:21) that no document explains. If delete only sets that flag, the URL row is never removed, so its click data is never deleted.
9. **F14 and F15 are in no RFC, and nothing records that they are deferred** (trace-check WARNs).
   - RFC-001 already specifies F15's endpoint, `GET /api/urls` (RFC-001:35), but does not claim F15 or test it. F15 also needs click counts (FEATURES.md:51), which do not exist until RFC-002.
   - F14 (OpenAPI docs) is rated Could Have. The PRD lists it as a requirement (PRD.md:66) and schedules it for launch week (PRD.md:99).
10. **Several PRD non-functional requirements never reached a feature, rule or RFC.** No acceptance criterion carries these targets:
    - 1,000 redirects per second (PRD.md:71)
    - 99.9% uptime (PRD.md:70)
    - 10M+ stored URLs (PRD.md:73)
    - API responses under 200 ms "for all endpoints" (PRD.md:91). Only `POST /api/urls` has a timing criterion (RFC-001:43). The list, delete and analytics endpoints have none.

### Contradictions between documents

11. **HTTP 301 conflicts with click tracking, deletion and expiry.** PRD.md:51, FEATURES.md:20 and RFC-001:33/44 all require a 301. Browsers may cache a 301 indefinitely unless told otherwise.
    - When a visitor's browser has cached the 301, the next visit never reaches the server, so the click goes unrecorded. That contradicts "every redirect" (RFC-002:52), "accurate count" (FEATURES.md:27) and "zero data loss" (PRD.md:92).
    - Deleted or expired links keep redirecting for that visitor, which contradicts FEATURES.md:20, 22 and 41.
    - No document sets cache headers or considers a 302 or 307 instead.
12. **RFC-003's alias regex allows hyphens:** `^[a-zA-Z0-9-]{3,30}$` (RFC-003:15). The PRD (PRD.md:45), F9 (FEATURES.md:40) and RFC-003's own acceptance criterion (RFC-003:35) all say alphanumeric.
13. **RFC-003 depends on RFC-002 but does not declare it.**
    - RFC-003's cleanup job must remove "their click data" (RFC-003:22, RFC-003:39), and RFC-002 creates the clicks table (RFC-002:15-22).
    - Yet RFC-003 lists only RFC-001 as a dependency (RFC-003:8), and RFC-002 says "Required by: None" (RFC-002:9).
    - The declared order allows RFC-003 straight after RFC-001. At that point no click data exists, so the criterion cannot be verified.
14. **RFC-001 and RFC-003 both claim `alias` and `expiresAt`.** RFC-001:32 already defines the request body as `{ url, alias?, expiresAt? }`, while RFC-003:14 and RFC-003:20 say RFC-003 adds those fields to `POST /api/urls`. It is unclear which RFC implements them, so whoever implements RFC-001 could end up building RFC-003's features.
15. **Unconfirmed click writes vs "zero data loss".**
    - RFC-002 writes each click without waiting to confirm it was saved (RFC-002:31, "fire-and-forget").
    - RULES.md:47 allows async or batched writes.
    - The PRD promises zero data loss on click tracking (PRD.md:92). Nothing retries a failed write or queues it somewhere durable, so the design cannot guarantee that promise.
16. **The PRD's own numbers disagree.**
    - Capacity: the Goals say 10,000+ active URLs (PRD.md:9), but the storage requirement says 10M+ (PRD.md:73). That is a factor of 1,000.
    - Redirect latency: there are two targets, 95th percentile under 100 ms (PRD.md:69) and average under 50 ms (PRD.md:90). Only the 95th-percentile target reached F2 and RFC-001.

### Minor drift (fix when the RFCs are next edited)

17. **RFC-003's expiry handling ignores the Redis cache.**
    - RULES.md:46 and RFC-001:39 put Redis in front of redirects, and RFC-001:46 clears the cached entry when a URL is deleted.
    - RFC-003's hourly cleanup deletes expired URLs straight from Postgres (RFC-003:31) and never clears their cached entries.
    - RFC-003's expiry check (RFC-003:21) does not say whether `expires_at` is stored in the cached entry. Expired links could keep resolving from Redis.
18. **RFC-001's short-code generation mixes two methods:** a counter "for uniqueness" (RFC-001:28) and a "retry with new random suffix" (RFC-001:29). A plain base62 counter also does not produce the required 7 characters (RFC-001:27, FEATURES.md:19) unless it starts at a high value or is padded.
19. **RFC-002's sample response leaves out envelope fields.** The sample has only `data` (RFC-002:39-49), but RULES.md:29 requires every response to have `data`, `error` and `meta`.
20. **RFC-001's indexes do not match RULES.md:36.**
    - `short_code` is indexed twice. The UNIQUE constraint (RFC-001:17) already creates an index, and RFC-001:23 adds a second one.
    - `urls.created_at` has no index, though RULES.md:36 asks for one.

## 4. Next step

**Run `/verify-prd`** (prompt: `prd-comprehensive-verification-prompt.md`). Stage 2 was skipped, and nine of the problems above (items 3–7, 10, 11, 15, 16) start in PRD.md or need a decision there. Nothing is implemented yet, so this is the cheapest point to fix them.

Running `/generate-rfcs` first would clear the two FAILs, but it would rebuild the RFCs on the same unverified PRD. While verifying, make sure the PRD:
- answers the three Open Questions
- decides which redirect status code to use and how it is cached
- states the UI scope explicitly
- reconciles the capacity and latency figures
- gives every requirement an FR- or NFR- ID

After that:
1. Bring stages 3–5 back in line with the improved PRD. With no code yet, the simplest way is to regenerate them: `/extract-features`, then `/generate-rules`, then `/generate-rfcs`. The new RFC set should:
   - include RFCS.md
   - assign F7 to an RFC
   - add an RFC for the UI
   - record whether F14 and F15 are built or deferred
   - fix items 12–14 and 17–20
2. Re-run `trace-check.py` until it reports no FAIL.
3. Run `/test-strategy`, then `/implement-rfc RFC-001`.
