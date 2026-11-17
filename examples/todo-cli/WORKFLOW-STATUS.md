# Workflow status (2026-11-16)

`trace-check.py`: 0 failures, 2 warnings (F11 split across RFC-002 and RFC-003; F15 split across RFC-001 and RFC-005; both intended). 19 requirements, 23 features, 56 rules, 6 RFCs.
Test suite re-run: `python3 -m unittest discover -s tests` gives 91 tests, OK, 1 skipped (Python 3.13.18; the skip is the unreadable-directory test, which cannot run as root).

## 1. Status table

| # | Stage | Artifact | Status |
|---|---|---|---|
| 0 | Document existing | n/a (greenfield) | Not needed |
| 1 | PRD | PRD.md | Done (about 28 assumption markers; Open Questions 19 and 20 unconfirmed) |
| 2 | Verify PRD | PRD-REVIEW.md | Done; F-1 settled by CR-001 (accepted by the person running the example, not the user) |
| 3 | Features | FEATURES.md | Done |
| 4 | Rules | RULES.md | Done (Open Question 10 on the Python 3.10 floor is stale: RFC-005 ran 3.10) |
| 5 | RFCs | RFCs/ (6) + RFCS.md | Done; only RFC-006 passed a cold read; RFC-001 to RFC-005 never did |
| 6 | Test strategy | TEST-STRATEGY.md | Stale: behind RFC-006 (12 criteria, not 11; rows 1, 9, 11); RFCS.md conflict 8 uncorrected |
| 7 | Implement | `td`, `tests/` | In progress: RFC-001 to RFC-006 all have code; RFC-002 is back In progress (blocking review issues open) |
| 8 | Review | reviews/ | In progress: 5 of 6 reviewed clean; RFC-002 has blocking issues (round 4) and its fix round 3 is unreviewed |
| 9 | Change management | changes/ | In progress: CR-001 applied; CHANGE-REQUEST-002 has four changes, all Decision: pending |
| 10 | Status check | this report | Done |

## 2. Per-RFC progress

```
RFC-001  Reviewed          implemented ✅   reviewed ✅ (round 5, no blocking issues; CR-002 Change 2 pending would reopen it)
RFC-002  In progress       implemented ✅   reviewed ❌ (round 4 blocking: B1 Ctrl-C traceback, conflict 12; fix round 3 closed B1, nobody reviewed it; conflict 12 undecided)
RFC-003  Reviewed          implemented ✅   reviewed ✅ (round 3, no blocking issues; conflict 12 touches it, review should cite it)
RFC-004  Reviewed          implemented ✅   reviewed ✅ (round 1, no blocking issues)
RFC-005  Reviewed          implemented ✅   reviewed ✅ (round 1; criterion 8 macOS run outstanding, on the release checklist)
RFC-006  Reviewed          implemented ✅   reviewed ✅ (round 1, no blocking issues)
```

Statuses were checked against the code: the suite passes, and no commit to `td` or `tests/` came after the last review of RFC-001, RFC-003 to RFC-006 other than those reviews' own fix rounds. RFC-002's last code commit (`92c3003`, fix round 3) is after its last review (`a1926ba`, round 4), so RFC-002 is correctly not Reviewed. RFC-006's lock (`data_lock`, `_check_parent`) is present as its notes say.

## 3. Inconsistencies

- **Conflict 12 (RFCS.md, blocks RFC-002):** RFC-002 Open Question 3 (closed stdout with output pending exits 1; handler saves then prints) against RULES.md SAFE-6 and F11. `td add x >&-` saves the task and exits 1, so a retrying script adds it twice. Undecided: CHANGE-REQUEST-002 Change 3 is pending. Touches RFC-002 and RFC-003.
- **Unreviewed fix round:** RFC-002 fix round 3 (`92c3003`) replaced `import signal` with `_signal` and added three tests; no review has seen it. RFCS.md Follow-up RFC-002 (round 4, F5) is still open: no test runs the timing loop against the real `td`. Conflict 11 (Ctrl-C during interpreter start-up cannot be caught by a one-file program) is for the user.
- **Pending changes nobody decided:** CHANGE-REQUEST-002 Changes 1 (`add -h` and a mid-text `--`), 2 (file mode kept on save; reverses RFC-001 criterion 5), 3 (above) and 4 (`--help` names the data file) are all pending. Also CR-001 (lock) was accepted by the person running the example, not by the user; follow-up RFC-001 (round 3, F8) asks the user to confirm or reverse it. RFC-006 rests on it and on PRD Open Questions 19 and 20.
- **Unconfirmed assumptions under implemented code (RFCS.md conflict 2, 5, 10):** `TD_FILE`, `~/.td.json`, key names, list line `<id> [ ] <text>`, exit codes, 1 second budget, Ctrl-C exits 1, and `td clear` built from "maybe" in IDEA.md. RFC-002 (In progress) depends on conflicts 2, 5, 11 and 12.
- **Release is not done:** RFCS.md Release checklist item 1 (macOS run, RFC-005 criterion 8) is unchecked.
- **Stale notes:** `RFCs/RFC-006-Run-Lock.md` line 76 still says "Implemented, waiting for review. ... No reviews/REVIEW-RFC-006.md exists" though the review exists and passed. `RFCs/RFC-004-Clear-Done.md` line 47 says "no lock" (RFC-006 follow-up F4). TEST-STRATEGY.md is behind RFC-006. RFCS.md conflict 8 (Features lines of RFC-002, RFC-004, RFC-005 omit features their criteria cite) is uncorrected. RFCS.md Roadmap and Open conflict 1 text say "RFC-006 is implemented" correctly; the RFC-006 file does not.
- **Cold reads:** RFC-001 to RFC-005 never passed one; all were implemented and reviewed anyway.
- **Open non-blocking follow-ups:** about 20 in RFCS.md. First to close: RFC-006 F1 (any `flock` error treated as "held"), RFC-005 F2 (`TD_RELEASE_NESTED` set silently skips criteria 5 and 6), RFC-001 F11 (fsync-order test only on a small store), RFC-002 F5.
- **Cross-RFC reads:** every RFC's Depends on line covers what it uses; no undeclared predecessor; no RFC implemented before its predecessors were Reviewed (RFC-006 started after RFC-001 to RFC-004 were Reviewed). No code without an RFC.
- **Versions:** RULES.md states only Python 3.10 as the floor. 3.10 reached end of life in October 2026; it is the PRD's NFR-3 choice, not a drift, but worth a line in the PRD.

## 4. Next step

The user must decide CHANGE-REQUEST-002 Change 3 (and ideally Changes 1, 2 and 4); nothing else unblocks RFC-002. After that decision, apply it in RFC-002 and RFC-003 and run `/implement-rfc RFC-002`, then `/review-rfc RFC-002` to review fix round 3 and clear conflict 12. If the user cannot decide yet, run `/review-rfc RFC-002` now: it reviews the unreviewed fix round 3, and conflict 12 stays the only blocker. In parallel, run `/test-strategy` to bring TEST-STRATEGY.md up to RFC-006.
