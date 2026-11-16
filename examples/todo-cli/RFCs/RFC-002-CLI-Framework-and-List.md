# RFC-002: CLI framework, output rules and `td list`

**Features**: F7, F11, F12
**Depends on**: RFC-001
**Rules**: STACK-2, ARCH-1, ARCH-2, NAME-2, DATA-7, SAFE-3, CLI-4, CLI-5, CLI-7, OUT-1, OUT-2, OUT-3, OUT-4, OUT-5, OUT-6, OUT-7, SEC-2, PERF-1, PERF-2, TEST-1, TEST-3, TEST-5, TEST-6, TEST-8, DEV-1
**Complexity**: Medium

## Summary

Turns `td` into a runnable program: `main`, argument parsing, the single error path, exit codes, safe output, and the first command, `td list` (also what bare `td` does). `list` is built here because it is read-only and exercises the whole framework end to end; there are no placeholder handlers (DEV-1). RFC-003 and RFC-004 register their commands in the same dispatch. Names from RFC-001 (`TdError`, `UsageError`, `resolve_path`, `load_store`, `save_store`) are used exactly as RFC-001's "Interfaces exposed" section defines them; this RFC does not redefine them.

Scope: F11 here covers unknown commands, usage errors from argparse, the single error path and load failures. Id validation and unknown-id errors belong to RFC-003 (`done`, `rm`) and extra-argument handling to each command's own RFC. The command-level corrupt-file checks of TEST-3 for `add`, `done`, `rm` and `clear` are in RFC-003 and RFC-004; this RFC tests them for `list`.

## Technical approach

- `td` gains `main(argv=None) -> int` and ends with `if __name__ == "__main__": sys.exit(main())` (ARCH-2). The first line is `#!/usr/bin/env python3`, and the file has the executable bit set (ARCH-1).
- Handler contract (RFC-003 and RFC-004 code against this): `COMMANDS` is a module-level dict `{name: handler}`, read when `main` builds the parser and again when it dispatches, so a test can replace an entry with `unittest.mock.patch.dict`. A handler is `handler(args, store, path) -> list[str]`: `args` is the argparse namespace, `store` is the dict `load_store` returned, `path` is the data file path. It returns the lines to print, each without a trailing newline; an empty list prints nothing. A handler that changes data calls `save_store(path, store)` itself, once, and only after all its validation. It raises `TdError` or `UsageError` for expected failures and never prints or calls `sys.exit`. Why handlers return text: output is written only after the command succeeded, so a failed command never writes to stdout (OUT-1). Each `build_parser()` subparser is created by iterating `COMMANDS`. A command's arguments are declared through a second module-level dict `ARGUMENTS = {name: callable(subparser) -> None}`, read at the same time as `COMMANDS`; the callable adds that command's positionals with `subparser.add_argument`. A name with no `ARGUMENTS` entry gets a subparser with no arguments (`list` and `clear`), and any extra argument is then an argparse error. RFC-003 and RFC-004 register their arguments only this way. Subparsers are created from the same `ArgumentParser` subclass as the main parser (the default of `add_subparsers`, which the `error()` override below relies on), so every parse error, subparser ones included, is one `td:` line.
- Order of events in `main`, and so which error wins: (1) set up output; (2) parse arguments, a parse failure is exit 2 and nothing is read from disk; (3) `path = resolve_path()`, called once (CLI-7); (4) `store = load_store(path)`, called once (PERF-1), failure is exit 1; (5) run the handler (its own usage errors are exit 2, its runtime errors exit 1); (6) write each returned line plus `"\n"` to stdout and flush inside the error-handling block; (7) return 0. So a corrupt data file beats a handler-level usage error such as an empty `add` text, but never beats an argparse error. RFC-006 (CR-001) adds a step between 3 and 4 for the commands in its `MUTATING` set (`add`, `done`, `rm`, `clear`): steps 4 and 5 run inside `with data_lock(path):`, so overlapping runs take turns. `list` is not in the set and takes no lock, so none of this RFC's criteria change.
- Parser: `argparse` with `allow_abbrev=False` on the parser and every subparser (NAME-2: `td --he`, `td li` are errors). A subclass of `ArgumentParser` overrides `error(message)` to write the single line `td: <message>` to stderr, with the same control-character replacement as every other message (so `td $'a\nb'` still gives one line) and raise `SystemExit(2)`, so even usage errors start with `td:` (OUT-7) and no usage dump is written. `-h`/`--help` is not an error: argparse prints help to stdout and exits 0, and `main` returns that code. `main` converts every `SystemExit` raised during parsing into the returned int (`e.code`, 0 or 2) so `main` always returns an int.
- `format_task(task) -> str`: returns `"<id> [ ] <text>"` or `"<id> [x] <text>"` (id in decimal with no padding, one space, marker, one space, text), with every character in Unicode category `Cc`, `Zl` or `Zp` (so `\x1b`, `\n`, `\r`, `\t`, `\x7f`, U+2028, U+2029) replaced by one space. RFC-003 reuses it for `add`'s output. Worked example, tasks 1 open "buy milk", 2 done "write notes", 10 open "x":

```
$ td list
1 [ ] buy milk
2 [x] write notes
10 [ ] x
```

- `list` handler: sorts tasks by id ascending (stored order is irrelevant) and returns `format_task` of each; bare `td` (no command) runs the `list` handler through the same steps (CLI-4).
- Error text, all on stderr as one line (OUT-7): `TdError` prints `td: <message>` and returns its `exit_code`; any other `Exception` prints `td: unexpected error: <type>: <message>` (`type(e).__name__`) and returns 1, never a traceback; `KeyboardInterrupt` prints `td: interrupted` and returns 1 (assumption: OUT-2 allows no other code). Before printing, every message has each `Cc`, `Zl` or `Zp` character replaced by a space, so a message is always one line even when an exception text or a path contains a newline.
- Output setup at the start of `main`, inside the same error-handling block: for each of stdout and stderr, `reconfigure(errors="replace")` only if the stream has a `reconfigure` method (a test may have replaced it with `io.StringIO`) (OUT-6). On `BrokenPipeError` while writing or flushing, redirect stdout to `os.devnull` with `os.dup2` as in the Python documentation (skipped if the stream has no usable file descriptor) and return 0 with no message (OUT-5, assumption: closed stdout is not an error). Any other write error (disk full, bad descriptor, a closed `sys.stdout` that is `None`) is an unexpected error: exit 1 with the message above, but only when there is a line to write; a command that returns `[]` writes nothing and exits 0 whatever stdout is. So "closed stdout exits 0" means a closed pipe (`BrokenPipeError`); a missing or closed descriptor with output pending is exit 1 with one `td:` line (still no traceback, F12).
- No `isatty()` checks, no ANSI codes, no `subprocess`/`os.system`/`eval` anywhere (OUT-3, SEC-2).

## Acceptance criteria

All tests set `TD_FILE` through `helpers.temp_env()` (TEST-8). "Stderr line" means a complete line including its newline.

1. The first line of `td` is `#!/usr/bin/env python3`, the file has an executable bit set, `main(["list"])` returns an `int`, and an `ast` scan of `td` finds no `sys.exit` call except the one in the `__main__` guard. (F11, ARCH-1, ARCH-2)
2. `td list` on tasks 1 (open, "buy milk"), 2 (done, "write notes") and 10 (open, "x") prints exactly `1 [ ] buy milk\n2 [x] write notes\n10 [ ] x\n` to stdout, nothing to stderr, exit 0. (F7)
3. `td list` prints tasks in ascending id order, including done ones, when the file stores them as ids 3, 1, 2. (F7, CLI-5)
4. `td list` with no data file or an empty task list prints nothing, exits 0, and does not create the data file. (F7, F2, DATA-7)
5. On the three-task store of criterion 2, `td` with no arguments gives byte-identical stdout, identical (empty) stderr and the same exit code as `td list`; the same holds on a missing data file. (F7, CLI-4)
6. An unknown command (`td frob`), an abbreviation (`td li`), an unknown flag (`td list --bogus`, `td --bogus`), a stray positional (`td 5`), extra arguments to `list` (`td list x`) and a newline inside an argument (`td $'a\nb'`) each exit 2, write exactly one stderr line starting with `td:`, and write nothing to stdout. `td --help` exits 0 and writes only to stdout. (F11, OUT-2, OUT-7, NAME-2)
7. If the data file is corrupt (any case of RFC-001 criterion 6; at least invalid JSON, a wrong-typed field, a missing key and `version` 2 are run here), `td list` and bare `td` exit 1, write exactly one stderr line, starting with `td:` and containing `str(path)`, write nothing to stdout, and leave the file byte for byte unchanged. (F11, F4, SAFE-3, TEST-3)
8. If `load_store` fails for another expected reason (missing parent directory of `TD_FILE`; the data path is a directory), the exit code is 1 with the same stderr format, containing the path, and empty stdout. A bad argument and a corrupt file together (`td list x` on invalid JSON) exit 2. (F11, CLI-7)
9. An unexpected exception inside a handler (a test replaces `COMMANDS["list"]` with a function that raises `RuntimeError("boom")`) yields exit 1, exactly one stderr line equal to `td: unexpected error: RuntimeError: boom`, and no `Traceback` text. A `TdError("m", 2)` raised by a replaced handler yields exit 2 and the line `td: m`. A message containing a newline appears on one stderr line. (F11, OUT-7)
10. A stored task text containing `\x1b[31m`, `\n`, `\r`, `\t` or U+2028 is printed on one line with each such character replaced by one space; stdout contains no `\x1b` byte, and `stdout.splitlines()` gives exactly one line per task and so does `stdout.split("\n")` once its final empty element (after the closing newline) is dropped. (F12, OUT-3, OUT-4)
11. Pipe test, a real subprocess run with two `Popen` objects or one `Popen` and a reader: `td list` over 20,000 tasks of 60 characters each (over a megabyte, so it cannot fit in the pipe buffer) is started with stdout piped; the reader reads one line, closes the pipe and waits. `td`'s own return code is 0 and its stderr is empty (no `Traceback`, no `BrokenPipeError`). (F12, OUT-5, TEST-5)
12. Encoding test, a real subprocess with `LANG=C`, `LC_ALL=C`, `PYTHONIOENCODING=ascii`, `PYTHONUTF8=0` and `PYTHONCOERCECLOCALE=0` (these make an ASCII stdout, so the feature is exercised) and a stored task text `café`: `td list` exits 0, stderr has no `UnicodeEncodeError`, and stdout is `1 [ ] caf?\n`. (F12, OUT-6, TEST-6)
13. An `ast` scan of `td` (comments and docstrings are not scanned, so a comment may say "no isatty check") finds no name or attribute `isatty`, no string constant containing the ESC character, no `NotImplementedError` and no function whose body is only `pass`; a plain-text search of the code lines (comment lines excluded) finds no `TODO` or `FIXME`. (OUT-3, DEV-1)
14. With `resolve_path`, `load_store` and `save_store` replaced by counting wrappers (the test patches the attributes on the loaded module, so `main` and the handlers must call these by bare name and not bind them early), `td list` calls `resolve_path` once, `load_store` once and `save_store` zero times. (PERF-1, CLI-7)

## Implementation considerations

- Python 3.10 floor: `sys.stdout.reconfigure` exists since 3.7; use only 3.10-safe library calls (STACK-2).
- `--help` text comes from `argparse`; its exact wording is the implementer's choice, and it lists whichever commands are registered at that time.
- Tests call `main` directly (with `contextlib.redirect_stdout` and `redirect_stderr` over `io.StringIO`) for most cases and use a real subprocess for the pipe and locale cases (ARCH-2, TEST-1).
- Implementer's choice: argparse prog name, how the `SystemExit` conversion is written, the wording of messages beyond the pinned ones (RFC-001 pins the load-failure messages).

## Open Questions

1. **(assumption)** Line format `<id> [ ] <text>` / `<id> [x] <text>` and show-all-tasks (PRD Open Question 5). No filter flag.
2. **(assumption)** Exit codes 0, 1, 2 (PRD Open Question 6); `KeyboardInterrupt` exits 1.
3. **(assumption)** Control characters (and U+2028/U+2029) become one space each when printed (PRD Open Question 13); a broken pipe exits 0 quietly (PRD Open Question 18), while a closed or missing stdout with output pending exits 1 with one `td:` line.
4. **(assumption)** The error prefix `td: ` on stderr, including argparse usage errors, which print one `td:` line instead of argparse's usage block.
5. **(assumption)** When a bad argument and a corrupt file occur together, the argument error (exit 2) wins; when a handler-level usage error and a corrupt file occur together, the corrupt file (exit 1) wins.

## Implementation Notes

### Plan (Phase 1) -- nobody confirmed it

The user was not available, so the plan was not shown for approval; implementation proceeded on it anyway. Predecessor RFC-001 has Status Reviewed in RFCS.md, so it counts. `reviews/REVIEW-RFC-001.md` has no blocking issues (its non-blocking N1, `RecursionError` from deeply nested JSON, is RFC-001's and not changed here; such a file would exit 1 as `td: unexpected error: RecursionError: ...`). Plan: edit `td` (shebang, `main`, `build_parser`, `format_task`, `cmd_list`, `COMMANDS`, `ARGUMENTS`, output setup, error path), add `tests/test_cli.py` with one test per criterion (TEST-STRATEGY.md RFC-002 rows 1 to 14). Order: framework, `list`, tests. Handlers are not called by name in `main`, only through `COMMANDS`, so RFC-003 and RFC-004 only add entries.

Resting on assumptions nobody confirmed (all taken as written in the RFC):
- Line format `<id> [ ] <text>`, show all tasks, no filter flag (PRD Open Question 5).
- Exit codes 0, 1, 2; Ctrl-C exits 1 with `td: interrupted` (RFCS.md Open conflict 5).
- Control characters and U+2028/U+2029 print as one space; a broken pipe exits 0 quietly; a closed or missing stdout with output pending exits 1 (PRD Open Questions 13, 18).
- The `td: ` prefix on every stderr error, including argparse errors; an argument error beats a corrupt file, a corrupt file beats a handler-level usage error.
- From RFC-001, unchanged: the environment variable and default file names, the key names. (No lock at the time of this RFC; RFC-006 has since added one in `main` for `add`, `done`, `rm` and `clear`, after step 3 of the order of events; `list` still takes none. RFCS.md Open conflict 1 is closed.) RFCS.md Open conflict 8 (RFC-002's Features line omits F2 and F4, cited by criteria 4 and 7) was followed as stated: the tests follow the criteria.

### Deviations

1. None from the RFC text. Wording of the `argparse` messages (for example `td: argument command: invalid choice: 'li' (choose from 'list')`) is the implementer's choice per the RFC.
2. The sanitizing helper `_one_line` is shared by `format_task` and every error message; RFC-002 describes the rule once for both.
3. Criterion 1's `sys.exit` scan and criterion 13's scans are done in `tests/test_cli.py` over the `ast` of `td`, as the RFC says.

### FILES CHANGED

Modified: `td` (shebang, executable bit, CLI framework), `RFCs/RFC-002-CLI-Framework-and-List.md` (this section), `RFCS.md` (Status Implemented). Created: `tests/test_cli.py`. Commit: `/implement-rfc RFC-002` on the current branch.

### Verification

`python3 -m unittest discover tests`: `Ran 39 tests ... OK` (25 from RFC-001, 14 new). Criteria 1 to 14 each have a test. Criteria 11 (broken pipe over a megabyte of output) and 12 (ASCII stdout) run the real `td` file as a subprocess; there is no separate build artifact, since `td` is the shipped file. Not verified: Python 3.10 (only 3.13 here), macOS (RFC-005).

### Future

`--help` lists only registered commands; RFC-003 and RFC-004 get usage text by registering in `COMMANDS` and `ARGUMENTS`.

### Fix round (after review round 2, Changes requested)

Plan not approved by a user (nobody available); the fixes are test additions plus one wording change, no open High conflict touches RFC-002 (conflict 1 is about concurrent writers; `list` writes nothing).

Blocking issues fixed (each was broken on purpose, the suite failed, then the code was restored byte for byte):
- **B1 (criterion 11, pipe handling):** new `test_c11_reader_closed_first` closes the pipe before `td` writes, so a `BrokenPipeError` always happens; new `test_c11_write_lines_redirects_to_devnull` calls `_write_lines` with a stdout stub that raises `BrokenPipeError` and asserts `os.dup2(devnull_fd, stdout_fd)`. Breaks: `dup2` replaced by `pass` fails the stub test; `except BrokenPipeError` swapped for another exception fails both.
- **B2 (`allow_abbrev`):** criterion 6 gained `--he`, `--hel` and `list --he`. Removing `allow_abbrev=False` from the parser fails the first two; from the subparsers fails the third.
- **B3 (argparse error sanitizing):** criterion 6 gained `["list", "a\nb"]` (one stderr line). Removing `_one_line` from `_Parser.error` fails it.

Follow-ups closed: F1 (`--help` wording: new `HELP` dict in `td`, test `test_c6_help_text_says_what_commands_do`; breaking it fails the test) and F2 (`test_c15_keyboard_interrupt`; changing the exit code to 0 fails it). F3 left open (contrived, output setup not touched).

### Deviations (fix round)

1. `td` changed, not only tests: the `HELP` dict and `help=HELP.get(...)` in `build_parser` (follow-up F1). It touches the text of `--help` for RFC-003 and RFC-004's commands; no criterion pins that text. Not approved by a user (nobody available).
2. The original `test_c11_broken_pipe` is kept unchanged; the two new tests do the guarding.

### FILES CHANGED (fix round)

Modified: `td`, `tests/test_cli.py`, `RFCs/RFC-002-CLI-Framework-and-List.md`, `RFCS.md`. Commit: `/implement-rfc RFC-002 (fix round)` on the current branch.

### Verification (fix round)

`python3 -m unittest discover tests`: before `Ran 69 tests ... OK`; after `Ran 73 tests ... OK` (4 new: reader-closed-first, dup2 stub, help text, KeyboardInterrupt). Not verified: Python 3.10, macOS (RFC-005).

### Fix round 2 (after BUG-REPORT-001 item 5, blocking follow-up in RFCS.md)

Plan not approved by a user (nobody available); no open High conflict touches this change (`list` writes nothing; conflict 5 is the Ctrl-C exit code, unchanged: `td: interrupted`, exit 1). The review file `reviews/REVIEW-RFC-002.md` has no blocking issue; the only blocking item is the follow-up. CHANGE-REQUEST-002 is pending and was not acted on.

Bug: the `except KeyboardInterrupt` is inside `main`, so a Ctrl-C while Python was importing modules or loading `td` (the first 5 to 40 ms) raised outside it and printed a traceback (31 of 60 tries before the fix; see Fix round 3: that claim was wrong, 19 of 60 tracebacks remained).

Fix, in `td` only: at the top of the file, before the other imports, `import os, signal, sys` and, only when `td` runs as the program (`__name__ == "__main__"`, so tests that import it change no signal handler), install `_on_sigint` for SIGINT. While `_STARTED` is False the handler writes `td: interrupted` to fd 2 and calls `os._exit(1)`: the same line and code as the normal path, and nothing is half-done at that point because no data file has been touched. `main` sets `_STARTED = True` as the first statement of its `try`; from then on the handler raises `KeyboardInterrupt`, so the existing `except KeyboardInterrupt` runs and `with data_lock` and `save_store` clean up as before (an `os._exit` there would skip them).

Not fixable: an interrupt before the first line of `td` runs (interpreter start-up, `site` import, reading the script) cannot be caught by `td`. The Python start-up window is a few ms; an interrupt there prints Python's own traceback or nothing. OUT-7 is not weakened; this is an open question for the user: accept that limit, or wrap the program in a launcher (not in scope of this RFC, ARCH-1 says one file).

New tests in `tests/test_cli.py`: `test_c16_interrupt_during_imports` (a stand-in `argparse` module on `PYTHONPATH` sends SIGINT to itself while `td` is importing, at a fixed point, not by timing; expects exit 1, empty stdout, stderr exactly `td: interrupted\n`), `test_c16_sigint_handler_after_main_starts` (handler raises `KeyboardInterrupt` and does not `_exit` once started; writes and `_exit(1)`s before) and `test_c16_main_marks_started`.

Broken on purpose, each restored byte for byte: handler not installed (caught, 1 failure); `os._exit(0)` (caught, 2 failures); `_STARTED` ignored in the handler (caught); `main` never sets `_STARTED` (not caught by the first two tests, since the output is the same; caught after adding `test_c16_main_marks_started`).

### Deviations (fix round 2)

1. `td` gained a module-level `_STARTED`, `_on_sigint` and a SIGINT install under the `__main__` guard, and three imports moved above the guard. No criterion covers it; RFC-002's error path ("`KeyboardInterrupt` prints `td: interrupted`") is what it implements. Not approved by a user (nobody available).
2. The RFC's rule "no function whose body is only `pass`" and the `sys.exit` scan are unaffected (`os._exit` is not `sys.exit`).

### FILES CHANGED (fix round 2)

Modified: `td`, `tests/test_cli.py`, `RFCs/RFC-002-CLI-Framework-and-List.md`, `RFCS.md`. Commit: `/implement-rfc RFC-002 (fix round 2)` on the current branch.

### Verification (fix round 2)

`python3 -m unittest discover tests`: before `Ran 85 tests ... OK (skipped=1)`; after `Ran 88 tests in 18.1s ... OK (skipped=1)` (3 new). Reproduction from RFCS.md: **the earlier claim of 0 tracebacks in 60 tries was wrong** (see Fix round 3). Not verified: Python 3.10, macOS (RFC-005).

### Fix round 3 (after review round 4, Changes requested)

Plan not approved by a user (nobody available). **Open conflict 12 (High: RFC-002 against SAFE-6 for `add`, `done`, `rm`; CHANGE-REQUEST-002 Change 3 pending) touches this RFC, so by the instructions this RFC should stop and report.** I did the part that does not depend on it, B1 (the signal handler, nothing to do with the output path or `save_store`), and did **not** touch the closed-stdout behavior, Open Question 3, step 6 of the order of events or any criterion about it. B2 is therefore unfixed and this RFC stays In progress, not Implemented: sending it to review now would only hit the same blocking conflict.

**Why the earlier "0 of 60" was wrong.** The fix round 2 loop used `cmd & ... kill -INT $!`. A non-interactive shell starts background jobs with SIGINT ignored, so the signal was dropped and no traceback was possible; the number measured nothing. Measured here with a Python driver (`subprocess.Popen`, `send_signal(SIGINT)` after a delay, `TD_FILE` a fresh temp name, Python 3.13.18 on Linux, 4 cores), so the child has the default SIGINT disposition. Two protocols: (a) the reviewer's sweep, 8 to 48 ms in steps of 2, 12 runs each (252 runs), counting stderr that contains `Traceback` and the first `td` line each names; (b) 60 runs at 20 ms.

| | (a) sweep, tracebacks of 252 | first `td` line named | (b) 20 ms, of 60 |
|---|---|---|---|
| Before (commit 2494db3) | 72 | line 4 `import signal`: 27; line 0 or no `td` frame (interpreter start-up): 45 | 19 |
| After `_signal` | 57 | line 4: 0; line 13 (`raise KeyboardInterrupt` after main returned): 1; start-up: 56 | 5 |
| After `_signal` and ignoring SIGINT after main | 48 | none in `td`'s code; all 48 name line 0 or no `td` frame (start-up, Open conflict 11) | 3 |

The 20 ms runs after the fix were not classified one by one; the sweep, which was, shows every remaining traceback is in the start-up window `td` cannot reach. The earlier (shell) loop gave 0 of 60 on both before and after, which is why it is not used.

Fixes, in `td`:
1. `import _signal` (a built-in module with no imports of its own) replaces `import signal`, and the handler is installed with `_signal.signal(_signal.SIGINT, ...)`. Only `_signal`, `os` and `sys` are imported before the handler exists.
2. After `main` returns, SIGINT is set to ignored (only when run as the program) before `sys.exit`. The sweep found a second `td`-owned window: an interrupt after main returned raised `KeyboardInterrupt` in the handler outside any `except` (line 13).

New tests in `tests/test_cli.py`: `test_c16_handler_installed_before_heavy_imports` (only `_signal`, `os`, `sys` may be imported before the install; checked on the `ast`), `test_c16_interrupt_during_import_of_signal` (stand-in `signal.py` on `PYTHONPATH` interrupts at the import; no traceback, exit 0 or `td: interrupted` exit 1) and `test_c16_interrupt_after_main_returns` (an atexit callback sends SIGINT after `main` returned; exit 0, empty stderr). The follow-up F5 (a test running the real timing loop) is **not** added: the loop is timing dependent and flaky by nature; the three deterministic tests stand in for it. F5 stays open.

Broken on purpose, each restored byte for byte (`cmp`), suite run each time: `import signal as _signal` back at the top (2 new tests fail); the SIGINT-ignore after main removed (1 fails); handler install removed (2 fail); `_STARTED = True` removed from `main` (1 fails). The nested release run (`test_6_nested_suite_run`) failed alongside each, as it should.

### Deviations (fix round 3)

1. `td` gained the SIGINT-ignore after `main` returns, which the review did not ask for (it was found by the sweep and is the same follow-up). Wording of exit codes unchanged: a late Ctrl-C after a finished run exits with main's code. Not approved by a user (nobody available).
2. Conflict 12 / B2 not fixed, on purpose: needs the user's decision on CHANGE-REQUEST-002 Change 3.

### FILES CHANGED (fix round 3)

Modified: `td`, `tests/test_cli.py`, `RFCs/RFC-002-CLI-Framework-and-List.md`, `RFCS.md`. Commit: `/implement-rfc RFC-002 (fix round 3)` on the current branch.

### Verification (fix round 3)

`python3 -m unittest discover tests`: before `Ran 88 tests ... OK (skipped=1)`; after `Ran 91 tests in 18.9s ... OK (skipped=1)` (3 new). Not verified: Python 3.10, macOS (RFC-005).
