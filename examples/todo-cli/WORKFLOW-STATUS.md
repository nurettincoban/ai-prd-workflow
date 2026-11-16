# Workflow status (2026-11-16)

`trace-check.py`: 0 failures, 2 warnings (F11 split across RFC-002 and RFC-003; F15 split across RFC-001 and RFC-005; both are intended splits noted in RFCS.md). 19 requirements, 23 features, 56 rules, 6 RFCs.
Test suite re-run: `python3 -m unittest discover -s tests` gives 85 tests, OK, 1 skipped (Python 3.13.18; the skip is the unreadable-directory test, which cannot run as root). RFC-005's notes record the same result on 3.10, 3.11 and 3.12 (Linux).

## 1. Status table

| # | Stage | Artifact | Status |
|---|---|---|---|
| 0 | Document existing | n/a (greenfield) | Not needed |
| 1 | PRD | PRD.md | Done (about 30 assumption markers and Open Questions 19 and 20 still unconfirmed, see Inconsistencies) |
| 2 | Verify PRD | PRD-REVIEW.md | Done; its F-1 finding was settled by CR-001 (accepted by the person running the example, not by the user) |
| 3 | Features | FEATURES.md | Done |
| 4 | Rules | RULES.md | Done |
| 5 | RFCs | RFCs/ (6 files) + RFCS.md | Done; RFC-006 passed a cold read (round 3); RFC-001 to RFC-005 never passed one (round 2 fixes were not re-read) |
| 6 | Test strategy | TEST-STRATEGY.md | Stale: its RFC-006 criteria count (11) and rows 1, 9, 11 are behind the RFC (12 criteria); RFCS.md conflict 8 is still uncorrected |
| 7 | Implement | `td`, `tests/` | Done: RFC-001 to RFC-006 all implemented |
| 8 | Review | reviews/ | Done: 6 of 6 reviewed, no blocking issues open |
| 9 | Change management | changes/CHANGE-REQUEST-001.md | Done: CR-001 applied (RFC-006); no change request pending |
| 10 | Status check | this report | Done |

## 2. Per-RFC progress

```
RFC-001  Reviewed   implemented ✅   reviewed ✅ (round 4, no blocking issues)
RFC-002  Reviewed   implemented ✅   reviewed ✅ (round 3, no blocking issues)
RFC-003  Reviewed   implemented ✅   reviewed ✅ (round 3, no blocking issues)
RFC-004  Reviewed   implemented ✅   reviewed ✅ (round 1, no blocking issues)
RFC-005  Reviewed   implemented ✅   reviewed ✅ (round 1; criterion 8 macOS run still outstanding, on the release checklist)
RFC-006  Reviewed   implemented ✅   reviewed ✅ (round 1, no blocking issues)
```

Statuses were checked against the code: the suite passes, no commit to `td` or `tests/` came after the last review of each RFC, and RFC-006's lock (`data_lock`, `_check_parent`, `_LOCK_POLL_SECONDS`) is present as its notes say.

## 3. Inconsistencies

- **Release is not done:** RFCS.md Release checklist item 1 (macOS run of the suite, RFC-005 criterion 8) is unchecked. Nothing says the suite passes on macOS.
- **CR-001 not confirmed by the user:** the lock (F17, D-9, SAFE-8, RFC-006) was accepted by the person running the example. Follow-up RFC-001 (round 3, F8) asks the user to confirm or reverse it. PRD Open Questions 19 and 20 (10 second wait, no lock on Windows) are assumptions too. RFC-006 is built on them.
- **Stale notes:** `RFCs/RFC-004-Clear-Done.md` line 47 still says "no lock" (RFC-006 follow-up F4). TEST-STRATEGY.md is behind RFC-006 (12 criteria, not 11). RFCS.md conflict 8 (RFC-002, RFC-004, RFC-005 Features lines omit features their criteria cite) is still uncorrected.
- **Cold reads:** RFC-001 to RFC-005 never passed one; all were implemented and reviewed anyway.
- **Unconfirmed assumptions under implemented code:** RFCS.md conflict 2 (`TD_FILE`, `~/.td.json`, key names, list line format, exit codes, 1 second budget), conflict 5 (Ctrl-C exits 1) and conflict 10 (`td clear` was built from "maybe" in IDEA.md). Code is built on these guesses and the user has not seen them. RULES.md still lists the Python 3.10 floor as unverified (Open Question 10), though RFC-005 has now run 3.10.20; the line is stale.
- **Open non-blocking follow-ups:** about 15 are open in RFCS.md (RFC-001 F6 and F9, RFC-002 F3, RFC-003 F1, RFC-005 F1 to F5, RFC-006 F1 to F6). The test gaps worth closing first: RFC-006 F1 (any `flock` error is treated as "held") and RFC-005 F2 (`TD_RELEASE_NESTED` set in the environment skips criteria 5 and 6 silently).
- **Cross-RFC reads:** every RFC's Depends on line covers what it uses; RFC-006 lists RFC-001 to RFC-004. No undeclared predecessor and no RFC implemented before its predecessors were Reviewed. No code without an RFC.
- **Versions:** RULES.md states only Python 3.10 as the floor. 3.10 reaches end of life in October 2026, so the floor is now past end of life, but it is the PRD's NFR-3 choice, not a drift. Worth a line in the PRD.

## 4. Next step

Run the suite on a macOS machine (`python3 -m unittest discover tests`) and record date, interpreter and result under `## Implementation Notes` in `RFCs/RFC-005-Release-Checks.md`, then tick item 1 of the Release checklist in RFCS.md. That is the only thing standing between this and a finished release. In parallel, ask the user to confirm CR-001 (D-9) and the conflict 2 names and formats. To refresh the stale documents, run `/test-strategy` to bring TEST-STRATEGY.md up to RFC-006.
