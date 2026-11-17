# RFCS: td, a tiny command-line to-do list

Product type: CLI (from PRD.md). All CLI checks apply. Skipped, as PRD.md records: UI design, accessibility, SEO, sessions, scalability, regulatory (plain-text single-user tool). No RFC has a UI, caching, auth or database section for that reason.

Each RFC is implemented by running `/implement-rfc <id>`, for example `/implement-rfc RFC-001`.

## Approach

All code lives in one file, `td` (RULES.md ARCH-1), so RFCs split by responsibility, not by file. Storage comes first because every command depends on it and it carries the hardest requirement (never lose tasks). `list` is built with the CLI framework so the framework is tested end to end without placeholder handlers. Then the mutating commands, the optional `clear`, and last the whole-program checks.

## RFC index

| RFC | Title | Features | Depends on | Successors | Complexity | Status |
|---|---|---|---|---|---|---|
| RFC-001 | Storage core | F1, F2, F3, F4, F5, F15 | none | RFC-002, RFC-003, RFC-004, RFC-005, RFC-006 | High | Reviewed |
| RFC-002 | CLI framework, output rules and `td list` | F7, F11, F12 | RFC-001 | RFC-003, RFC-004, RFC-005, RFC-006 | Medium | In progress |
| RFC-003 | `td add`, `td done`, `td rm` | F6, F8, F9, F11 | RFC-001, RFC-002 | RFC-005, RFC-006 | Medium | Reviewed |
| RFC-004 | `td clear` (Should-have) | F10 | RFC-001, RFC-002 | RFC-006 | Low | Reviewed |
| RFC-005 | Release checks | F13, F14, F15, F16 | RFC-001, RFC-002, RFC-003 | none | Medium | Reviewed |
| RFC-006 | Lock for concurrent runs (CR-001) | F17 | RFC-001, RFC-002, RFC-003, RFC-004 | none | Medium | Reviewed |

## Dependency graph

```
RFC-001 --> RFC-002 --> RFC-003 --> RFC-005
                  \--> RFC-004
RFC-003 --> RFC-006 (also after RFC-001, RFC-002, RFC-004)
```

RFC-006 (CR-001) depends on RFC-001 to RFC-004, so it is last in the chain; it is not a predecessor of RFC-005, and neither waits for the other. RFC-005 also depends directly on RFC-001 (data layout, test helpers) and RFC-002 (line format); the arrows show the chain. RFC-001 is the critical path start. After RFC-002, RFC-003 and RFC-004 are independent and can run in parallel. A solo implementer follows the numbers; RFC-004 may be skipped without affecting any other RFC.

## Roadmap (matches the PRD's suggested weekend order)

1. RFC-001: storage with atomic save.
2. RFC-002 and RFC-003: the commands and error handling, with tests.
3. RFC-005: release checks (3.10 and macOS runs).
4. RFC-004: `clear`, if time allows.
5. RFC-006: the lock for concurrent runs (added by CR-001, after the first version of this roadmap). RFC-001 to RFC-004 are Reviewed, so it can start.

## Feature coverage

| Feature | Priority | RFC |
|---|---|---|
| F1, F2, F3, F4, F5 | Must | RFC-001 |
| F6, F8, F9 | Must | RFC-003 |
| F7, F11, F12 | Must | RFC-002 (F11 also exercised in RFC-003) |
| F10 | Should | RFC-004 |
| F13, F14, F15 | Must | RFC-005 (F15 also RFC-001) |
| F16 | Should | RFC-005 |
| F17 | Must | RFC-006 (added by CR-001; was Won't) |
| F18 to F23 | Won't | Not planned: out of scope for v1 |

Nothing is deferred. F17 (locking) was deferred until CR-001 made it a Must. No Could Have features exist.

## PRD-REVIEW.md High-impact findings

- F-1 (concurrent runs): RFC-006 (CR-001, accepted by the person running the example, not by the user). Open conflict 1 is closed.
- F-2 (ids never reused): RFC-001 criteria 5 and 8; RFC-003 criterion 6.
- F-3 (fsync): RFC-001 criteria 9 and 12.

## Cold read status

Round 1: a clean-context reader cold-read each of RFC-001 to RFC-005 (reports in `the cold-reads folder, one file per RFC`). The findings were triaged: guesses that change observable behavior or an interface another RFC uses were fixed in the RFC text; the rest were listed there as the implementer's choice. Every RFC was changed, so all five **await a second cold read**. No RFC has passed a cold read; do not treat any as passed.

Round 2: a clean-context reader cold-read each RFC again, given the RFC plus the RFCs it declares in Depends on (reports in the cold-reads folder, named for the RFC and "round2"). RFC-005's reader got only RFC-003, so its first finding partly reflected that; it led to RFC-005 now declaring RFC-001 and RFC-002 directly. The findings were triaged the same way and fixed in all five RFCs. **The round 2 fixes were not cold-read a third time, so no RFC has passed a cold read; all five stay unpassed and need another read.**

What round 2 changed across RFCs: RFC-002 pins how commands declare arguments (`ARGUMENTS`, subparsers use the same `td:` error class), the closed-stdout rule (broken pipe exits 0, a closed descriptor with output pending exits 1) and the one-line sanitizing of argparse errors; RFC-001 pins check order in `save_store`, which exceptions are converted, the quoted key in structure messages, and how test wrappers tell the directory fsync from the temp file's; RFC-003 resolves the leading-zero and over-long id rules (limit now 4000 digits, message uses the id as typed), the exit code of `td add` with no argument on a corrupt file (1, not 2), and rejects non-UTF-8 text; RFC-004 no longer needs `add` in its criteria; RFC-005 fixes the speed check (fresh copy per run, exit 0 asserted), the subprocess environment and the scan scopes. Several criteria that passed by luck now pin exact values.

RFC-006 (added by CR-001), round 1: a clean-context reader, given RFC-001 to RFC-004, found five guesses (`cold-reads/RFC-006-round1.md`). Four changed behavior or an interface and were fixed in the RFC: which errors beat a held lock (only argparse errors skip it; handler validation runs under the lock), `data_lock` as a class so `td` needs no `contextlib`, which `OSError`s mean "held", and an unreadable data directory (exit 1). The symlink-versus-realpath question is listed in the RFC as the implementer's choice. Its criteria were also rewritten to observable behavior (the import scan and the call-order and call-count wrappers are gone). **RFC-006 awaits a second cold read** and has not passed.

RFC-006, round 2 (`cold-reads/RFC-006-round2.md`): a clean-context reader found three guesses, all fixed in the RFC: the "held" retry set applies to `flock` only, so an `os.open` error on an unreadable directory is reported at once (criterion 11); the parent check may be extracted from `load_store` as a pure refactor or applied by the same rule, with the observable rule pinned (criterion 8 gained the parent-is-a-file case); and RFC-005's checks were read and need no edit (`fcntl` and `time` are stdlib, neither is banned), with the one constraint that new strings in `td` contain no `/` or `\`. **The round 2 fixes were not cold-read again, so RFC-006 has not passed**; it needs one more read of the changed text.

RFC-006, round 3 (`cold-reads/RFC-006-round3.md`): a clean-context reader of the changed text found no guess that changes behavior or an interface. **RFC-006 passed its cold read.**

What round 1 changed across RFCs: RFC-001 now pins the interfaces the others use (`TdError(message, exit_code=1)`, `UsageError`, `resolve_path`, `load_store`, `save_store`, `add_task`, `find_task`, `remove_task`, `clear_done`); RFC-002 pins the handler contract `handler(args, store, path) -> list[str]`, the order in which errors win, and the `td:` prefix for usage errors; RFC-003 to RFC-005 refer to those sections instead of guessing.

## Open conflicts

1. **[CLOSED by CR-001] Concurrent runs against goal G2.** Resolved in favour of G2: PRD.md gained NFR-10 and D-9, F17 is a Must, RULES.md has SAFE-8, and RFC-006 builds the lock. **Accepted by the person running the example on the user's behalf, not by the user in IDEA.md**, who has not seen it; the other option was rewording G2 to "never lose tasks to a crash". RFC-006 is implemented, so the code now has the lock and G2 is met for overlapping runs. The reviews of RFC-001 and RFC-003 (round 2) that waited on this conflict are no longer blocked by it. Still open for the user, as assumptions: the 10 second wait and no lock on Windows (PRD Open Questions 19 and 20).
2. **Assumed names and formats nobody confirmed** (not conflicts between artifacts, but `/implement-rfc` should show them to the user before code depends on them): `TD_FILE` and `~/.td.json`; file keys `version`, `next_id`, `tasks`; list line `<id> [ ] <text>`; `done`, `rm` and `clear` print nothing; exit codes 0, 1, 2; a broken pipe exits 0 (a closed descriptor with output pending exits 1); the 1 second performance budget. Each RFC lists its own under Open Questions.
3. **PRD Open Question 7 (prototype):** none assumed. If one exists, RULES.md naming rules and these RFCs need re-deriving from it.
4. **RULES.md NAME-3 and DEV-4 read together (note, no higher artifact blocked).** NAME-3 says `TD_FILE` and `~/.td.json` appear nowhere else "as string literals"; DEV-4 asks for docstrings. RFC-001 reads docstrings and messages as literals, so they refer to the constants. RULES.md could say so explicitly; nothing is blocked.
5. **RULES.md OUT-2 against RFC-002's `KeyboardInterrupt` handling (note).** OUT-2 allows only exit codes 0, 1 and 2, so Ctrl-C exits 1 with `td: interrupted`. Nobody confirmed this.
6. **RFC-005 bans `subprocess`, `importlib`, `ctypes` and threading modules in `td`.** This is stricter than SEC-2 and PERF-2 and weakens nothing; it is an assumption (RFC-005 Open Questions).
7. **RFC-005 criterion 9 narrows what `td` strings may contain (note, no higher artifact blocked).** Docstrings are exempt, but help text and messages must avoid `/` and `\`. RULES.md DEV-4 and F15 are not weakened; it is an assumption about how the separator check is scanned.
8. **RFC Features lines understate several criteria (found by `/test-strategy`; needs RFC correction).** RFC-002 criterion 4 cites F2 and criterion 7 cites F4, but its `**Features**` line is F7, F11, F12. RFC-004 criterion 5 cites F11 and criterion 6 cites F4, but its line is F10. RFC-005 criterion 4 cites F5, but its line is F13, F14, F15, F16. Followed: the RFC criteria (the tests are planned as written, with the feature's own priority); the header lines should add those features, or the criteria should stop citing them. The index and Feature coverage tables here are unchanged, since no feature is uncovered.
9. **RFC-001 criterion 14 cites F11, which RFC-001 does not list (note).** F11's error path is RFC-002's; the criterion tests only the exception classes. Nothing is blocked.
10. **`td clear` (F10) is built, decided from IDEA.md, not confirmed by the user (RFC-004).** The RFC leaves the decision to the user; IDEA.md says "Maybe clearing all done tasks", so it was built. If the user prefers to skip it, remove `cmd_clear` and its `COMMANDS` entry and set RFC-004 back to Not started with F10 deferred.

11. **Ctrl-C before the first line of `td` runs (RFC-002 fix round 2, for the user):** `td` now catches an interrupt during its own imports (fix round 3 measured it: sweep 8-48 ms, 252 runs, 72 tracebacks before and 48 after, all 48 in the start-up window; the earlier "60 tries, 0" was a bad measurement, see RFC-002 Implementation Notes), but an interrupt during Python's own start-up cannot be caught by a one-file program (ARCH-1). Accept that limit, or ask for a launcher. OUT-7 is not weakened; nobody confirmed.

12. **RFC-002 against RULES.md SAFE-6 and FEATURES F11 for `add`, `done` and `rm` (found by `/review-rfc RFC-001` round 5 in CHANGE-REQUEST-002 Change 3; unresolved).** RFC-002 Open Question 3 says a closed or missing stdout with output pending exits 1, and the handler prints after saving; SAFE-6 says a failed command never modifies the data file. A run with `>&-` saves the task and exits 1, so a retrying script adds it twice. Not decided: Change 3 is pending and nobody accepted it. **Still open after RFC-002 fix round 3 (not decided; RFC-002 stays In progress for it).** **Judged blocking for RFC-002 in its round 4 review** (a broken rule, SAFE-6, reproduced with `td add x >&-`; unaccepted; CHANGE-REQUEST-002 Change 3 pending). Touches RFC-002 and RFC-003 (their reviews should cite it); RFC-001 is not affected (`save_store` and `load_store` do not print).

## Release checklist

Checks that need a person or another machine. They do not block an RFC's Status, but the release is not done until each is recorded.

1. **[ ] RFC-005 criterion 8, macOS:** run `python3 -m unittest discover tests` on a macOS machine (any Python 3.10 or newer; 3.10 is already covered on Linux) and record date, interpreter and result under `## Implementation Notes` in RFCs/RFC-005-Release-Checks.md. Also worth noting there: `flock` on a directory on macOS (RFC-006 follow-up F6).

## Follow-ups

Non-blocking findings from reviews. Each carries its RFC.

- **[CLOSED in the RFC-001 fix round] RFC-001 (round 2, F1):** add `id` 0, a negative `id` and `version` -1 to the criterion 6 corrupt cases; mutating `task["id"] < 1` to `< 0` passes the suite today.
- **[CLOSED in the RFC-001 fix round] RFC-001 (round 2, F2):** duplicate JSON object keys load silently (last wins); consider an `object_pairs_hook` that treats them as corrupt.
- **[CLOSED in the RFC-001 fix round] RFC-001 (round 2, F3):** no test fails if `O_EXCL` is dropped from the temp-file open; add one (for example pre-create the temp name).
- **[CLOSED in the RFC-001 fix round] RFC-001 (round 2, F4):** test `add_task` after removing every task in a store whose `next_id` is far above its highest id.
- **[CLOSED in the RFC-001 fix round] RFC-001 (round 2, F5):** `save_store` with an oversized `next_id` raises a raw `ValueError` from `json.dumps`; unreachable today, convert to `TdError` if a later RFC builds stores from outside input.
- **RFC-001 (round 2, F6):** a 4300-digit integer in the data file reports Python's own limit text; wording only.
- **[CLOSED by RFC-006] RFC-001 (round 3, F7):** RFC-001's Implementation Notes "Future" line (locking open) went stale when RFC-006 landed; reworded to say the lock is built and RFC-001's functions are unchanged. G2 is now met for overlapping runs.
- **RFC-001 (round 3, F8):** CR-001 (lock, closes Open conflict 1) was accepted by the person running the example, not by the user in IDEA.md; ask the user to confirm D-9 or reverse it as the CR describes.
- **[CLOSED in the RFC-002 fix round] RFC-002 (round 2, F1):** `td --help` lists `done tasks` and `rm tasks`, which repeat the command name; give each command a help text that says what it does. Wording only (RFC-003's commands).
- **[CLOSED in the RFC-002 fix round] RFC-002 (round 2, F2):** no test covers `KeyboardInterrupt` (`td: interrupted`, exit 1); mutating the exit code to 0 passes the suite.
- **RFC-002 (round 2, F3):** `td frob 2>&-` exits 1 with no message, and `td --help` into a closed pipe on a slow reader may be reported as an unexpected error; contrived, fix only if output setup is touched again.
- **RFC-003 (round 2, F1):** the error for an over-long id echoes the whole id (a 5000-character stderr line); the RFC asks for the id as typed, so consider truncating if message wording is revisited.
- **[CLOSED by RFC-006] RFC-002 (round 3, F4):** RFC-002's Implementation Notes ("no lock") went stale when RFC-006 landed; reworded to say RFC-006 added the lock in `main`.
- **[CLOSED by RFC-006] RFC-003 (round 3, F2):** RFC-003's Implementation Notes ("Future" line, the B1 text and the "no lock" line) said a lock was still open; reworded. Overlapping `add`, `done` and `rm` now take turns (NFR-10 met).
- **RFC-001 (round 4, F9):** no test asserts the `empty file` message; disabling the empty-file check still passes because json rejects the empty text as invalid JSON (same exit code and path, different wording). Add the assertion to the criterion 6 case.
- **RFC-006 (round 1, F1):** no test makes `flock` fail with a non-"held" error; treating every `flock` error as "held" passes the suite. Add a criterion and a test (patch `fcntl.flock` to raise `ENOLCK`; expect exit 1 at once).
- **RFC-006 (round 1, F2):** criterion 11's test does not assert the OS error text or a time bound; it only caught a retry-as-held break through the subprocess timeout.
- **RFC-006 (round 1, F3):** a symlinked `TD_FILE` locks the realpath directory and no test covers it (the RFC calls it the implementer's choice).
- **RFC-006 (round 1, F4):** RFC-004's Implementation Notes still say "no lock"; TEST-STRATEGY.md rows 1, 9 and 11 and its RFC-006 criteria count (11, now 12) are behind the RFC.
- **RFC-006 (round 1, F5):** test 2 does not assert that a waiting run wrote nothing while waiting.
- **RFC-006 (round 1, F6):** `flock` on a directory on macOS and on network filesystems is untested; the default `~/.td.json` locks the home directory.
- **RFC-005 (round 1, F1):** the criterion 2 scan is evaded by a computed name (`getattr(os, "sys" + "tem")` passes); a regression guard, not a sandbox, as the RFC allows. Change only if the ban must be strict.
- **RFC-005 (round 1, F2):** with `TD_RELEASE_NESTED` set in a developer's shell, criteria 5 and 6 skip silently and the suite reports OK; fail on it in the top-level run or pick a name nobody sets by accident.
- **RFC-005 (round 1, F3):** the fixture's `next_id` (5) equals highest id plus one, so criterion 4 cannot tell whether `add` reads the stored `next_id`; use a gap (for example `next_id` 7). The id-reuse tests in RFC-001 and RFC-003 cover the behavior meanwhile.
- **RFC-005 (round 1, F4):** the nested run doubles the suite time (about 18 s in all); revisit if the suite grows.
- **RFC-005 (round 1, F5):** macOS run still not done (Release checklist item 1); the release is not done until it is recorded. `import tomllib` passes criteria 1 and 7 on 3.13 and fails only on 3.10, so the 3.10 run is the real floor guard.
- **[CLOSED in the RFC-001 fix round 3] (blocking) RFC-001 (BUG-REPORT-001 item 4, CHANGE-REQUEST-002):** the fsync test does not check what is on disk when fsync runs. Reproduce: delete `handle.flush()` in `save_store`, run `python3 -m unittest discover tests`; all 85 pass although fsync now runs on an empty temp file (a probe saw `size at fsync: 0`). Moving the fsync before the write also passes. Expected: the test records the temp file's size when `os.fsync` is called on it and fails on both mutations (criteria 9 and 12, SAFE-1, F3). Fix with `/implement-rfc RFC-001`, then `/review-rfc RFC-001`.
- **[CLOSED in the RFC-002 fix round 2] (blocking) RFC-002 (BUG-REPORT-001 item 5, CHANGE-REQUEST-002):** Ctrl-C in the first 5 to 40 ms prints a Python traceback instead of `td: interrupted` (31 of 60 tries; OUT-7, RFC-002 error path). Reproduce: `for i in $(seq 60); do TD_FILE=$(mktemp -u) python3 td list 2>err & sleep 0.02; kill -INT $!; wait $!; grep -l Traceback err; done` and count. The `except KeyboardInterrupt` is inside `main`, so an interrupt during imports and module load escapes it. If an interrupt before the first line of `td` runs cannot be caught, record that as an open question for the user instead of weakening OUT-7. Fix with `/implement-rfc RFC-002`, then `/review-rfc RFC-002`.
- **RFC-001 (round 5, F10):** CHANGE-REQUEST-002 Change 2 (a save keeps an existing data file's mode; a read-only data file is refused, BUG-REPORT-001 item 2) is pending and reverses RFC-001 criterion 5 and Open Question 4. If the user accepts it, set RFC-001 to Spec changed and run a fix round (modes 600, 640, 444 before and after a save).
- **RFC-001 (round 5, F11):** `FsyncOrderTest.test_order` checks the temp file's size on one small store; add a store larger than 8 KiB so a partial flush is also caught. Hardening only; the flush mutation is caught today.
- **RFC-002 (round 4, F5, still open: fix round 3 added three deterministic tests, not a timing-loop test):** after B1 is fixed, add a test that sends SIGINT at several delays against the real `td` and accepts only `td: interrupted` (or nothing, in the interpreter start-up window); today no test runs the follow-up's reproduction.
- **[CLOSED in the RFC-002 fix round 3] (blocking) RFC-002 (round 4, B1, reopens BUG-REPORT-001 item 5):** the Ctrl-C fix is incomplete. The follow-up's loop still prints a traceback in 29 of 60 tries (Linux, Python 3.13), not 0. About 40 of 72 tracebacks seen at 8 to 48 ms name `td` line 4, `import signal`, which runs before the handler is installed (`signal` pulls in `enum`, `functools`, `collections`); the rest are inside Python's own start-up (Open conflict 11). Fix: install the handler before any heavy import (for example through the built-in `_signal` module), add a test that interrupts during the import of `signal` itself, and correct the "0 of 60" note in RFC-002. Then `/review-rfc RFC-002`.
- **Pending changes, not Follow-ups:** CHANGE-REQUEST-002 changes 1 to 4 (BUG-REPORT-001 items 1, 2, 3, 6) wait for the user to accept or reject them. Change 3 shows RFC-002 (closed stdout exits 1) against SAFE-6 for `add`, `done` and `rm`; see that file.
