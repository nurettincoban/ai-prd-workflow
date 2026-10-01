# Example: LinkSnip, a URL shortener — before and after

This folder shows the workflow on one small product, twice.

- **[before/](before/)** — what the v2.0 prompts produced: a PRD, features, rules and three RFCs. It looks complete. It is not.
- **after/** — the same product run through the 3.0.0 workflow, starting from the same PRD.

Nothing in either folder is hand-edited. Each command ran in a fresh context with only its own instructions and the project files — no notes, no memory, and no list of known problems — and wrote what you see. The model was Claude Opus 5.5 (`claude-opus-5-5`), on 2026-10-01. The runs were non-interactive, so wherever a command would normally ask you a question, it recorded an assumption instead; the documents mark them.

## The problems in before/, found by hand

Before running anything, we read `before/` closely and listed every problem we could find. The commands never saw these lists.

**In PRD.md alone** — what `/verify-prd` could catch:

1. 10,000+ active URLs in the goals, but 10M+ in the storage requirement
2. HTTP 301 redirects are cached by browsers: repeat clicks never reach the server, and deleted or expired links keep redirecting
3. No authentication, yet delete and list-all are open — anyone can delete any link or enumerate all of them
4. Three latency targets that disagree: sub-100 ms, p95 under 100 ms, average under 50 ms
5. "Zero data loss on click tracking" at 1,000 redirects per second, with nothing to make it true
6. A malware-blocklist requirement with no provider, and no behavior for links that turn malicious later
7. Referrer, user agent and IP-derived country stored with no privacy rules or retention period
8. 99.9% uptime from a single `docker-compose` host
9. Custom aliases that can shadow the app's own routes (`/api`, `/docs`)
10. A 100 requests/minute per-IP limit with no scope — applied to redirects, it throttles popular links

**Across the documents** — what `/workflow-status` could catch:

1. F7, a Must Have (the REST API, including rate limiting), is assigned to no RFC
2. No RFC builds the UI that the PRD, RULES.md (React and Vite) and F5, F6 and F11 describe
3. RFC-003 deletes click data from RFC-002's table, but declares only RFC-001 as a predecessor
4. RFCS.md, PRD-REVIEW.md and TEST-STRATEGY.md do not exist
5. RFC-003's alias regex allows hyphens; the PRD, F9 and the RFC's own acceptance criterion say alphanumeric
6. RFC-001 generates codes from a counter, then handles collisions with a random suffix
7. The PRD's malware-blocklist requirement becomes a Could Have, then "Optional"
8. The PRD's open question on analytics retention is answered silently by RFC-003
9. RULES.md states Node 20 (end of life since April 2026) and React 18, from memory
10. F14 and F15 are in no RFC, and nothing records that they are deferred
11. "Zero data loss" in the PRD vs fire-and-forget click writes in RFC-002
12. HTTP 301 vs per-click analytics
13. F4 deletes a link's analytics in RFC-001, but the analytics table only arrives in RFC-002

## /workflow-status on before/: 12 of 13

[workflow-status-on-before.md](workflow-status-on-before.md) is the report a fresh `/workflow-status` wrote. It found every cross-document problem above except the stale versions (9), and recommended `/verify-prd` as the next step.

It also found problems we had missed:

- RFC-002 claims F5, F6 and F11, but its acceptance criteria only test the API — every ID is cited, so the traceability script cannot see the gap
- RFC-003's expiry cleanup never clears the Redis cache, so expired links keep resolving
- RFC-001 and RFC-003 both claim the `alias` and `expiresAt` fields
- Date-range filtering exists only on the timeline endpoint
- Four performance targets in the PRD never reach any acceptance criterion
- RFC-002's sample response omits the `{ data, error, meta }` envelope RULES.md requires

These are single runs of one model. The [eval suite](../../evals/) runs the same checks repeatedly, with and without the workflow, so the difference can be measured rather than claimed.
