# Grading the /workflow-status reruns

Seven `/workflow-status` reports on the same `before/` folder, graded against the 13 cross-document problems listed by hand in [../README.md](../README.md). The grader was a fresh agent on Claude Sonnet 5.5 that saw only the problem list and the seven reports, under neutral names (R1 to R7). It used one strict standard for all of them and quoted the sentence behind every FOUND. Below, the neutral names are replaced with what each report is:

- `v3.0.0` is [workflow-status-on-before.md](../workflow-status-on-before.md), the single run from 2026-10-01.
- `3.1.0-run1` to `3.1.0-run3` are three runs of the 3.1.0 prompt, on Claude Opus 5.5, on 2026-11-15.
- `3.2.0-run1` to `3.2.0-run3` are three runs on Claude Opus 5.5 after the 3.2.0 changes. The prompt now tells the command to check each RFC's undeclared predecessors, RFCs that contradict themselves, and versions stated from memory.

## Result

| # | v3.0.0 | 3.2.0-run1 | 3.1.0-run1 | 3.2.0-run2 | 3.1.0-run2 | 3.2.0-run3 | 3.1.0-run3 |
|---|----|----|----|----|----|----|----|
| 1 | FOUND | FOUND | FOUND | FOUND | FOUND | FOUND | FOUND |
| 2 | FOUND | FOUND | MISSED | FOUND | FOUND | FOUND | FOUND |
| 3 | FOUND | FOUND | MISSED | FOUND | MISSED | FOUND | MISSED |
| 4 | FOUND | FOUND | FOUND | FOUND | FOUND | FOUND | FOUND |
| 5 | FOUND | FOUND | FOUND | FOUND | FOUND | FOUND | FOUND |
| 6 | FOUND | FOUND | FOUND | FOUND | MISSED | FOUND | MISSED |
| 7 | FOUND | FOUND | FOUND | FOUND | FOUND | FOUND | FOUND |
| 8 | FOUND | MISSED | FOUND | MISSED | FOUND | MISSED | MISSED |
| 9 | MISSED | FOUND | MISSED | FOUND | MISSED | FOUND | MISSED |
| 10 | FOUND | FOUND | FOUND | FOUND | FOUND | FOUND | FOUND |
| 11 | FOUND | MISSED | MISSED | FOUND | FOUND | FOUND | FOUND |
| 12 | FOUND | FOUND | FOUND | FOUND | FOUND | FOUND | FOUND |
| 13 | FOUND | FOUND | MISSED | MISSED | MISSED | MISSED | MISSED |
| **Total** | **12** | **11** | **8** | **11** | **9** | **11** | **8** |

## What this does and does not show

- **It is in-sample.** The 3.2.0 changes were written after reading what the 3.1.0 runs missed on this same `before/` folder, and then scored on it again. It shows the new checks work where they were aimed; it is not a score on a project the prompt was never tuned against.
- **Problem 8 got worse.** The 3.1.0 prompt found it in two of three runs, the 3.2.0 prompt in none. The new checks may crowd out the reading that found it. Problem 13 is still missed in two of three 3.2.0 runs.
- **Some of the 13 are mechanical.** `trace-check.py`, which every run executes first, reports the missing RFCS.md and the unassigned feature by itself.

Note: problem 7 is graded FOUND where the report says the blocklist check is "Optional" in RFC-003 against the PRD requirement; no report says "Could Have".

## Justifying quotes (FOUND)
Quotes are abridged.

### v3.0.0
1. "F7 (Must Have) is assigned to no RFC"
2. "No RFC builds any user interface."
3. "RFC-003 depends on RFC-002 but does not declare it."
4. "RFCS.md ... Missing; PRD-REVIEW.md Missing; TEST-STRATEGY.md Missing" (status table)
5. "RFC-003's alias regex allows hyphens ... all say alphanumeric."
6. "RFC-001's short-code generation mixes two methods: a counter ... and a 'retry with new random suffix'"
7. "it makes the blocklist check 'Optional' ... The PRD lists blocklist validation as a security requirement"
8. "Later documents answered two of them without updating the PRD: Retention ... RFC-003:22 ... delete a URL's click data"
10. "F14 and F15 are in no RFC, and nothing records that they are deferred"
11. "The PRD promises zero data loss ... RFC-002 writes each click without waiting to confirm ('fire-and-forget')"
12. "HTTP 301 conflicts with click tracking, deletion and expiry."
13. "Half of F4 is tested nowhere ... The clicks table and its ON DELETE CASCADE arrive in RFC-002"

### 3.2.0-run1
1. "F7 (Must Have) is in no RFC"
2. "RFC-002 builds only API endpoints, and no RFC builds or tests a frontend."
3. "RFC-003 uses tables from RFC-002 without declaring it ... add RFC-002 as a predecessor"
4. "no RFCS.md index, no PRD-REVIEW.md, no TEST-STRATEGY.md"
5. "RFC-003's alias rule contradicts its own acceptance criterion and the PRD."
6. "'a counter-based approach...' and also 'retry with new random suffix'"
7. "RFC-003 claims F13 (blocklist validation) but makes it optional."
9. "Node.js 20 reached end of life on 2026-04-30 ... React 18 is a major version behind React 19."
10. "F14 ... is in no RFC and is not formally deferred." / "F15 is partly built but unclaimed."
12. "HTTP 301 conflicts with click tracking, expiration and deletion."
13. "RFC-001 cannot do this, because the clicks table does not exist until RFC-002."

### 3.1.0-run1
1. "F7 has no RFC."
4. "RFCS.md is missing" ... "PRD-REVIEW.md Missing ... TEST-STRATEGY.md Missing"
5. "RFC-003 allows hyphens ... but its own first acceptance criterion says 'alphanumeric'."
6. "counter-based base62 code, which is unique by construction, and also a 'retry with new random suffix'"
7. "RFC-003 calls the blocklist check 'Optional'."
8. "RFC-003's hourly cleanup job hard-deletes expired URLs and their click data, which answers the question without anyone deciding it."
10. "F14 ... has no RFC and no recorded deferral." / "F15 (list URLs) is half covered."
12. "HTTP 301 vs. tracking every click."

### 3.2.0-run2
1. "F7 (Must have) is not assigned to any RFC."
2. "No RFC builds any UI."
3. "RFC-003 depends on RFC-002 but declares only RFC-001."
4. Status table: "RFCS.md ... missing", "PRD-REVIEW.md Missing", "TEST-STRATEGY.md Missing"
5. "The approach allows hyphens ... The acceptance criterion, F9 and the PRD all say 'alphanumeric'."
6. "'use a counter-based approach...' and then 'collision handling: retry with new random suffix'."
7. "The approach marks the blocklist check as 'Optional'."
9. "Node.js 20 reached end of life on 2026-04-30 ... React 18 has been superseded by React 19."
10. "F14 (OpenAPI docs) and F15 (List URLs) are not assigned to any RFC."
11. "'Zero data loss on click tracking' ... against fire-and-forget writes."
12. "A 301 redirect conflicts with click tracking, expiration and delete."

### 3.1.0-run2
1. "F7 (Must have) is an RFC gap" -> "F7 (Must have) is not assigned to any RFC."
2. "The analytics dashboard UI has no RFC."
4. "no RFC index, no test strategy" / "PRD-REVIEW.md Missing" / "RFCS.md ... missing"
5. "RFC-003's own first acceptance criterion says 'alphanumeric'."
7. "Blocklist check is 'optional' in RFC-003."
8. "analytics for an expired campaign are deleted within an hour of expiry. Nobody has agreed to that, and it is tied to open question 3 (analytics retention)."
10. "F14 (OpenAPI docs at /docs) has no RFC ... F15 (list URLs) is not credited to any RFC"
11. "'Zero data loss on click tracking' vs fire-and-forget."
12. "HTTP 301 undermines click tracking, deletion and expiry."

### 3.2.0-run3
1. "F7 (Must have) ... is assigned to no RFC"
2. "no RFC builds any frontend."
3. "RFC-003 needs RFC-002 but does not declare it."
4. Status table: PRD-REVIEW.md Missing, RFCS.md missing, TEST-STRATEGY.md Missing
5. "The approach allows hyphens ... Its own acceptance criterion, F9, and the PRD all say 'alphanumeric'."
6. "'a counter-based approach...' and also from 'Collision handling: retry with new random suffix'."
7. "Its approach calls the blocklist check 'Optional'."
9. "Node.js 20 is past end of life ... React 18 is a major version behind"
10. "no recorded deferral of F14 (OpenAPI docs) or F15 (list URLs)"
11. "'Zero data loss on click tracking' clashes with fire-and-forget writes."
12. "HTTP 301 clashes with click tracking and expiration."

### 3.1.0-run3
1. "F7 (Must Have) is not assigned to any RFC."
2. "no RFC builds the frontend."
4. "no RFCS.md ... PRD-REVIEW.md Missing ... TEST-STRATEGY.md Missing"
5. "allows hyphens too ... but its acceptance criterion still says 'alphanumeric'."
7. "its URL Validation section leaves the blocklist check 'Optional'."
10. "F14 ... and F15 ... are not assigned to any RFC, and no RFCS.md defers them."
11. "Fire-and-forget tracking conflicts with 'zero data loss'."
12. "Permanent redirects conflict with click tracking."
