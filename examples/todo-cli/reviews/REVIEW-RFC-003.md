# Review: RFC-003 `td add`, `td done`, `td rm`

Reviewer context: fresh session, did not write the code. Commit reviewed: `e3a3497 /implement-rfc RFC-003`. Files changed per Implementation Notes: `td`, the RFC file, `RFCS.md`, `tests/test_commands.py`. The commit matches that list.

## Round 1 -- 2026-11-15

**Overall verdict: PASS with non-blocking findings. Overall risk: Low. Status set: Reviewed.**

Product type (PRD.md): CLI. Applied: command and flag design, exit codes, stdout/stderr separation, scripting, encoding, environment handling. Skipped: UI, accessibility, SEO, sessions, auth, scalability, caching (PRD records them as skipped; plain-text single-user tool). Security reduced to input validation, terminal-escape sanitizing on output, and no shell/eval.

Open conflicts in RFCS.md: conflict 1 (no lock) means two overlapping `add` runs can lose a task; the code follows it (no lock) and it is not RFC-003's to fix. Conflict 2 (assumed names/formats), 5 (Ctrl-C) were followed as written. Conflict 8 does not touch RFC-003. No new conflicts found. Predecessors RFC-001 and RFC-002 are Reviewed. The Implementation Notes record no deviations; I found none that matter.

### Step 0: run it

No build step (single Python file `td`). Test run:

```
$ python3 -m unittest discover tests
....................................................
Ran 52 tests in 0.901s

OK
```

Hand runs of `./td` with a temporary `TD_FILE`: `add buy milk` -> `1 [ ] buy milk`, exit 0; `add -- -x` -> `2 [ ] -x`; `add "  "` -> `td: task text is empty`, exit 2; `add $'a\nb'` -> exit 2; `done 01` marks task 1, silent; `done 1` again silent, file unchanged; `rm 007` -> `td: no task with id 007`, exit 1; after `rm 2`, `add z` gets id 3; `done " 1"` and `done ٣` -> `td: invalid id: ...`, exit 2; `add $'a\tb\x1b[31m'` prints `a b [31m` (tab and ESC replaced) while the file keeps the raw text; `add $'\xff'` -> `td: task text is not valid UTF-8`, exit 2; `done` with 5000 nines -> exit 1, `no task with id <as typed>`; `add` with no args exit 2; `done 1 2` exit 2. Every result matches the RFC. Only Python 3.13 was available; 3.10 and macOS are RFC-005's.

Regression check (mutation): I changed `td` temporarily, ran the suite, and restored it (`git status` clean afterwards).

| Mutation | Suite result |
|---|---|
| `done` saves even when already done | fails (caught) |
| `rm` also raises `next_id` to max+1 (id reuse) | fails (caught) |
| `strip()` removed | fails (caught) |
| newline check drops `\r` | fails (caught) |
| `\d` instead of `[0-9]` in the id check | passes (not caught) |
| `lstrip("0")` removed before the length check | passes (not caught) |

### Acceptance criteria and tests

All 13 criteria have a test in `tests/test_commands.py`, as TEST-STRATEGY.md RFC-003 plans (13 of 13). The mutations above show criteria 3, 4, 6, 8, 9 would fail on regression. Two guards are not pinned (see N1, N2).

### 1. RFC adherence: PASS
All 13 criteria are met in behavior. Handler contract, `ARGUMENTS`, single `save_store` after validation, the `done`-already-done no-write rule, the 4000-digit cut-off (`MAX_ID_DIGITS`), id echoed as typed, and nothing printed by `done`/`rm` all match. No extra features. Deviations: none recorded, none found. The plan was not confirmed by the user; the notes say so openly.

### 2. Rules compliance: PASS
NAME-2 (only three commands), DATA-4 (`next_id` untouched by `rm`), SAFE-6 (validation before save), PERF-1 (one load, one save), CLI-3 (idempotent `done`), OUT-7 (`td:` one-line errors) hold. Comments say why. Tests use `helpers.temp_env()` (TEST-8).

### 3. Security: PASS
Ids are validated with an ASCII-only regex before `int`, with a length cap that avoids Python's int-conversion limit. Text is checked for newlines and encodability before it is stored. Control characters are stored raw and replaced on output, so a stored escape sequence cannot reach the terminal. No shell, eval or path built from user input.

### 4. Performance: PASS
One load and one save per command; `done` of a done task skips the write. Linear scans are fine for a single-user list.

### 5. Maintainability: PASS
Small handlers, one shared `_find`, no dead code. Tests are one method per criterion with subtests-like loops, as planned.

### Findings

**Blocking issues:** none.

**Non-blocking:**
- N1. No test pins ASCII-only ids. Replacing `[0-9]` with `\d` passes the suite, and then `td done ٣` would mark task 3 (since `int("٣")` is 3), against the RFC ("ASCII digits only"). Suggest adding `"٣"` to the bad-id list in `test_c11_bad_id` (`tests/test_commands.py`).
- N2. No test pins that leading zeros are dropped before the length check. With the `lstrip("0")` removed, `td done 000...0099` (5000 zeros then a real id 99) reports "no task with id" instead of marking task 99; criterion 10's over-long case only uses an id that does not exist. Suggest a test where task 99 exists.
- N3. The error for an over-long id echoes the whole id as typed (a 5000-character stderr line). This is what the RFC asks ("the id as typed"); noted only because it is long.
- N4. The tests call `main` in-process, so the real `./td` entry point (shebang, `sys.exit`) is covered only by my hand runs and, later, RFC-005.

### Overall

**Overall risk: Low.** The implementation satisfies all 13 criteria, follows RULES.md, and my hand runs found no behavior the RFC does not cover. Two guards are not caught by tests (N1, N2), which is worth a small test addition but does not block. Merge-ready.

### FEATURES.md

FEATURES.md has no Status column, so nothing to update there.

## Round 2 -- 2026-11-15

**Overall verdict: FAIL on three blocking issues (one unaccepted High conflict, two tests that pass when the behavior they cover is broken). Overall risk: Medium. Status set: Changes requested.**

Re-review under the updated instructions. Round 1 Status was Reviewed and was accepted as the starting point. Reviewer context: fresh session, did not write the code. Commit reviewed: HEAD (`69940b0`). Since Round 1, `td` changed only by RFC-004's `cmd_clear` (`git diff 615bba5 HEAD -- td`); `tests/test_commands.py` is unchanged. The Implementation Notes' Files changed list (`td`, the RFC file, `RFCS.md`, `tests/test_commands.py`) matches commit `e3a3497`. `git status` was clean before and after my breaks (`td` restored from a saved copy).

Product type (PRD.md): CLI, unchanged. Applied: command and flag design, exit codes, stdout vs stderr, scripting, encoding, environment handling. Skips are PRD's own.

### Open conflicts (RFCS.md)

**Conflict 1 (High): PRD G2 "never lose tasks" against F17 / DEV-3 (no lock). It touches this RFC directly.** `td add` is the command PRD Open Question 9 names: two overlapping `td add` runs drop one task, and `done` and `rm` have the same read-modify-write race. I searched PRD.md, PRD-REVIEW.md, FEATURES.md and RFCS.md: the PRD itself records it as an unresolved assumption, and there is no written acceptance by the user. The code follows the RFC (no lock) correctly, but a review cannot certify code that breaks a PRD goal on the RFC's say-so. Round 1 called it "not RFC-003's to fix"; under the new rule that is blocking (B1), the same call Round 2 of RFC-001 made. Conflicts 2 and 5 followed as stated; 8 does not touch RFC-003. No new conflicts found. Predecessors: RFC-001 and RFC-002 are both Changes requested now (their own blocking issues); RFC-003's behavior is not affected by their findings.

### Step 0: run it

No build or typecheck exists (single Python file `td`, no third-party tools). Test run on Python 3.13.18:

```
$ python3 -m unittest discover tests
..................................................................
Ran 66 tests in 2.608s

OK
```

(66 = 52 at Round 1 plus RFC-004 and RFC-005 tests.) 13 of 13 criteria have a test in `tests/test_commands.py`, as TEST-STRATEGY.md plans.

Used as the PRD's user, with `TD_FILE` pointing at a temporary file: `add buy milk` -> `1 [ ] buy milk`; `add -- -x` -> `2 [ ] -x`; `done 01` silent, `list` shows `1 [x]`; `rm 007` -> `td: no task with id 007`, exit 1; `done ٣` -> `td: invalid id: ٣`, exit 2; `add "  "` -> `td: task text is empty`, exit 2; `done` with no id -> `td: the following arguments are required: id`, exit 2; a tab and ESC in text print as spaces, and the next `add` after `rm 2` got id 4 (ids never reused); `done` with 5001 nines -> exit 1, `no task with id` plus the whole id; on a corrupt file `add x` and `done abc` exit 1 with a `td:` line naming the path. All match the RFC. Goals G1/G2/G3 in practice: a crash-safe save is RFC-001's; the lock gap is B1. `--help` lists `done tasks` and `rm tasks` (already filed under RFC-002 follow-up F1).

### Deliberate breaks (each made in `td`, suite run, `td` restored)

| Break | Suite |
|---|---|
| `done` saves even when already done | caught (c8, c13) |
| `done` never sets `done` | caught (c7) |
| `rm` does not save | caught (c6, c9, c13) |
| `rm` also raises `next_id` to max+1 (id reuse) | caught (c6, c9) |
| `add` does not save | caught (c1, c2, c4) |
| `add` prints nothing | caught (c1) |
| `strip()` removed / strips only spaces | caught (c2, c3) |
| `\r` check dropped / `\n` check dropped | caught (c4) |
| newline check moved after the strip | caught (c4) |
| UTF-8 encode check removed | caught (c4) |
| empty-text check removed | caught (c3) |
| words joined with `""` instead of `" "` | caught (c1, c2) |
| `re.match` instead of `re.fullmatch` | caught (c11) |
| bad id raises exit 1 instead of 2 | caught (c11) |
| unknown id echoes the int, not the id as typed | caught (c10) |
| unknown id exits 2 | caught (c10) |
| id 0 mapped to 1 | caught (c10) |
| `nargs="*"` changed to `"+"` | caught (c12) |
| ASCII-only id check widened to accept Arabic-Indic digits (`[0-9٠-٩]+`) | **not caught** |
| the 4000-digit cut-off removed (`if False:`) | **not caught** |
| `lstrip("0")` removed before the length check | **not caught** |
| `MAX_ID_DIGITS` raised to 5000 | **not caught** |

The first `\d` attempt in my script was caught only by RFC-005's separator scan (it bans a backslash in `td`), which is luck, not coverage; the backslash-free form above passes the whole suite.

### 1. RFC adherence: NEEDS WORK
All 13 criteria are met in behavior and no extra features exist. Deviations: none recorded, none found. The gaps are in what the tests prove (B2, B3), not in the code's behavior today.

### 2. Rules compliance: PASS
NAME-2, DATA-4, SAFE-6, PERF-1, CLI-3, OUT-7 hold as in Round 1. TEST-1/TEST-3: the guards named in B2 and B3 are rule-relevant (TEST-3, "a test that cannot fail is not a test") and are what the new instructions make blocking.

### 3. Security: PASS
Ids are matched ASCII-only before `int`; the cut-off keeps `int` below Python's 4300-digit limit; control characters are sanitized on output; text is encodable before save. All unchanged. These guards are correct today but unprotected (B2, B3).

### 4. Performance: PASS
One load and one save per command; `done` of a done task skips the write.

### 5. Maintainability: NEEDS WORK
Code is small and clear. Tests: the two guards above have no failing test. The 4001-nines and 5000-zero cases in `test_c10_unknown_id` look as if they cover the cut-off but do not (an `int` of 4001 digits works; the real limit is 4300), so a reader trusts a guard nothing checks.

### Blocking issues

- **B1: open High conflict 1 (G2 against no lock) touches this RFC (`add`, `done`, `rm` all read-modify-write) and has no written user acceptance.** Needs the PRD owner: add a locking requirement (F17 becomes Must, new RFC) or reword G2 to "never lose tasks to a crash" and record that in PRD.md. No change to RFC-003's code clears it; once PRD.md is settled, a re-review citing the decision closes it.
- **B2: the over-long id guard is not tested.** The RFC fixes the cut-off at 4000 digits after dropping leading zeros and says such ids must report `no task with id <as typed>`. Removing the cut-off, or dropping `lstrip("0")`, or raising the limit passes all 66 tests; without the guard, `td done` with 4301 or more digits makes `int` raise `ValueError`, which `main` reports as `unexpected error` (exit 1, wrong message). Fix in `tests/test_commands.py`: add a `done` and `rm` case with 4301 nines (must exit 1 with `no task with id <as typed>`) and one with 5000 zeros followed by `99` where task 99 exists (must mark it).
- **B3: ASCII-only ids are not tested.** The RFC says ASCII digits only. Widening the regex to Unicode digits passes the suite, and then `td done ٣` would mark task 3 (`int("٣")` is 3). Fix: add `"٣"` (and a full-width `"１"`) to the bad-id list in `test_c11_bad_id` (exit 2, one `td:` line, file unchanged), for both `done` and `rm`.

### Improvement suggestions (non-blocking, added to RFCS.md Follow-ups)

- F1: the error for an over-long id echoes the whole id (a 5000-character stderr line). The RFC asks for the id as typed; consider truncating with an ellipsis if a later RFC revisits message wording (carried from Round 1 N3).
- Round 1 N4 (the real `./td` entry point is only covered by hand runs) is now covered by RFC-005 criterion 3 (installed-copy run); closed.

### Overall

**Overall risk: Medium.** The code satisfies all 13 criteria and my hand runs found nothing wrong. It cannot be marked Reviewed because the High G2 conflict that `add` embodies has no user acceptance, and because two RFC-stated guards (id length cut-off, ASCII-only ids) pass every deliberate break; both test additions are small.

### FEATURES.md

FEATURES.md has no Status column, so nothing to update there; F6, F8, F9 are not marked as built.

## Round 3 -- 2026-11-15

**Overall verdict: PASS with non-blocking findings. Overall risk: Low (Medium for overlapping runs until RFC-006 lands, see below). Status set: Reviewed.**

Re-review after the fix round (`8d4ebad /implement-rfc RFC-003 (fix round)`), judged against Round 2's three blockers. Reviewer context: fresh session, did not write the code. `td` is unchanged since the RFC-002 fix round (`1726a43`); the fix round touched only `tests/test_commands.py`, the RFC file and `RFCS.md`, which matches its Files changed list. `git status` was clean before and after my breaks (`td` restored from a saved copy, `cmp` identical).

Product type (PRD.md): CLI, unchanged. Skips are the PRD's own.

### Round 2 blockers

- **B1 (open High conflict 1, G2 against no lock): cleared, with a caveat I am recording rather than hiding.** RFCS.md now marks conflict 1 CLOSED by `changes/CHANGE-REQUEST-001.md`. That CR was accepted by the person running the example, not by the user in IDEA.md, and says so itself; the user has not seen it. The review rule blocks on a High conflict "that the user has not accepted in writing". My judgment: it does not block RFC-003, for three reasons. (1) The contradiction between artifacts is gone, because the higher artifact was changed: PRD.md now has NFR-10 and D-9, FEATURES F17 is a Must, RULES.md has SAFE-8. The code no longer follows a lower artifact against the PRD; the PRD asks for a lock and RFC-006 is where the lock is built. (2) The decision is written, dated, reasoned, and reversible: reversing D-9 retires RFC-006 and SAFE-8 and touches no RFC-003 code or criterion, so nothing certified here depends on which way the user decides. (3) The only human reachable in this non-interactive run is the one who accepted it; holding RFC-003 for the fictional IDEA.md author would block it forever, and RFC-006 depends on RFC-003 being Reviewed first. What this does not do: it does not make G2 true. Until RFC-006 is implemented, overlapping `add`, `done` and `rm` can still lose a write (NFR-10 unmet in the code). That is RFC-006's criterion, not an RFC-003 criterion, and the CR states RFC-003's criteria are unchanged. It stays visible as Follow-up RFC-001 (round 3, F7, F8). Had the CR been an open or rejected item, or had RFC-006 not existed, I would have kept this blocking.
- **B2 (over-long id guard untested): fixed.** Verified by breaking, below.
- **B3 (ASCII-only ids untested): fixed.** Verified by breaking, below.

Other open conflicts in RFCS.md: 2 and 5 followed as stated; 8 does not touch RFC-003. No new conflict found. Predecessors RFC-001 is Changes requested (its own round-3 findings; a different RFC's open item, not a behavior RFC-003 relies on being wrong) and RFC-002 is Reviewed. I note RFC-001's status as a risk, not a blocker: RFC-003's criteria exercise `load_store`, `save_store`, `add_task`, `find_task`, `remove_task` as they stand and pass.

### Step 0: run it

No build or typecheck exists (single Python file `td`, standard library only). Test run on Python 3.13:

```
$ python3 -m unittest discover tests
..........................................................................
Ran 74 tests in 3.583s

OK
```

13 of 13 criteria have a test in `tests/test_commands.py` (14 tests, one extra for the leading-zero guard), as TEST-STRATEGY.md RFC-003 plans.

Used as the PRD's user, with a temporary `TD_FILE`: `add buy milk` -> `1 [ ] buy milk`; `add -- -x` -> `2 [ ] -x`; `done 01` silent exit 0; `rm 007` -> `td: no task with id 007`, exit 1; `done ٣` -> `td: invalid id: ٣`, exit 2; after `rm 2`, `add z` gets id 3, `list` shows 1 and 3; `done` with no id -> exit 2; `--help` now gives each command a real description (RFC-002 F1 closed). All match the RFC.

### Deliberate breaks (each made in `td`, suite run, `td` restored)

| Break | Suite |
|---|---|
| id regex widened to Arabic-Indic digits (Round 2 B3, was not caught) | caught (2 failures) |
| `lstrip("0")` removed (Round 2 B2, was not caught) | caught (2) |
| `MAX_ID_DIGITS` 4000 to 5000 (was not caught) | caught (2) |
| `MAX_ID_DIGITS` 4000 to 3000 | caught (2) |
| 4000-digit cut-off removed (`if False:`) (was not caught) | caught (2) |
| `done` saves even when already done | caught (3) |
| `done` never sets `done` | caught (3) |
| `rm` does not save | caught (5) |
| `add` does not save | caught (6 failures, 2 errors) |
| `strip()` removed | caught (3) |
| words joined with `""` instead of `" "` | caught (3) |
| `\r` check dropped | caught (2) |
| unknown id echoes the int, not the id as typed | caught (2) |
| id `0` mapped to 1 | caught (2) |

All four Round 2 "not caught" breaks are now caught; the rest of Round 2's table was spot-checked, not rerun in full (its other rows were already caught and the tests they rely on are unchanged apart from additions).

### Dimensions

1. RFC adherence: **PASS.** All 13 criteria met; no extra features; the fix round recorded its deviations (none from the RFC text) honestly, including that B1 was not fixable in this RFC.
2. Rules compliance: **PASS.** NAME-2, DATA-4, SAFE-6, PERF-1, CLI-3, OUT-7, TEST-3 hold; the guards the RFC names now each have a test that fails when they are broken.
3. Security: **PASS.** ASCII-only ids and the length cut-off are now protected by tests; text is checked for newlines and encodability before storage; control characters are sanitized on output.
4. Performance: **PASS.** One load and one save per command; `done` of a done task skips the write.
5. Maintainability: **PASS.** Small handlers, one `_find`, no dead code. The old doubt that the 4001-nines test looked like cover but was not is resolved by the `9`*4301 and `9`*5000 cases and the real 4000-digit id.

### Blocking issues

None.

### Improvement suggestions (non-blocking)

- Carried: error for an over-long id echoes the whole id (Follow-up RFC-003 round 2, F1; already in RFCS.md).
- N5. The "hand test" of the fix round's claim that `test_c10_unknown_id` fails with the cut-off removed is confirmed; nothing further. No new follow-ups from this round beyond the one below.
- F2 (new). RFC-003's own Implementation Notes "Future" line ("A lock ... is still open") and B1 text will be stale once RFC-006 lands; reword then. Added to RFCS.md Follow-ups.

### Overall

**Overall risk: Low** for the code reviewed; **Medium** for the product as a whole until RFC-006 adds the lock, because `add`, `done` and `rm` can still lose a write under overlapping runs. The code satisfies all 13 criteria, follows RULES.md, and every deliberate break, including the four that slipped through in Round 2, now fails a test. Reviewed.

### FEATURES.md

FEATURES.md has no Status column, so nothing to update there.
