# Example: LinkSnip, a URL shortener — before and after

This folder shows the workflow on one small product, twice.

- **[before/](before/)** — what the v2.0 prompts produced: a PRD, features, rules and three RFCs. It looks complete. It is not.
- **[after/](after/)** — the same product run through a pre-release state of the 3.1.0 commands (see below), starting from the same `before/PRD.md`.
- **[cold-reads/](cold-reads/)** — what a second model found when it read each generated RFC cold.
- **[workflow-status-reruns/](workflow-status-reruns/)** — six more `/workflow-status` runs on `before/`, graded blind.

This example stops before code. [todo-cli](../todo-cli/) is a smaller one that goes all the way to reviewed code.

Nothing in `before/` or `after/` is hand-edited. Each command ran in a fresh context with only its own instructions and the project files — no notes, no memory, and no list of known problems — and wrote what you see. The runs were non-interactive, so wherever a command would normally ask you a question, it recorded an assumption instead; the documents mark them **(assumption)**.

## How after/ was made

On 2026-11-15, with the skills built from this repository at 3.1.0, each command ran as its own agent on Claude Opus 5.5 (`claude-opus-5-5`), one after another, each committing its output:

| Step | What it wrote |
|---|---|
| `/verify-prd` | [PRD-REVIEW.md](after/PRD-REVIEW.md) — 5 High, 9 Medium and 10 Low findings — and the improved [PRD.md](after/PRD.md): 28 requirement IDs, 6 decisions, 15 open questions marked (assumption) |
| `/extract-features` | [FEATURES.md](after/FEATURES.md) — 44 features, each traced to a requirement |
| `/generate-rules` | [RULES.md](after/RULES.md) — 95 rules with IDs; every dependency version checked against its registry that day |
| `/generate-rfcs` | 12 RFCs in [RFCs/](after/RFCs/) and the index [RFCS.md](after/RFCS.md) |
| cold reads | The RFC agent could not start clean-context readers itself, so we ran them as its instructions describe: Fable 5.2 (`claude-fable-5-2`), given only PRD.md, FEATURES.md, RULES.md and one RFC at a time, answering "what would you have to guess to implement this?" They listed over 150 guesses, contradictions and untestable criteria (158 by the fixing agent's count). The same RFC agent then fixed them in the RFCs, deciding the ones the documents could not settle as marked assumptions flagged in RFCS.md for correction |
| `/test-strategy` | [TEST-STRATEGY.md](after/TEST-STRATEGY.md) — 203 planned tests, one row per acceptance criterion, 188 of them automated |

`trace-check.py` on `after/` reports 0 failures; its 3 warnings are two deferrals that RFCS.md records and one feature split across two RFCs. The [cold-read reports](cold-reads/) are condensed from the readers' output, keeping every finding. No code was written: the run stops where `/implement-rfc` would start. The whole run took about an hour of agent time.

The run committed after each step, and some files mention those commits (`git diff`, commit hashes); that history is not part of this repository. The commits, in order: start from `before/PRD.md`, `/verify-prd`, `/extract-features`, `/generate-rules`, `/generate-rfcs`, two cold-read fix commits, `/test-strategy`.

`after/` was made with the prompts as they stood after the first review round. A second round, run on `after/` itself, then changed the prompts again: assumptions and conflicts now go into `## Open Questions` and `## Open conflicts` lists that `/implement-rfc` must show you, cold-read fixes are limited to what changes behavior or an interface, and RFCs avoid criteria that restate the rules. A run today would produce a leaner `after/`; we have not rerun it, so this one is labelled for what it is.

Is `after/` good? Judge for yourself. It is far more thorough than `before/`, and some will find it too thorough for a URL shortener: 44 features and 95 rules is what you get when a PRD asks for 10M URLs, 99.9% uptime and zero click loss, and nobody is there to answer "how much of this do you need for v1?" In an interactive run, that is the first thing the interview and `/verify-prd` would ask you.

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

## /verify-prd on the same PRD: 10 of 10

The `/verify-prd` step of the after/ run started from `before/PRD.md`. Its [PRD-REVIEW.md](after/PRD-REVIEW.md) names all ten PRD problems above; the [eval suite's](../../evals/) graders for those ten match it, and match none of them in the fixture itself.

## /workflow-status on before/: 12 of 13 once, then 8 of 13, then 11 of 13

[workflow-status-on-before.md](workflow-status-on-before.md) is the report a fresh `/workflow-status` wrote with the v3.0.0 prompt on 2026-10-01. It found every cross-document problem above except the stale versions (9), and recommended `/verify-prd` as the next step.

That was one run. When a critic pointed out that the README's headline number came from it, we ran the command three more times with the 3.1.0 prompt, on Claude Opus 5.5, and had a fresh agent grade all the reports blind against the list above. The three runs found **8, 9 and 8**. The misses were consistent: an RFC that uses a table another RFC builds without declaring it as a predecessor (3 and 13), and an RFC that contradicts itself (6). The prompt never asked for either check. One run had found them anyway.

3.2.0 adds those checks, and versions stated from memory, to the prompt. Three new runs found **11, 11 and 11**. Problem 8, RFC-003 answering the retention question without a decision, is now the one most often missed. The reports and the blind grading are in [workflow-status-reruns/](workflow-status-reruns/).

It also found problems we had missed:

- RFC-002 claims F5, F6 and F11, but its acceptance criteria only test the API — every ID is cited, so the traceability script cannot see the gap
- RFC-003's expiry cleanup never clears the Redis cache, so expired links keep resolving
- RFC-001 and RFC-003 both claim the `alias` and `expiresAt` fields
- Date-range filtering exists only on the timeline endpoint
- Four performance targets in the PRD never reach any acceptance criterion
- RFC-002's sample response omits the `{ data, error, meta }` envelope RULES.md requires

These are single runs of one model. The [eval suite](../../evals/) runs the same checks repeatedly, with and without the workflow, so the difference can be measured rather than claimed.
