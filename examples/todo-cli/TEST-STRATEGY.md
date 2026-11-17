# TEST-STRATEGY: td, a tiny command-line to-do list

Product type: CLI (PRD.md Product Type). Applied checks: command and flag design, exit codes, stdout vs stderr, piping, environment handling, cross-platform paths, install. Skipped, as PRD.md records: UI design, accessibility, SEO, sessions, scalability, regulatory. Because of that there is no UI, browser, load or auth test anywhere below. Level names used: unit (calls library functions or `main` in-process), integration (real subprocess or real files), security and performance (static scan or timing), and the CLI-specific "static scan" (an `ast` check of the shipped file).

Tests are planned before the code exists; `/implement-rfc` writes them with each RFC. Framework: `unittest` only (RULES.md STACK-4, TEST-8). RULES.md TEST-9 sets no coverage percentage, so none is set here; coverage is measured by the criteria below.

## Baseline (STEP 0)

Run in the project folder on 2026-11-15 with `python3 -m unittest discover` (Python 3.13.18):

```
----------------------------------------------------------------------
Ran 0 tests in 0.000s

NO TESTS RAN
```

No `td` file, no `tests/` folder and no test of any kind exist yet. Existing tests: **0**. Passing: 0. Failing: 0. Every row below is therefore **proposed**; the Exists? column says so. The Python 3.10 floor has never been run (RULES.md STACK says unverified).

Shared test infrastructure, proposed in RFC-001 and used by every section: `tests/helpers.py` with `load_td()` and `temp_env()`; every test sets `TD_FILE` inside a temp directory and never touches `~/.td.json` (TEST-8).

## RFC-001: Storage core (data file, schema, crash-safe save)

Test file: `tests/test_storage.py`; fixture `tests/fixtures/v1.json`.

| Criterion | Test | Level | Exists? | Priority |
|---|---|---|---|---|
| 1 | `test_storage.py`: five env cases (unset with `HOME` temp, absolute, empty, `~/z.json`, `rel.json`); fails if any returns another path or a cached value (call twice with the env changed in between) | unit | proposed | Must (F1) |
| 2 | `ast` parse of `td`; fails if `TD_FILE` or `.td.json` occurs in any string constant, docstrings included, beyond the two definitions | unit (static scan) | proposed | Must (F1; no feature of its own, see Open Questions) |
| 3 | Missing parent, parent that is a regular file, data path that is a directory, for both `load_store` and `save_store`; fails if no `TdError`, exit code not 1, message lacks `str(path)`, or the directory got created | unit | proposed | Must (F1) |
| 4 | `load_store` on a missing file in an existing temp dir; fails unless it returns the empty store and the directory listing is unchanged | unit | proposed | Must (F2) |
| 5 | Round trip with `naïve café` and a text with `\n`; parse the raw file and assert exact keys; umask 022 gives mode 0644 and umask 077 gives 0600 (`skipUnless posix`) | unit | proposed | Must (F3, F5) |
| 6 | One subtest per listed bad input (19 cases); fails if no `TdError`, exit code not 1, message does not start with `str(path)`, quoted key missing for structure cases (`'next_id'`, `'tasks'`, `'done'`, `'id'`), `JSONDecodeError` text missing for invalid JSON, or bytes changed | unit | proposed | Must (F4) |
| 7 | Load `tests/fixtures/v1.json` (version 1, next_id 5, tasks 1 done "first", 3 open "naïve café", 4 done "x") and compare to the literal dict; then `add_task` must return id 5 | unit | proposed | Must (F5) |
| 8 | Remove-then-add (id 3, next_id 4, also after save and load), no-removal add (id 4), remove all then add returns prior `next_id`, `find_task`/`remove_task` on missing id (message `no task with id <n>`), `clear_done` count and `next_id` unchanged | unit | proposed | Must (F5) |
| 9 | Subprocess child with `os.fsync`/`os.replace` wrappers calling `os._exit(9)` at three points (before temp fsync, before replace, after replace); directory fsync told from temp fsync by `stat.S_ISDIR(os.fstat(fd).st_mode)`; each point run with and without a previous file; fails if `load_store` raises or returns the wrong store | integration | proposed | Must (F3) |
| 9 | Same three points as injected `OSError` in-process, plus an injected non-`OSError` that must propagate unchanged and leave the same files | unit | proposed | Must (F3) |
| 10 | Failed save (exception before replace): directory listing identical before and after; a pre-placed stray file survives a later load and save | unit | proposed | Must (F3) |
| 11 | `TD_FILE` as absolute symlink, relative symlink and chain of two; after save the link is still a link and its target holds the new store | integration | proposed | Must (F1) |
| 12 | Wrap `os.fsync` and `os.replace` to record order (temp fsync, replace, dir fsync); directory fsync raising `OSError` and an `os.open` wrapper failing for the directory both still succeed; another exception propagates | unit | proposed | Must (F15) |
| 13 | `save_store` with `next_id` as string and with duplicate ids; fails if no `TdError`, file bytes change, or a temp file appears | unit | proposed | Must (F4) |
| 14 | `TdError` and `UsageError` exit codes and `str` values | unit | proposed | Must (F11 via RFC-002; see Open Questions) |
| 15 | `temp_env()` restores `HOME` and `TD_FILE` including the unset state; `unittest discover tests` runs under the standard library | unit | proposed | Must (F1; STACK-1, STACK-4) |

Notes: no mocks of external services (there are none). Fixtures are written by each test into the temp dir; corrupt files are written byte-exact so "unchanged" can be compared. Criterion 9's child script is a small file or `-c` string that loads `td` by path. Prerequisites from earlier RFCs: none.

## RFC-002: CLI framework, output rules and `td list`

Test file: `tests/test_cli.py` (in-process via `main` with `redirect_stdout` and `redirect_stderr`; real subprocess for rows marked integration). Prerequisite: RFC-001 interfaces and `helpers`.

| Criterion | Test | Level | Exists? | Priority |
|---|---|---|---|---|
| 1 | Read first line of `td`, check `os.access(X_OK)`, `main(["list"])` is an `int`, `ast` finds `sys.exit` only in the `__main__` guard | unit (static scan) | proposed | Must (F11) |
| 2 | Three-task fixture (1 open "buy milk", 2 done "write notes", 10 open "x"); stdout exactly `1 [ ] buy milk\n2 [x] write notes\n10 [ ] x\n`, empty stderr, exit 0 | unit | proposed | Must (F7) |
| 3 | File stores ids 3, 1, 2 with a done task; output in id order including done | unit | proposed | Must (F7) |
| 4 | No data file, then empty `tasks`; empty stdout, exit 0, file not created | unit | proposed | Must (F7; the criterion also cites F2, not on this RFC's Features line) |
| 5 | Bare `main([])` against `main(["list"])`, compare stdout, stderr, exit on the three-task store and on a missing file | unit | proposed | Must (F7) |
| 6 | One subtest each: `frob`, `li`, `list --bogus`, `--bogus`, `5`, `list x`, `$'a\nb'`; exit 2, exactly one `td:` stderr line, empty stdout; `--help` exits 0 with stdout only | unit | proposed | Must (F11) |
| 7 | Corrupt cases (invalid JSON, wrong-typed field, missing key, `version` 2) with `list` and bare `td`; exit 1, one `td:` line containing `str(path)`, empty stdout, bytes unchanged | unit | proposed | Must (F11; also cites F4, not on the Features line) |
| 8 | Missing parent of `TD_FILE` and data path is a directory: exit 1, path in message; `list x` on invalid JSON exits 2 | unit | proposed | Must (F11) |
| 9 | Patch `COMMANDS["list"]` with a handler raising `RuntimeError("boom")` (exact line `td: unexpected error: RuntimeError: boom`, no `Traceback`), one raising `TdError("m", 2)` (exit 2, `td: m`), one with a newline in the message (one stderr line) | unit | proposed | Must (F11) |
| 10 | Stored text with `\x1b[31m`, `\n`, `\r`, `\t`, U+2028; no `\x1b` in stdout, `splitlines()` and `split("\n")` (final empty dropped) both give one line per task | unit | proposed | Must (F12) |
| 11 | Real subprocess `td list` over 20,000 tasks of 60 characters; reader takes one line and closes the pipe; return code 0 and empty stderr | integration | proposed | Must (F12) |
| 12 | Real subprocess with `LANG=C`, `LC_ALL=C`, `PYTHONIOENCODING=ascii`, `PYTHONUTF8=0`, `PYTHONCOERCECLOCALE=0`, task `café`; stdout exactly `1 [ ] caf?\n`, no `UnicodeEncodeError` | integration | proposed | Must (F12) |
| 13 | `ast` scan: no `isatty`, no ESC in string constants, no `NotImplementedError`, no pass-only function; text search of non-comment lines for `TODO`/`FIXME` | unit (static scan) | proposed | Must (F12) |
| 14 | Counting wrappers patched on the loaded module; `td list` calls `resolve_path` once, `load_store` once, `save_store` zero times | unit | proposed | Must (F7) |

Notes: criterion 12 fails on a platform where Python ignores `PYTHONIOENCODING`; that is what the pinned variables are for. Criterion 11 needs a large generated file (generate in the temp dir, do not commit).

## RFC-003: `td add`, `td done`, `td rm`

Test file: `tests/test_commands.py`. Fixtures are written non-canonically (4-space indent) so a rewrite is detectable. Prerequisites: RFC-001 interfaces, RFC-002 `main`, `format_task`, `COMMANDS` and `ARGUMENTS`.

| Criterion | Test | Level | Exists? | Priority |
|---|---|---|---|---|
| 1 | `add buy milk` and `add "buy milk"` on an empty store; stdout exactly `1 [ ] buy milk\n`, empty stderr, exit 0, file now exists | unit | proposed | Must (F6) |
| 2 | `add "  buy milk  "` stores `buy milk`; `add "  a" "b  "` stores `a b` | unit | proposed | Must (F6) |
| 3 | `add` with no args, `""`, `"   "`, `"  \t "`; exit 2, one `td:` line, empty stdout, file not created or changed | unit | proposed | Must (F6) |
| 4 | `a\nb`, `a\r`, `\nabc`, `abc\n`, `-x` each exit 2 and file unchanged; `add -- -x` stores `-x`; `main(["add","\udcff"])` exits 2 | unit | proposed | Must (F6) |
| 5 | 100,000-character text through `add` then `list` (full line printed); `naïve café` round trip; tab stored, printed as a space | unit | proposed | Must (F6) |
| 6 | Add two, `rm 2`, add (id 3, list shows 1 and 3); `rm 1` leaves other ids; add two, rm both, add gets id 3 | unit | proposed | Must (F6, F9) |
| 7 | `done 1` silent exit 0 and `[x]` in next list; `done 01`; file with id `10**20` marked by `done 100000000000000000000` | unit | proposed | Must (F8) |
| 8 | `done` on an already-done task: exit 0, silent, file bytes unchanged | unit | proposed | Must (F8) |
| 9 | `rm 1`: silent exit 0, gone from list, other ids and file `next_id` unchanged | unit | proposed | Must (F9) |
| 10 | `done`/`rm` with `99`, `0`, `99999999999999999999`, and `rm 007`; exit 1, stderr exactly `td: no task with id <as typed>`, empty stdout, file unchanged; on a missing file none is created | unit | proposed | Must (F8, F9) |
| 11 | Eight bad ids (`abc`, `-1`, `1.5`, `+1`, `" 1"`, `""`, none, `1 2`) for `done` and again for `rm`; exit 2, one `td:` line, empty stdout, file unchanged | unit | proposed | Must (F11) |
| 12 | Corrupt files (four kinds) with `add x`, `done 1`, `rm 1` (exit 1, `td:` line with `str(path)`, empty stdout, bytes unchanged); `add`, `add ""`, `done abc`, `done -1` exit 1; `done` and `rm` with no argument exit 2 | unit | proposed | Must (F11) |
| 13 | Counting wrappers: successful `add`, `rm`, `done` of an open task call `load_store` once and `save_store` once; failed commands and `done` of a done task call `save_store` zero times | unit | proposed | Must (F6, F8, F9) |

Notes: criterion 4's surrogate case is skipped nowhere; it calls `main` directly because a shell cannot pass it. Mocks: none beyond the counting wrappers.

## RFC-004: `td clear` (Should-have)

Test file: `tests/test_clear.py`. Built only if the user decides to build `clear` (FEATURES.md F10 is Should); if skipped, no test here is written and RFC-002 test 6 already covers "unknown command exits 2". Priority is Should for every row.

| Criterion | Test | Level | Exists? | Priority |
|---|---|---|---|---|
| 1 | Tasks 1 done, 2 open "keep me", 3 done, `next_id` 4; `clear` silent exit 0; `list` prints exactly `2 [ ] keep me` | unit | proposed | Should (F10) |
| 2 | Same scenario; file `next_id` is 4 and `add_task` on the reloaded store returns id 4 | unit | proposed | Should (F10) |
| 3 | All tasks done: exit 0, empty task list, same `next_id`, `list` empty | unit | proposed | Should (F10) |
| 4 | No done tasks: bytes of the non-canonical fixture unchanged and no temp file in the directory; no data file: none created | unit | proposed | Should (F10) |
| 5 | `clear extra`, `clear ""`, `clear --bogus`, also on a corrupt file; exit 2, one `td:` line, empty stdout, file unchanged | unit | proposed | Should (F10; also cites F11, not on the Features line) |
| 6 | Four corrupt kinds (including `done` as an integer); exit 1, one `td:` line with `str(path)`, empty stdout, bytes unchanged | unit | proposed | Should (F10; also cites F4, not on the Features line) |

## RFC-005: Release checks

Test file: `tests/test_release.py`. Prerequisites: RFC-001, RFC-002, RFC-003 complete; `tests/fixtures/v1.json`. Subprocesses use one env dict (`TD_FILE`, `PYTHONUTF8=1`, `PYTHONIOENCODING=utf-8`, `PATH` with the install dir first).

| Criterion | Test | Level | Exists? | Priority |
|---|---|---|---|---|
| 1 | `ast` import scan of `td` against `sys.stdlib_module_names`; scan of `tests/*.py` (stdlib or `helpers` only); no test file named like a stdlib module | unit (static scan) | proposed | Must (F13) |
| 2 | `ast` scan of `td` for the 14 banned imports, the names `system`, `popen`, `eval`, `exec`, `__import__` (as name, attribute or alias) and string constants equal to them | security (static scan) | proposed | Should (F16) |
| 3 | Copy only `td` into an empty dir, chmod +x, put first on `PATH`; bare `td add x` prints exactly `1 [ ] x\n`, then `td list` the same | integration | proposed | Must (F14) |
| 4 | Copy of `tests/fixtures/v1.json` as data file of the installed copy; `list` prints exactly `1 [x] first\n3 [ ] naïve café\n4 [x] x\n`; `add y` prints `5 [ ] y` and the first three tasks are unchanged in the file | integration | proposed | Must (F14; also cites F5, not on the Features line) |
| 5 | 5,000-task file copied fresh per run; `list`, `add x`, `done 1`, `rm 2` each three times as subprocesses; every exit 0, median under 1 second | performance | proposed | Should (F16) |
| 6 | Nested `python3 -m unittest discover tests` with fresh `HOME`, `TD_FILE` unset and the skip variable set; exit 0 and no `.td.json` in the temp `HOME` | integration | proposed | Must (F13) |
| 7 | `ast.parse(..., feature_version=(3, 10))` on `td` and each `tests/*.py` | unit (static scan) | proposed | Must (F13) |
| 8 | Manual: full suite on Python 3.10, on a newer Python, on Linux and on macOS, recorded in the RFC's Implementation Notes (see Manual gaps) | manual | proposed | Must (F13, F15) |
| 9 | `ast` scan of `td` string constants (f-string pieces included) for `/` or `\` other than `DEFAULT_FILE` and docstrings; no `os.sep`, `os.path.sep`, `os.altsep`, `os.path.altsep` | unit (static scan) | proposed | Must (F15) |

## RFC-006: Lock for concurrent runs (CR-001)

Test file: `tests/test_lock.py`. Prerequisites: RFC-001 to RFC-004 Reviewed. A holder is a separate subprocess that enters `data_lock(path)`, prints `ready` and waits for a line on stdin; tests read `ready` before starting the run under test, so no row depends on winning a race. Priority is Must (F17) for every row.

| Criterion | Test | Level | Exists? | Priority |
|---|---|---|---|---|
| 1 | `MUTATING` is the four names, `LOCK_WAIT_SECONDS` is 10, `data_lock` exists; `ast` scan: `fcntl` imported inside `try`/`except ImportError`, no other new import except `time` | unit (static scan) | proposed | Must (F17) |
| 2 | Holder held: `add x`, `done 1`, `rm 2`, `clear` each still running after 0.5 s with no output; after release each exits 0 within 10 s with its result in the file | integration (real subprocesses) | proposed | Must (F17) |
| 3 | Holder held: `list` and bare `td` exit 0 within 5 s with correct stdout, file unchanged | integration | proposed | Must (F17) |
| 4 | `LOCK_WAIT_SECONDS` patched to 0.3, holder held: each of the four returns 1, one `td:` line with `str(path)`, empty stdout, file bytes unchanged, no extra file, under 3 s | unit with subprocess holder | proposed | Must (F17) |
| 5 | 8 parallel `add` subprocesses on a missing file, 5 rounds: 8 tasks, ids 1 to 8 once each, `next_id` 9 | stress (real subprocesses) | proposed | Must (F17, G2) |
| 6 | `clear`, `done 3`, `rm 4`, `add y` in parallel on a 4-task store, 5 rounds: task 2 open, 1 and 4 absent, 3 done or absent, one `y` with id 5, `next_id` 6 | stress | proposed | Must (F17, G2) |
| 7 | Holder killed with SIGKILL; later `add z` exits 0 within 5 s (posix only) | integration | proposed | Must (F17) |
| 8 | Directory listing after `add` on a missing file, failed commands, an argparse error, a no-op `clear` and a timeout: exactly `["tasks.json"]` or `[]` as stated; missing parent directory exits 1 with the path and creates nothing | unit | proposed | Must (F17, DATA-7) |
| 9 | Recording wrappers: `add` gives enter, `load_store`, `save_store`, exit; unknown id gives enter, `load_store`, exit; corrupt file likewise; argparse error no lock; `list` no lock | unit (mocks of own code only) | proposed | Must (F17) |
| 10 | `sys.modules["fcntl"] = None` before loading: `td` loads, `add x` returns 0 and stores | unit | proposed | Must (F17; Windows assumption) |
| 11 | Whole suite passes: RFC-002 criterion 14, RFC-003 criterion 13, RFC-004 criterion 4, RFC-005 criteria 1, 2, 9 | regression (existing tests) | proposed | Must (F17) |

## Totals

Counted from the tables above (rows, not criteria; RFC-001 criterion 9 has two rows).

| RFC | Criteria | Automated rows | Manual rows | Existing | Proposed |
|---|---|---|---|---|---|
| RFC-001 | 15 | 16 | 0 | 0 | 16 |
| RFC-002 | 14 | 14 | 0 | 0 | 14 |
| RFC-003 | 13 | 13 | 0 | 0 | 13 |
| RFC-004 | 6 | 6 | 0 | 0 | 6 |
| RFC-005 | 9 | 8 | 1 | 0 | 9 |
| RFC-006 | 11 | 11 | 0 | 0 | 11 |
| **Total** | **68** | **68** | **1** | **0** | **69** |

Every criterion of every RFC has at least one row; the manual row is RFC-005 criterion 8.

## Gaps that need manual testing

1. **Python 3.10 run** (RFC-005 criterion 8). Cannot be automated from one machine; no 3.10 interpreter has been used here, so the floor is unverified. Static checks (RFC-005 criterion 7) only catch part of it.
2. **macOS run** of the full suite (same row). Linux only is available here.
3. **Real power loss.** Kill tests (RFC-001 criterion 9) prove the file stays parseable when the process dies; they cannot prove that `fsync` really reached the disk after a power cut. This is not testable in an automated suite; the design (fsync file and directory) is the only guard.
4. **Concurrent runs.** No longer a gap: F17 is a Must (CR-001) and RFC-006 has automated rows. Two things stay manual or unverified: `flock` on a directory on macOS (covered only by the RFC-005 criterion 8 macOS run), and a lock on a network filesystem (out of scope, PRD D-6).
5. **Windows.** Untested by decision (PRD D-8); only the separator scan and the directory-fsync skip are checked.
6. **Success metric** ("use it daily for a month and never open the JSON file by hand"): can only be judged by the user.

## Skipped checks

UI, accessibility, SEO, sessions, scalability and regulatory checks are skipped, following PRD.md Product Type. There is no network test because NFR-8 is covered by the import scan (RFC-005 criterion 2).

## Open Questions

All assumptions, because nobody could be asked (non-interactive run). `/implement-rfc` should show them to the user before code depends on them.

1. **(assumption)** Priority for criteria with no feature ID of their own (RFC-001 criteria 2, 14, 15; RFC-002 criterion 13; RFC-005 criterion 7) is taken from the nearest feature the criterion's rule serves, shown in the row. Nothing was reassigned.
2. **(assumption)** RFC-005 criterion 2 is Should because it cites F16 only; its static scan also serves F13, which is Must. If the scan is dropped as optional, F13 loses a check.
3. **(assumption)** Criterion rows that list many inputs (RFC-001 criterion 6, RFC-003 criteria 10 to 12) are one test method with subtests, not one method per input.
4. **(assumption)** No coverage percentage (RULES.md TEST-9 gives none).
5. Carried forward from RFCS.md and the RFCs, not repeated here: `TD_FILE`, `~/.td.json`, key names, line format, exit codes, the 1 second budget, and whether `clear` is built.
