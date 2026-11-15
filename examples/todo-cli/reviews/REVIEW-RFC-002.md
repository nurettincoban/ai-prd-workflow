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
