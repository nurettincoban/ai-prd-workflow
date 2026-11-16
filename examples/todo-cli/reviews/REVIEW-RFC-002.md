# Review: RFC-002 CLI framework, output rules and `td list`

Reviewer context: fresh session, did not write the code. Commit reviewed: `841a25a /implement-rfc RFC-002`. Files changed per Implementation Notes: `td`, `tests/test_cli.py`, the RFC file, `RFCS.md`. The commit matches that list.

## Round 1 -- 2026-11-15

**Overall verdict: PASS with non-blocking findings. Overall risk: Low. Status set: Reviewed.**

Product type (PRD.md): CLI. Applied: command and flag design, exit codes, stdout/stderr separation, piping, encoding, environment handling. Skipped: UI, accessibility, SEO, sessions, auth, scalability, caching (PRD records them as skipped; plain-text single-user tool). Security checks reduced to input sanitizing on output and no shell/eval; there is no network, auth or database.

Open conflicts in RFCS.md: conflict 5 (Ctrl-C exits 1) touches this RFC and the code follows it; conflict 8 (the Features line omits F2 and F4) was followed as stated (tests follow the criteria). Conflict 1 (no lock) is not touched here. Predecessor RFC-001 is Reviewed. No new conflicts found.

### Step 0: run it

No build step (single Python file). Test run:

```
$ python3 -m unittest discover tests
.......................................
----------------------------------------------------------------------
Ran 39 tests in 0.581s

OK
```

Python 3.13. Python 3.10 and macOS were not run (STACK-2, F15 unverified here; RFC-005). `git status` was clean after the run.

I also exercised `./td` by hand against a temp `TD_FILE`:
- `td` and `td list` with ids stored 10, 2, 1: `1 [ ] a b c`, `2 [x] caf\xc3\xa9`, `10 [ ] x y[31m tab` (ESC, tab, U+2028, U+0085 and DEL each became one space; no ESC byte on stdout). Bare `td` on a missing file: silent, exit 0, file not created.
- `frob`, `li`, `--he`, `5`, `list x`, `list --bogus`, a newline argument: each exit 2, one `td:` line, empty stdout. `-h`, `--help`, `list -h`: exit 0 on stdout. `-- list` works.
- Corrupt file: bare `td` exit 1, one `td:` line with the path; `td list x` on the same file exits 2. A directory as `TD_FILE` exits 1 with the path. 100000 nested `[` exits 1 as `td: unexpected error: RecursionError: ...` (RFC-001's N1, still open there).
- `td list | head -1`: exit codes 0 0, no stderr. `td list >&-`: `td: unexpected error: AttributeError: ...`, exit 1 (as the RFC specifies for output pending on a closed stdout). `td list >/dev/full`: exit 1, one `td:` line.

Mutation checks (I changed `td`, ran the suite, restored it): removing the `sorted` call, `_one_line`'s replacement, `reconfigure(errors="replace")`, the `COMMANDS[args.command or "list"]` dispatch or the usage exit code 2 each makes tests fail. Two mutations survive, see N1 and N2.

Criterion coverage (does a test fail if the behavior regresses?):

| Crit | Test | Would fail on regression? |
|---|---|---|
| 1 | `test_c1_shebang_exec_int_exit` (first line, `S_IXUSR`, int return, `sys.exit` scan limited to the `__main__` guard) | yes |
| 2 | `test_c2_list_output` (exact stdout, stderr, code) | yes |
| 3 | `test_c3_sorted` (mutation confirmed) | yes |
| 4 | `test_c4_empty_creates_nothing` | yes |
| 5 | `test_c5_bare_equals_list`, both stores | yes |
| 6 | `test_c6_usage_errors`, 7 subtests plus `--help` | yes (not `--he`, see N2) |
| 7 | `test_c7_corrupt`, 4 corruptions x 2 invocations, bytes unchanged | yes |
| 8 | `test_c8_load_failures` | yes |
| 9 | `test_c9_error_path` | yes |
| 10 | `test_c10_sanitized` (mutation confirmed). U+2028 is in the test list only if the literal survived; the `a b` entry is a literal U+2028 in the file, which I confirmed by the `cat -A` run above | yes |
| 11 | `test_c11_broken_pipe` (real subprocess, 20,000 tasks) | partly, see N1 |
| 12 | `test_c12_ascii_stdout` (mutation confirmed) | yes |
| 13 | `test_c13_static` | yes |
| 14 | `test_c14_single_load` | yes |

All 14 criteria have a test, and all planned TEST-STRATEGY.md rows for RFC-002 exist (the strategy marks them "proposed"; they are now implemented). No planned test is missing.

### 1. RFC adherence -- PASS
- Every criterion is met (above). The handler contract, `COMMANDS` and `ARGUMENTS` read at parser-build time, the order of events in `main` (parse, then `resolve_path`, then `load_store`, then handler, then write) and the `td:` prefix on argparse errors match the RFC.
- Implementation Notes record no deviations; I found none. Wording of argparse messages is the implementer's choice per the RFC. The shared `_one_line` helper is a recorded, sensible choice.
- No extra features. No lock added.

### 2. Rules compliance -- PASS
ARCH-1 (one file, shebang, executable), ARCH-2 (`main` returns an int, one `sys.exit` in the guard), NAME-2 (`allow_abbrev=False` on parser and subparsers; `td --he` exits 2, verified by hand), CLI-4, CLI-5, CLI-7 and PERF-1 (one `resolve_path`, one `load_store`), OUT-1 (handlers return lines; nothing written to stdout on failure), OUT-3 (no `isatty`, no ANSI), OUT-5, OUT-6, OUT-7, SEC-2 (no subprocess/eval/shell), DEV-1 (no stubs), TEST-1/5/6/8.

### 3. Security -- PASS
Terminal-escape injection through stored text or error messages is closed: every `Cc`, `Zl` and `Zp` character is replaced in `format_task` and in every message, including argparse errors. No shell, eval or pickle. Messages contain only the user's own path and arguments.

### 4. Performance -- PASS
One read per run, sorting only (n log n), lines joined and written once. A 20,000-task listing finishes well inside the 1 second budget in the pipe test.

### 5. Maintainability -- PASS
Short functions, comments give the why (devnull redirect, `errors="replace"`), tests map to criteria by comment and name. No unused imports (`unicodedata`, `uuid`, `argparse` all used).

### Blocking issues

None.

### Non-blocking issues

- **N1: criterion 11 does not guard the `os.dup2` to devnull.** With that line replaced by `pass`, the whole suite still passes, and by hand `td list | head -1` still exits 0 with empty stderr on Python 3.13. The code follows OUT-5 and the Python documentation, so the code is right; the test cannot tell whether the line is there, so a later "simplification" could remove it and only a different Python version would show it. Suggestion: also assert that the second flush at exit stays quiet on the oldest Python RFC-005 runs, or test `_write_lines` directly with a stdout stub that raises `BrokenPipeError` and check that `dup2` was called.
- **N2: `allow_abbrev=False` is not tested.** Removing it leaves the suite green because the subcommand names are never abbreviated by argparse and no test passes `td --he`. By hand `td --he` correctly exits 2 today. Suggestion: add `["--he"]` to the cases of criterion 6 (the RFC's technical approach names it; criterion 6 lists only `li`).
- **N3: closed stderr turns a usage error into exit 1.** `td frob 2>&-` exits 1 with no message, because `_Parser.error` writes to `sys.stderr` (None) and the `AttributeError` is caught by the outer `except Exception`. Contrived (nobody closes stderr on purpose), and the RFC does not cover it; mention only. Closing stdout with output pending works as the RFC specifies.
- **N4: `-h` to a closed pipe is reported as an unexpected error.** The help text is printed inside `parse_args`, outside the `_write_lines` guard, so `td --help | true` could print `td: unexpected error: BrokenPipeError` on a slow reader; I could not reproduce it (exit 0 0). Low value.
- **N5: RFC-001's N1 (`RecursionError`) is still open and shows here** as `td: unexpected error: RecursionError: ...` with exit 1. It is exit 1 with one line and no traceback, so F11 holds; the path is not named, as RFC-001's review already noted.
- **N6: unverified platforms.** Python 3.10 floor, macOS and Windows are not run; Implementation Notes say so. RFC-005's job.
- **N7: the Plan in Implementation Notes was never confirmed by a user** (nobody was available). Its assumptions are the RFC's own and unchanged.

### Summary

The implementation satisfies all 14 acceptance criteria, follows RULES.md and records its (absent) deviations, and my hand runs found only edge cases the RFC does not cover. Two guards (`dup2`, `allow_abbrev`) are not caught by any test, which is worth a small test addition but does not block. Merge-ready.

### FEATURES.md

FEATURES.md has no Status column, so nothing to update there.

## Round 2 -- 2026-11-15

**Overall verdict: NEEDS WORK. Overall risk: Low (the code is right; three guards are untested). Status set: Changes requested.**

Re-review under the updated instructions (blocking now includes "a test that still passes when the behavior it covers is broken"). Round 1 Status was Reviewed; that was accepted as the starting point. Reviewer context: fresh session, did not write the code. Code is unchanged since Round 1 (`git status` clean; `td` restored byte for byte after every break, checked with `cmp`).

Product type (PRD.md): CLI. Same applied and skipped checks as Round 1; nothing added to the PRD's skip list.

Open conflicts in RFCS.md: conflict 1 (High, G2 against no lock) is about concurrent writers. RFC-002 writes nothing (`list` is read-only, `save_store` is called zero times, criterion 14), so I do not count it as touching this RFC; it stays open under RFC-001's review. Conflicts 5 and 8 were followed as in Round 1. No new conflicts. Predecessor RFC-001 is now Changes requested (its B2, nested JSON, shows through `td list`, see "Dependency" below).

### Step 0: run it

No build step (single Python file).

```
$ python3 -m unittest discover tests
..................................................................
Ran 66 tests in 2.860s
OK
```

Python 3.13.18; 66 tests now because RFC-003 to RFC-005 added theirs (the 14 RFC-002 tests are `tests/test_cli.py`). Python 3.10 and macOS were not run by me.

Breaks (I changed `td`, ran the suite, restored it):

| Break | Caught? |
|---|---|
| `sorted(...)` removed from `cmd_list` | yes |
| `_one_line` dropped from `_report` | yes |
| `Zl`/`Zp` dropped from the replaced categories | yes |
| usage exit code 2 changed to 1 | yes |
| `reconfigure(errors="replace")` removed | yes |
| `unexpected error: ` prefix changed | yes |
| bare `td` dispatches another command | yes |
| `[x]` marker changed | yes |
| `load_store` called twice / `resolve_path` called twice | yes |
| `os.dup2(devnull, ...)` replaced by `pass` | **no** |
| `except BrokenPipeError` replaced by another exception (pipe no longer handled) | **no** |
| `allow_abbrev=False` removed from the parser | **no** |
| `_one_line` removed from `_Parser.error` | **no** |
| `KeyboardInterrupt` exit code 1 changed to 0 | **no** |
| `sys.stdout.flush()` removed from `_write_lines` | no (equivalent here: a small output flushes at exit and still exits 0 on 3.13) |
| `--help` exit code expression rewritten | no (equivalent mutant) |

Why the survivors survive:

- **Pipe handling (criterion 11).** With BrokenPipeError no longer handled, `td list` over 20,000 tasks piped into `head -1` still exits 0 here, because on this kernel the 1.4 MB write completes before the reader closes, so no `BrokenPipeError` is ever raised and the test cannot tell. When the reader has closed before `td` writes (`Popen(... stdout=PIPE)`, close at once, wait), the same mutant exits 1 with `td: unexpected error: BrokenPipeError: [Errno 32] Broken pipe`, and the real code exits 0 with empty stderr. The test's size argument ("cannot fit in the pipe buffer") does not hold when the pipe buffer is large or the reader is slow to close. The test is timing-dependent and, as written, guards nothing on this machine.
- **`allow_abbrev`.** Without it `td --he` prints help and exits 0, but NAME-2 and the RFC say it is an error (exit 2). Criterion 6 lists `li`, which argparse never abbreviates for subcommands, so the case does not exercise the setting.
- **Sanitizing in `_Parser.error`.** Criterion 6's `a\nb` case goes through argparse's "invalid choice" message, which prints `repr()` and escapes the newline, so the sanitizer is never needed. `td list $'a\nb'` ("unrecognized arguments: a\nb") produces two stderr lines when the sanitizer is removed (checked with `cat -A`), and no test runs it.
- **`KeyboardInterrupt`.** The RFC pins `td: interrupted` and exit 1 (assumption, RFCS.md conflict 5); no criterion or test covers it.

Criterion coverage: criteria 1 to 5, 7 to 10, 12 to 14 each fail when their behavior regresses (Round 1 table, re-confirmed by the breaks above). Criterion 6 and 11 do not, as above.

Used as the user: `td add`, `td done 1`, `td`, `td --help`, `td --he`, `td list $'a\nb'`. All behave as specified; `td list | head -1` exits 0 0. The help text lists `done      done tasks` and `rm        rm tasks`, which repeat the command name instead of saying what it does (F1 below). Goals G1 and G3 are served; G2's concurrent-write gap is not this RFC's.

Dependency: `td list` on a data file of 200000 `[` prints `td: unexpected error: RecursionError: ...` with no path, which breaks SAFE-3 and TEST-3. The fault is in `load_store` (RFC-001's B2) and its fix and test belong there; I do not file it a second time here, but RFC-002's criteria 7 and 8 would be incomplete until RFC-001 is re-reviewed, so run that fix first.

### 1. RFC adherence -- NEEDS WORK
All 14 criteria are met by the code. Criteria 6 and 11 are met but not guarded (B1 to B3). No unrecorded deviation, no extra feature.

### 2. Rules compliance -- PASS
Unchanged from Round 1: ARCH-1/2, NAME-2 (the code is right, the test is the gap), CLI-4/5/7, PERF-1, OUT-1/3/5/6/7, SEC-2, DEV-1. TEST-5 is met in letter and, on this machine, not in effect (B1).

### 3. Security -- PASS
Terminal-escape injection is closed for stored text and error messages; no shell, eval or pickle.

### 4. Performance -- PASS
One read per run, one sort, one write. 20,000 tasks list well inside the 1 second budget.

### 5. Maintainability -- NEEDS WORK
Code is short and commented. The three untested guards above are the work item.

### Blocking issues

- **B1: criterion 11 passes when pipe handling is removed (OUT-5, TEST-5).** Make the reader close first and deterministically: start `td list` with `stdout=PIPE`, close `proc.stdout` without reading, then wait; assert exit 0 and empty stderr (keep the large data). Add a direct test of `_write_lines` with a stdout stub whose `write` raises `BrokenPipeError`, asserting `os.dup2` was called with the devnull descriptor, so the `dup2` line is guarded on any Python version. Re-run the two breaks above and confirm each fails.
- **B2: `allow_abbrev=False` is untested (NAME-2).** Add `["--he"]` (and `["--hel"]`) to criterion 6's cases, and confirm removing the setting from the parser fails the suite. A subparser case (`td list --he`) would guard the subparser setting too.
- **B3: sanitizing of argparse errors is untested (OUT-7, criterion 6's newline case).** Add `["list", "a\nb"]` to criterion 6's cases; it must give exactly one stderr line, and removing `_one_line` from `_Parser.error` must fail it.

No code change is needed for any of the three; each is a test addition.

### Improvement suggestions (non-blocking, added to RFCS.md Follow-ups)

- F1: `--help` lists `done tasks` and `rm tasks`; give each command a help text that says what it does (for example "mark a task done"). Wording only, and RFC-003's to fix.
- F2: add a test for `KeyboardInterrupt` (patch a handler to raise it; expect exit 1 and `td: interrupted`). Not in the RFC's criteria, but the RFC pins the behavior.
- F3: `td frob 2>&-` exits 1 with no message (Round 1 N3); `td --help` to a closed pipe is reported as an unexpected error on a slow reader (Round 1 N4). Both are contrived; fix only if a later RFC touches output setup.
- Carried from Round 1: Python 3.10 and macOS runs are RFC-005's; the Plan was never user-confirmed (nobody was available).

### Summary

The implementation satisfies all 14 criteria and I found no defect in `td` itself. Under the stricter rule, though, three guards the RFC and RULES.md rely on (pipe handling, no abbreviations, one-line argparse errors) can be removed without any test failing, and the pipe test cannot fail at all on this machine. These are test-only fixes; once made, the RFC is Reviewed.

### FEATURES.md

FEATURES.md has no Status column, so nothing to update there.

## Round 3 -- 2026-11-15

**Overall verdict: PASS. Overall risk: Low. Status set: Reviewed.**

Re-review after the fix round (`1726a43 /implement-rfc RFC-002 (fix round)`). Judged against Round 2's B1 to B3. Reviewer context: fresh session, did not write the code. `td` was restored byte for byte after every break (`cmp` against a saved copy; `git status` clean).

Product type (PRD.md): CLI. Same applied and skipped checks as Rounds 1 and 2; nothing added to the PRD's skip list.

### Open conflicts

- **Conflict 1 (High, G2 against no lock), now marked CLOSED by CR-001.** The CR was accepted by the person running the example, not by the user in IDEA.md. My judgement: it does not block this RFC, for two reasons. (a) It does not touch RFC-002's behavior: `list` writes nothing, takes no lock and calls `save_store` zero times (criterion 14); RFC-006 only adds a step in `main` for the mutating commands. (b) The closure follows the order of authority (it resolves the conflict toward PRD goal G2 and amends PRD.md, FEATURES.md and RULES.md consistently), so the code is not certified against a document that contradicts the PRD. What is still unconfirmed is whether the user wants the lock; that is already a follow-up (RFC-001 round 3, F8), so I do not file it again. Had RFC-002 itself written data, I would have treated an acceptance by someone other than the user as not enough and blocked.
- Conflicts 5 and 8: followed as before. No new conflicts.
- Predecessor RFC-001: Status is still Changes requested in RFCS.md (its own review rounds). The Round 2 dependency, `RecursionError` on deeply nested JSON, is fixed: a file of 200000 `[` now gives `td: <path>: invalid JSON: nesting too deep`, exit 1, path named.

### Step 0: run it

No build step (single Python file).

```
$ python3 -m unittest discover tests
..........................................................................
Ran 74 tests in 3.4s
OK
```

Python 3.13; 3.10 and macOS not run (RFC-005's job).

### What I broke on purpose

| Break | Caught? |
|---|---|
| `os.dup2(...)` replaced by `pass` (B1) | yes (2 failures) |
| `except BrokenPipeError` replaced by another exception (B1) | yes (2 failures, 1 error) |
| `allow_abbrev=False` removed from the parser (B2) | yes |
| `allow_abbrev=False` removed from the subparsers (B2) | yes |
| `_one_line` removed from `_Parser.error` (B3) | yes |
| `KeyboardInterrupt` exit code 1 changed to 0 (F2) | yes |
| `td: interrupted` text changed | yes |
| `list` help text changed (F1) | yes |
| `sorted` removed | yes (19 failures) |
| unexpected-error exit code 1 changed to 2 | yes |
| `TdError` exit code ignored (always 1) | yes |
| `sys.stdout.flush()` removed from `_write_lines` | no, equivalent: I ran it by hand with a small listing and the reader closed first, 3 times, exit 0 and empty stderr, because the `dup2` and exit-time flush stay quiet on 3.13 |

All three Round 2 blockers are fixed by tests that fail when the guarded line is broken, including the pipe test, which no longer depends on timing (the reader closes first, and a stub raises `BrokenPipeError` straight into `_write_lines`).

### Used as the user

`td add`, `td`, `td list`, `td done 1`, `td done 99` (`td: no task with id 99`, exit 1), `td --help` (each command now has a sentence saying what it does), `td --he` (exit 2, one `td:` line), `td list $'a\nb'` (one line, `a b`, exit 2), corrupt and deeply nested files (exit 1, one line, path named). G1, G3 and G4 are served; G2's overlapping-run gap is RFC-006's.

### 1. RFC adherence -- PASS
All 14 criteria met and each has a test that fails on regression (criteria 6 and 11 now do). The fix round's one `td` change (the `HELP` dict) is recorded as Deviation 1; judged: reasonable, wording only, no criterion pins the help text, and it is tested.

### 2. Rules compliance -- PASS
ARCH-1/2, NAME-2, CLI-4/5/7, PERF-1, OUT-1/3/5/6/7, SEC-2, DEV-1, TEST-1/5/6/8. TEST-5 is now met in effect, not only in letter.

### 3. Security -- PASS
Control characters are replaced in task text and in every message, argparse errors included (now tested). No shell, eval or pickle.

### 4. Performance -- PASS
One read, one sort, one write.

### 5. Maintainability -- PASS
Short, commented, tests map to criteria. No dead code found.

### Blocking issues

None.

### Non-blocking (added to RFCS.md Follow-ups)

- F4: RFC-002's Implementation Notes (Plan, "no lock") will be stale once RFC-006 lands; reword then.
- Still open from Round 2: F3 (closed stderr, `--help` into a closed pipe), contrived. Python 3.10 and macOS runs are RFC-005's. The plan was never user-confirmed.

### Summary

The fix round did what Round 2 asked: three test additions that fail when pipe handling, abbreviation blocking or argparse error sanitizing is removed, plus the two follow-ups. The code was right and still is. No blocking issue; Reviewed.

### FEATURES.md

No Status column, so nothing to update.

## Round 4 -- 2026-11-16

**Overall verdict**: NEEDS WORK

**Overall Risk Level**: Medium (no task is lost; Ctrl-C can still print a traceback, and a closed stdout makes a saved task look failed).

Status set: Changes requested.

Re-review after `2494db3 /implement-rfc RFC-002 (fix round 2)`, which answered the blocking follow-up from `changes/BUG-REPORT-001.md` item 5 (early Ctrl-C prints a traceback). Judged against that follow-up, against Rounds 1 to 3, and against the open conflicts that now touch this RFC. Reviewer context: fresh session, did not write the code. `td` was restored byte for byte after each break (`cmp` against a saved copy).

Product type (PRD.md): CLI, Small. Same checks as earlier rounds; nothing added to the PRD's skip list.

### Open conflicts and pending changes: what blocks this RFC

- **Conflict 12 (RFC-002 against SAFE-6 and F11 for `add`, `done`, `rm`): blocking for RFC-002.** SAFE-6 ("a failed command never modifies the data file") is a rule and outranks the RFC; RFC-002 Open Question 3 and its step order (save, then print) make the code break it. I reproduced it: `TD_FILE=<new> td add x >&-` prints `td: unexpected error: AttributeError: 'NoneType' object has no attribute 'write'`, exits 1, and `td list` then shows `1 [ ] x`. A script that retries on exit 1 adds the task twice. The code follows the RFC exactly, so this is not a coding slip, but nobody has accepted it in writing and CHANGE-REQUEST-002 Change 3 is still **Decision: pending**. The conflict touches RFC-002 (the RFC states the behavior and owns the output path in `main`), so the review cannot certify the code against a rule it breaks. It stays blocking until the user decides Change 3, or accepts the contradiction in writing. The `list` half (closed stdout exits 1) is unaffected: `list` saves nothing, and that behavior matches SAFE-6.
- **Conflict 11 (Ctrl-C before the first line of `td` runs): not blocking, as far as it goes.** The interpreter's own start-up cannot be caught by a one-file program, and the fix round recorded that for the user instead of weakening OUT-7, which is what the follow-up asked for. But see B1: not all of the remaining tracebacks fall in that window.
- **Conflict 1 (lock) is closed; conflicts 2 to 10: unchanged, none blocks.** Conflict 8 (Features line) and 5 (exit 1 for Ctrl-C) followed as before.
- **CHANGE-REQUEST-002 Changes 1, 2 and 4 (pending): not blocking.** They change what the product does (`add -h`, file mode, help text naming the data file). The RFCs and RULES.md say what the code does today, no higher artifact is contradicted, and nobody accepted them, so the code is judged against the RFC as written. Change 2 touches RFC-001 and Change 1 RFC-003; Change 4 would touch RFC-002's help text and is a Could have. Change 3 is the exception, above.

### Step 0: run it

No build step (single Python file).

```
$ python3 -m unittest discover tests
..........................................s.............................................
Ran 88 tests in 18.796s
OK (skipped=1)
```

Python 3.13 on Linux; 3.10 and macOS not run (Release checklist item 1).

### What I broke on purpose

| Break | Caught? |
|---|---|
| SIGINT handler not installed | yes (`test_c16_interrupt_during_imports`, and the nested run) |
| `os._exit(1)` changed to `os._exit(0)` in the handler | yes (2 failures) |
| `KeyboardInterrupt` path returns 0 instead of 1 | yes (`test_c15_keyboard_interrupt`) |
| `sorted` removed from `cmd_list` | yes (many failures) |
| `_write_lines(lines)` removed from `main` (list prints nothing) | yes (many failures) |
| Run the follow-up's own reproduction (60 Ctrl-Cs at 20 ms) on the shipped code | **no test does this**: 29 of 60 runs print a traceback while the suite is green (see B1) |

The tests that exist do catch the breaks I made. What no test covers is the property the follow-up is about.

### Used as the user

`td`, `td list`, `td add`, `td --help` (fine), closed stdout on `add` and on `list` (see B2), and the Ctrl-C loop from RFCS.md.

### 1. RFC adherence -- NEEDS WORK
Criteria 1 to 14 hold as in Round 3. The blocking follow-up, "Ctrl-C in the first 5 to 40 ms prints a traceback", is not fixed (B1). The fix round's own notes say "0 of 60 after"; on this machine the same command gives 29 of 60.

### 2. Rules compliance -- NEEDS WORK
OUT-7 (no traceback reaches the user) is broken by B1; SAFE-6 is broken by B2 (through the RFC's own text). Others as in Round 3.

### 3. Security -- PASS
No change since Round 3. Control characters are still replaced in text and messages.

### 4. Performance -- PASS
One read, one sort, one write. The handler adds nothing at run time.

### 5. Maintainability -- PASS
The `_STARTED` flag and handler are small and commented. Tests map to criteria, but see B1 on what they leave out.

### Blocking issues

**B1. Early Ctrl-C still prints a traceback; the blocking follow-up (BUG-REPORT-001 item 5) is not met, and part of the window is td's own.** Reproduce with the follow-up's loop: `for i in $(seq 60); do TD_FILE=$(mktemp -u) python3 td list 2>err & sleep 0.02; kill -INT $!; wait $!; grep -l Traceback err; done`. I got 29 of 60 tracebacks. I then sent the signal at 8 to 48 ms in steps of 2 ms (12 runs each) and read each traceback. Most come from Python's own start-up (`site`, `os`, `_collections_abc`; or `td` line 0, before any of `td` runs): that part is Conflict 11 and is not blocking. But about 40 of the 72 tracebacks name `td` line 4, which is `import signal`. They run through `signal.py`, `enum`, `functools` and `collections`, so the handler is installed only after `signal` has finished importing, which is slow enough to be hit often. That window is `td`'s to close: the handler can be installed through `_signal` (a built-in module with no imports) or `signal` can be imported lazily after a cheaper first handler is in place. The follow-up said that only what `td` cannot catch should be recorded for the user; here a catchable part was not caught, and the Implementation Notes' "0 of 60 after" does not hold. The new tests do not see it: `test_c16_interrupt_during_imports` sends SIGINT at a fixed point after the handler exists, so it passes whatever happens earlier. Fix: install the handler with nothing heavy imported first (the reproduction should drop to the start-up window only), add a test that raises the interrupt during the import of `signal` itself (stand-in module on `PYTHONPATH`, as the existing test does for `argparse`), and correct the "0 of 60" claim.

**B2. Conflict 12: a closed stdout makes `add`, `done`, `rm` save and then exit 1 (SAFE-6, F11).** Details above. Fix needs the user's decision on CHANGE-REQUEST-002 Change 3 (recommended there: exit 0 after a successful save, best-effort `td:` line), then RFC-002 step 6, Open Question 3 and a criterion, with RFC-003 reviewed again. Not fixable by the implementer alone.

### Non-blocking (added to RFCS.md Follow-ups)

- F5: `test_c16_interrupt_during_imports` and its siblings do not run the real timing loop; once B1 is fixed, consider one test that sends SIGINT at several delays and accepts only `td: interrupted` or silence from the start-up window. Folded into B1's fix; listed so it is not lost.
- Still open from earlier rounds: F3 (closed stderr, `--help` into a closed pipe).
- Pending (Changes 1, 2, 4) and Conflict 11 wait for the user; RFC-002's reviewer did not touch them.

### Summary

The fix round made `td` catch an interrupt during its imports after line 23, and the tests for that hold up when broken. But the handler is installed too late: `import signal` runs first and is slow, so about half of the early interrupts still print a traceback, which is what the blocking follow-up asked to stop. Separately, the unresolved contradiction between RFC-002 and SAFE-6 (Conflict 12, Change 3 pending) means the code is certified against a rule it breaks. RFC-002 is Changes requested.

### FEATURES.md

No Status column, so nothing to update.
