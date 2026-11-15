# Workflow status (2026-11-15)

`trace-check.py`: 0 failures, 2 warnings (F11 split across RFC-002 and RFC-003; F15 split across RFC-001 and RFC-005). Both are intended splits, noted in RFCS.md. 18 requirements, 23 features, 55 rules, 5 RFCs.
Test suite re-run: `python3 -m unittest discover -s tests` gives 66 tests, OK (Python 3.13).

## 1. Status table

| # | Stage | Artifact | Status |
|---|---|---|---|
| 0 | Document existing | n/a (greenfield) | Not applicable |
| 1 | PRD | PRD.md | Done (with open questions, see Inconsistencies) |
| 2 | Verify PRD | PRD-REVIEW.md | Done; its F-1 finding (concurrent runs vs G2) is still unresolved in PRD.md |
| 3 | Features | FEATURES.md | Done |
| 4 | Rules | RULES.md | Done |
| 5 | RFCs | RFCs/ (5 files) + RFCS.md | Done, but no RFC has passed a cold read (rounds 1 and 2 only; round 2 fixes never re-read) |
| 6 | Test strategy | TEST-STRATEGY.md | Done (it found RFCS.md conflict 8, still uncorrected) |
| 7 | Implement | code (`td`, `tests/`) | In progress: RFC-001 to 004 done, RFC-005 In progress |
| 8 | Review | reviews/ | In progress: 4 of 5 reviewed, RFC-005 has no review |
| 9 | Change management | changes/ | Missing (folder does not exist; no change requests, none pending) |
| 10 | Status check | this report | Done |

## 2. Per-RFC progress

```
RFC-001  implemented ✅   reviewed ✅
RFC-002  implemented ✅   reviewed ✅
RFC-003  implemented ✅   reviewed ✅
RFC-004  implemented ✅   reviewed ✅
RFC-005  implemented ⚠️ partial (criteria 1-7, 9 pass; criterion 8 lacks the macOS run)   reviewed ❌ (no reviews/REVIEW-RFC-005.md)
```

Every RFC marked Reviewed has a single `## Round 1` with "PASS with non-blocking findings" and no blocking issues, so the Reviewed status is supported. Spot-checks: `td` has `cmd_clear` and its COMMANDS entry (RFC-004), the 66 tests pass, and RFC-005's own Implementation Notes record manual runs on Python 3.10.20, 3.11.18, 3.12.3 and 3.13 on Linux, all passing. Code supports the statuses in RFCS.md. I did not re-run each criterion by hand; I relied on the passing suite plus the review reports.

## 3. Inconsistencies and unconfirmed items

- **Unconfirmed guesses under code that is built (largest risk).** Nobody confirmed any of these, and RFCs 001 to 004 are already Reviewed on top of them. They are RFCS.md Open conflicts 2 and 10, and the Open Questions in each RFC:
  - names and formats: `TD_FILE`, `~/.td.json`, the keys `version`, `next_id`, `tasks`, the list line `<id> [ ] <text>`, silent `done`/`rm`/`clear`, exit codes 0/1/2
  - `td clear` (F10) was built from IDEA.md's "Maybe clearing all done tasks", not from a user decision
  - the 1 second speed budget at 5,000 tasks, and the `subprocess`/`importlib`/`ctypes`/threading ban, both RFC-005 (In progress) assumptions
  - Counts of "assumption" lines: PRD.md 27, FEATURES.md 12, RULES.md 23, RFC-001 9, RFC-002 8, RFC-003 5, RFC-004 3, RFC-005 7 (line counts, not distinct items).
- **RFCS.md Open conflict 1 (High): G2 "never lose tasks" contradicts F17/DEV-3 (no locking).** The code builds no lock, so two overlapping `td add` runs can drop a task. PRD.md has not been changed. This is the only item that needs a human decision on the PRD; no change request exists in `changes/`.
- **RFCS.md conflict 8 not fixed.** The Features lines of RFC-002, RFC-004 and RFC-005 omit features their criteria cite (F2/F4, F11/F4, F5). Tests follow the criteria, so nothing is broken, but the RFC headers are wrong.
- **Cold reads never passed.** RFCS.md says all five RFCs await a third read. All were implemented without it.
- **RFC-001 review N1 still open.** A deeply nested JSON data file raises `RecursionError` instead of a `TdError` naming the file; `td` has no `RecursionError` handling and no test for it. Non-blocking per the review, but it is a real SAFE-3/F4 gap.
- **RFC-005 predecessor order is fine** (001, 002, 003 all Reviewed before it started). No RFC was implemented before its predecessors.
- **No drift found** between code and PRD/RULES.md in the spot-checks; no feature in the code without an RFC (`clear` has RFC-004). RFC-005's Implementation Notes record no deviations.
- **Housekeeping:** `__pycache__/` at the root and in `tests/` is ignored by .gitignore. The commit history shows each RFC implemented then reviewed in order.

## 4. Next step

Finish RFC-005, then review it. The only blocker to RFC-005 is the macOS run (criterion 8), which cannot be done on this Linux machine. Two choices:

1. If a macOS machine is available: run `python3 -m unittest discover tests` there, record the result under RFC-005 Implementation Notes, and set the RFC-005 Status to Implemented.
2. Otherwise, run the review now on what is implemented and have it state clearly that macOS is unverified.

Recommended command: `/review-rfc RFC-005`. After that, take the High conflict to the PRD owner: `/manage-changes` to decide G2 versus locking (F17).
