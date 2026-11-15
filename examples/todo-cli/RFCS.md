# RFCS: td, a tiny command-line to-do list

Product type: CLI (from PRD.md). All CLI checks apply. Skipped, as PRD.md records: UI design, accessibility, SEO, sessions, scalability, regulatory (plain-text single-user tool). No RFC has a UI, caching, auth or database section for that reason.

Each RFC is implemented by running `/implement-rfc <id>`, for example `/implement-rfc RFC-001`.

## Approach

All code lives in one file, `td` (RULES.md ARCH-1), so RFCs split by responsibility, not by file. Storage comes first because every command depends on it and it carries the hardest requirement (never lose tasks). `list` is built with the CLI framework so the framework is tested end to end without placeholder handlers. Then the mutating commands, the optional `clear`, and last the whole-program checks.

## RFC index

| RFC | Title | Features | Depends on | Successors | Complexity | Status |
|---|---|---|---|---|---|---|
| RFC-001 | Storage core | F1, F2, F3, F4, F5, F15 | none | RFC-002, RFC-003, RFC-004, RFC-005 | High | Reviewed |
| RFC-002 | CLI framework, output rules and `td list` | F7, F11, F12 | RFC-001 | RFC-003, RFC-004, RFC-005 | Medium | Reviewed |
| RFC-003 | `td add`, `td done`, `td rm` | F6, F8, F9, F11 | RFC-001, RFC-002 | RFC-005 | Medium | Reviewed |
| RFC-004 | `td clear` (Should-have) | F10 | RFC-001, RFC-002 | none | Low | Reviewed |
| RFC-005 | Release checks | F13, F14, F15, F16 | RFC-001, RFC-002, RFC-003 | none | Medium | In progress |

## Dependency graph

```
RFC-001 --> RFC-002 --> RFC-003 --> RFC-005
                  \--> RFC-004
```

RFC-005 also depends directly on RFC-001 (data layout, test helpers) and RFC-002 (line format); the arrows show the chain. RFC-001 is the critical path start. After RFC-002, RFC-003 and RFC-004 are independent and can run in parallel. A solo implementer follows the numbers; RFC-004 may be skipped without affecting any other RFC.

## Roadmap (matches the PRD's suggested weekend order)

1. RFC-001: storage with atomic save.
2. RFC-002 and RFC-003: the commands and error handling, with tests.
3. RFC-005: release checks (3.10 and macOS runs).
4. RFC-004: `clear`, if time allows.

## Feature coverage

| Feature | Priority | RFC |
|---|---|---|
| F1, F2, F3, F4, F5 | Must | RFC-001 |
| F6, F8, F9 | Must | RFC-003 |
| F7, F11, F12 | Must | RFC-002 (F11 also exercised in RFC-003) |
| F10 | Should | RFC-004 |
| F13, F14, F15 | Must | RFC-005 (F15 also RFC-001) |
| F16 | Should | RFC-005 |
| F17 to F23 | Won't | Not planned: out of scope for v1 |

Deferred: F17 (locking), see Open conflicts. No Could Have features exist.

## PRD-REVIEW.md High-impact findings

- F-1 (concurrent runs): deferred. F17 is Won't Have and the PRD has not been changed; see Open conflicts.
- F-2 (ids never reused): RFC-001 criteria 5 and 8; RFC-003 criterion 6.
- F-3 (fsync): RFC-001 criteria 9 and 12.

## Cold read status

Round 1: a clean-context reader cold-read each of RFC-001 to RFC-005 (reports in `the cold-reads folder, one file per RFC`). The findings were triaged: guesses that change observable behavior or an interface another RFC uses were fixed in the RFC text; the rest were listed there as the implementer's choice. Every RFC was changed, so all five **await a second cold read**. No RFC has passed a cold read; do not treat any as passed.

Round 2: a clean-context reader cold-read each RFC again, given the RFC plus the RFCs it declares in Depends on (reports in the cold-reads folder, named for the RFC and "round2"). RFC-005's reader got only RFC-003, so its first finding partly reflected that; it led to RFC-005 now declaring RFC-001 and RFC-002 directly. The findings were triaged the same way and fixed in all five RFCs. **The round 2 fixes were not cold-read a third time, so no RFC has passed a cold read; all five stay unpassed and need another read.**

What round 2 changed across RFCs: RFC-002 pins how commands declare arguments (`ARGUMENTS`, subparsers use the same `td:` error class), the closed-stdout rule (broken pipe exits 0, a closed descriptor with output pending exits 1) and the one-line sanitizing of argparse errors; RFC-001 pins check order in `save_store`, which exceptions are converted, the quoted key in structure messages, and how test wrappers tell the directory fsync from the temp file's; RFC-003 resolves the leading-zero and over-long id rules (limit now 4000 digits, message uses the id as typed), the exit code of `td add` with no argument on a corrupt file (1, not 2), and rejects non-UTF-8 text; RFC-004 no longer needs `add` in its criteria; RFC-005 fixes the speed check (fresh copy per run, exit 0 asserted), the subprocess environment and the scan scopes. Several criteria that passed by luck now pin exact values.

What round 1 changed across RFCs: RFC-001 now pins the interfaces the others use (`TdError(message, exit_code=1)`, `UsageError`, `resolve_path`, `load_store`, `save_store`, `add_task`, `find_task`, `remove_task`, `clear_done`); RFC-002 pins the handler contract `handler(args, store, path) -> list[str]`, the order in which errors win, and the `td:` prefix for usage errors; RFC-003 to RFC-005 refer to those sections instead of guessing.

## Open conflicts

1. **Concurrent runs contradict goal G2 (High, needs a PRD.md decision).** PRD G2 and D-4 say tasks are never lost, but PRD Open Question 9, FEATURES F17 and RULES DEV-3 choose atomic replace only, so two overlapping `td add` runs can drop one task. Followed: PRD Open Question 9 and F17 (no lock), because adding a lock would add a requirement nobody has approved. RFC-001 builds no lock. PRD.md must either add a locking requirement (then F17 becomes Must and a new RFC is added) or reword G2 to "never lose tasks to a crash". Not settled here.
2. **Assumed names and formats nobody confirmed** (not conflicts between artifacts, but `/implement-rfc` should show them to the user before code depends on them): `TD_FILE` and `~/.td.json`; file keys `version`, `next_id`, `tasks`; list line `<id> [ ] <text>`; `done`, `rm` and `clear` print nothing; exit codes 0, 1, 2; a broken pipe exits 0 (a closed descriptor with output pending exits 1); the 1 second performance budget. Each RFC lists its own under Open Questions.
3. **PRD Open Question 7 (prototype):** none assumed. If one exists, RULES.md naming rules and these RFCs need re-deriving from it.
4. **RULES.md NAME-3 and DEV-4 read together (note, no higher artifact blocked).** NAME-3 says `TD_FILE` and `~/.td.json` appear nowhere else "as string literals"; DEV-4 asks for docstrings. RFC-001 reads docstrings and messages as literals, so they refer to the constants. RULES.md could say so explicitly; nothing is blocked.
5. **RULES.md OUT-2 against RFC-002's `KeyboardInterrupt` handling (note).** OUT-2 allows only exit codes 0, 1 and 2, so Ctrl-C exits 1 with `td: interrupted`. Nobody confirmed this.
6. **RFC-005 bans `subprocess`, `importlib`, `ctypes` and threading modules in `td`.** This is stricter than SEC-2 and PERF-2 and weakens nothing; it is an assumption (RFC-005 Open Questions).
7. **RFC-005 criterion 9 narrows what `td` strings may contain (note, no higher artifact blocked).** Docstrings are exempt, but help text and messages must avoid `/` and `\`. RULES.md DEV-4 and F15 are not weakened; it is an assumption about how the separator check is scanned.
8. **RFC Features lines understate several criteria (found by `/test-strategy`; needs RFC correction).** RFC-002 criterion 4 cites F2 and criterion 7 cites F4, but its `**Features**` line is F7, F11, F12. RFC-004 criterion 5 cites F11 and criterion 6 cites F4, but its line is F10. RFC-005 criterion 4 cites F5, but its line is F13, F14, F15, F16. Followed: the RFC criteria (the tests are planned as written, with the feature's own priority); the header lines should add those features, or the criteria should stop citing them. The index and Feature coverage tables here are unchanged, since no feature is uncovered.
9. **RFC-001 criterion 14 cites F11, which RFC-001 does not list (note).** F11's error path is RFC-002's; the criterion tests only the exception classes. Nothing is blocked.
10. **`td clear` (F10) is built, decided from IDEA.md, not confirmed by the user (RFC-004).** The RFC leaves the decision to the user; IDEA.md says "Maybe clearing all done tasks", so it was built. If the user prefers to skip it, remove `cmd_clear` and its `COMMANDS` entry and set RFC-004 back to Not started with F10 deferred.
