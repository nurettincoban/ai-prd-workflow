# RULES: td, a tiny command-line to-do list

## Overview

`td` is a single-user, single-machine command-line to-do list for developers who work in a terminal. v1 adds, lists, completes and removes tasks (and optionally clears done tasks), stores them in one JSON file, saves crash-safely, and prints plain text that pipes into grep. It is Python 3.10+ with the standard library only. These rules come from PRD.md, PRD-REVIEW.md and FEATURES.md. Rules cite the requirement or feature they serve so a reviewer can trace them. Items marked **(assumption)** are listed under Open Questions.

Rule IDs are permanent. Never renumber or reuse one; retire a rule by marking it [REMOVED].

## Product type checks

Product type is **CLI** (PRD.md). Applied: command and flag design, exit codes, stdout vs stderr, piping, environment handling, cross-platform paths, install. Skipped, as PRD.md already records: UI design and accessibility (plain text, no graphical interface), SEO (no web pages), sessions (no accounts or server), scalability and regulatory (one user, one machine). No accessibility or responsive-design rules are written for this reason.

There is no existing code, prototype or reference implementation to ground naming and structure in (PRD Open Question 7). The naming rules below use ordinary Python conventions (PEP 8) and are the only naming source until code exists.

## Technology stack

Dependencies were checked: there are none to verify against a registry, because NFR-3 forbids third-party packages. The only version fact is the Python floor. Local interpreter observed with `python3 --version`: 3.13.18. The 3.10 floor comes from PRD.md (NFR-3) and was not run on 3.10 here, so it is **unverified** until the test suite runs on 3.10.

| Item | Choice | Version | Source |
|---|---|---|---|
| Language | Python | 3.10 minimum (floor from NFR-3; unverified on 3.10) | NFR-3, F13 |
| Third-party packages | none | n/a | NFR-3 |
| Argument parsing | `argparse` (stdlib) | bundled | assumption: exit 2 on usage errors matches F11 |
| Storage | `json` (stdlib) | bundled | D-3 |
| Paths | `pathlib` / `os.path` (stdlib) | bundled | NFR-6 |
| Tests | `unittest` (stdlib) | bundled | NFR-3 |

- **STACK-1**: Every `import` in the shipped program is from the Python standard library. A third-party import, or a `requirements.txt`/`pyproject.toml` dependency entry, breaks this rule. (NFR-3, F13)
- **STACK-2**: The program uses no syntax or library feature added after Python 3.10. Check each new stdlib call against the 3.10 documentation, and run the test suite on 3.10 before release. Examples that break it: `tomllib`, `ExceptionGroup`/`except*`, `typing.Self`. (NFR-3, F13)
- **STACK-3**: The program makes no network calls: no import of `socket`, `urllib`, `http`, `ssl` or similar, and no telemetry. (NFR-8, F16)
- **STACK-4**: Tests use `unittest` and the standard library only. A test dependency such as `pytest` breaks this rule, because it would be a second thing to install. (NFR-3; assumption: the "nothing to install" promise is read to cover the test run too)

## Technical preferences

### Structure and naming

The PRD fixes a single-file install (F14). It fixes nothing else about code layout, so internal module design is left to the RFCs.

- **ARCH-1**: The shipped program is one Python file with a `#!/usr/bin/env python3` first line, runnable as `td` after copying it onto PATH and marking it executable. Tests live outside that file. (F14)
- **ARCH-2**: The program has a `main(argv=None)` function that returns an integer exit code, and the file ends with `if __name__ == "__main__": sys.exit(main())`. Tests call `main` directly. A command handler that calls `sys.exit` deep inside the logic breaks this rule. (F11; reason: direct calls make exit codes testable without subprocesses)
- **NAME-1**: Functions, variables and modules use `snake_case`, classes use `CapWords`, constants use `UPPER_SNAKE_CASE`. (PEP 8)
- **NAME-2**: The command names are exactly `add`, `list`, `done`, `rm` and, if built, `clear`. No aliases, abbreviations or extra subcommands in v1. (FR-1 to FR-5, D-7)
- **NAME-3**: The environment variable is named `TD_FILE` and the default data file is `~/.td.json`. Both appear as named constants in one place only, and nowhere else in the code as string literals. (F1; assumption, see Open Questions)

### Data handling

- **DATA-1**: The data file is a JSON object with exactly three top-level keys: a format version integer, a next-id integer, and a list of task objects. Reading a file with a missing or wrong-typed key is a corrupt-file error (see SAFE-3). (F5; exact key names are for the RFC)
- **DATA-2**: Each task has an integer id, a string text and a boolean done state, and no other fields in v1. Due dates, priorities, tags and list names do not appear in the schema. (F5, F18 to F22)
- **DATA-3**: A new task gets its id from the stored next-id counter, and the counter is incremented in the same save. The code never computes an id as "highest existing id plus one" or "length of list plus one". (FR-6, F5, review F-2)
- **DATA-4**: Removing or completing a task never changes any other task's id, and `rm` does not decrease the next-id counter. (FR-6, F5)
- **DATA-5**: The program reads and writes the data file with an explicit `encoding="utf-8"` on every `open` call (or an equivalent explicit UTF-8 encode/decode). A bare `open(path)` on the data file breaks this rule. (NFR-9, F3, review F-8)
- **DATA-6**: A newer format version than the program knows is a corrupt-file error that leaves the file untouched; the program never guesses at a future format. A file written by an earlier v1 build must still load. (F5, F14; assumption)
- **DATA-7**: A missing data file is treated as an empty list. Read-only commands (`list`, bare `td`) never create the file; only a command that changes tasks does. (FR-8, F2)

### Saving and data safety

- **SAFE-1**: Every write of the data file goes through one function. That function writes a temporary file in the same directory as the resolved target, calls `flush()` and `os.fsync()` on it, then calls `os.replace()` onto the target. No other code opens the data file for writing. In-place overwrite (`open(path, "w")` on the real file) breaks this rule. (NFR-1, D-4, F3, review F-3)
- **SAFE-2**: After `os.replace()` the save function fsyncs the containing directory where the platform allows it. If the platform does not support that (an `OSError`, or no `O_DIRECTORY` handle), the step is skipped without failing the save, and no other error is swallowed there. (NFR-1, F3, F15)
- **SAFE-3**: If the data file exists but cannot be read as the expected structure (invalid JSON, wrong types, missing keys, unknown newer version), every command, including `add`, exits non-zero without writing to the data file or deleting it. The error names the file path and the parse problem. (NFR-2, F4, review F-5)
- **SAFE-4**: The save function resolves the target path with `os.path.realpath` (or `Path.resolve`) before choosing the temporary file's directory, so a symlinked data file stays a symlink after a save. (F1, review F-7)
- **SAFE-5**: The temporary file is removed on failure of the save (in a `finally` or `except` block), so a failed save leaves no stray temp file beside the data file. A temp file left by a killed process is never read as data. (NFR-1, F3; assumption)
- **SAFE-6**: A failed command never modifies the data file. Validation (id parsing, text checks, id lookup) happens before the save function is called. (F11)
- **SAFE-7**: No code path deletes, truncates or renames the data file other than the atomic replace in SAFE-1. (D-4, NFR-2)

### Commands and arguments

- **CLI-1**: Arguments after `add` are joined with single spaces to form the task text. Text that is empty or only whitespace is a usage error (exit 2). Text containing `\n` or `\r` is rejected as a usage error (exit 2). Very long text is accepted. (F6; assumption)
- **CLI-2**: `done` and `rm` take exactly one id. A non-integer id (`abc`, `-1`, `1.5`), a missing id or more than one id is a usage error (exit 2). A well-formed id that matches no task is a runtime error (exit 1) and changes nothing. (F8, F9, F11, review F-6; assumption)
- **CLI-3**: Marking an already-done task done succeeds with exit 0 and leaves the file's task data unchanged. (FR-3, F8; assumption)
- **CLI-4**: Running `td` with no command behaves exactly as `td list`, with identical stdout and exit code. (FR-2, F7; assumption)
- **CLI-5**: `td list` prints tasks in ascending id order, including done tasks. An empty list prints nothing and exits 0. (F7; assumption)
- **CLI-6**: `td clear`, if built, removes only done tasks, leaves open tasks and their ids untouched, and exits 0 when there is nothing to clear. (F10)
- **CLI-7**: The environment variable `TD_FILE` is read once, at startup. An empty value counts as unset. A leading `~` is expanded with `os.path.expanduser`. A missing parent directory of the data file is a runtime error (exit 1) with the path in the message; the program does not create it. (FR-7, F1, review F-7; assumption)

### Output, errors and exit codes

- **OUT-1**: Normal output goes to stdout only, and every error message goes to stderr only. A failed command writes nothing to stdout. (FR-9, NFR-5, F11)
- **OUT-2**: Exit codes are 0 for success, 1 for a runtime error (unknown id, unreadable or corrupt data file, missing parent directory) and 2 for a usage error (bad arguments, unknown command). No other exit code is used in v1. (NFR-5, F11; assumption)
- **OUT-3**: Output contains no ANSI escape sequences and no color or styling code, and no code checks `isatty()` to change the output format. (NFR-4, F12, F21)
- **OUT-4**: Each task prints on exactly one line. Before printing, control characters in task text (including `\x1b`, `\n`, `\r`) are removed or replaced, so stored text can never add a line or an escape sequence. (NFR-4, F12, review F-4; assumption)
- **OUT-5**: A `BrokenPipeError` on stdout (for example `td list | head -1`) ends the process quietly: no traceback and no message. The handler follows the documented Python pattern of redirecting stdout to `os.devnull` before exit so the interpreter does not report a second error on flush. (G4, F12, review F-10; assumption)
- **OUT-6**: Output survives a non-UTF-8 locale (for example `LANG=C`): stdout is configured so unencodable characters print as replacement characters (`errors="replace"`) rather than raising `UnicodeEncodeError`. The same applies to stderr. (NFR-9, F12, review F-8; assumption)
- **OUT-7**: The program never lets an uncaught Python exception reach the user as a traceback. Expected failures (see OUT-2) are caught in one place in `main` and printed as a single-line message on stderr prefixed with `td:`. (FR-9, F11; assumption)

## Security and privacy

- **SEC-1**: The program makes no network calls and sends no data anywhere. (NFR-8, F16; same check as STACK-3)
- **SEC-2**: Task text and the environment variable's value are never passed to a shell: no `os.system`, no `subprocess` with `shell=True`, no `eval`, `exec` or `pickle`. The JSON file is parsed only with `json`. (assumption: standard injection hygiene, the program has no reason to run commands)
- **SEC-3**: The data file is created with the process's default permissions (the default umask); the program does not widen them with `chmod`. (assumption: it is a personal file in the home directory and no secrets are expected in it; the PRD sets no permission requirement)

## Performance

- **PERF-1**: Each command reads the data file once and, if it changes data, saves it once. A command that loops over tasks does not re-read or re-save the file per task. (NFR-7, F16; reason: this is what keeps a few thousand tasks responsive)
- **PERF-2**: The program has no startup work beyond importing standard-library modules and parsing arguments: no background threads, no caches written to disk, no update checks. (NFR-7, NFR-8, F16)

## Development standards

### Testing

- **TEST-1**: Each of the commands `add`, `list`, `done`, `rm` (and `clear` if built) has at least one test of its success path and one of its failure path (unknown id or bad arguments), asserting stdout, stderr and the exit code each time. (F6 to F11)
- **TEST-2**: A test kills a saving process at each stage of the save (before the temporary file is complete, after it is written but before the replace, after the replace) and checks that the data file then parses and holds either the previous task list or the new one. Killing is done with a real subprocess or an injected failure at each step, not by only reading the code. (NFR-1, F3, G2)
- **TEST-3**: A test writes a corrupt file (invalid JSON, wrong types, missing key, newer version number), runs each command including `add`, and checks the exit code is non-zero, stderr names the path, stdout is empty and the file is byte-for-byte unchanged. (NFR-2, F4)
- **TEST-4**: A test adds tasks 1 and 2, removes 2, adds again, and checks the new task's id is 3, not 2. (FR-6, F5, review F-2)
- **TEST-5**: A test runs `td list` with stdout closed early (for example piped into a process that exits immediately) and checks there is no traceback on stderr. (F12, review F-10)
- **TEST-6**: A test runs with `LANG=C`/`LC_ALL=C` and non-ASCII task text, and checks there is no `UnicodeEncodeError`. (F12, review F-8)
- **TEST-7**: Tests for environment handling cover: unset, empty, `~` expansion, relative path, missing parent directory, and a symlinked target that is still a symlink after a save. (F1, review F-7)
- **TEST-8**: Every test uses a temporary directory and sets `TD_FILE` to a path inside it. A test that reads or writes `~/.td.json` breaks this rule, because it can destroy the developer's real tasks. (F1; reason: the author uses the tool daily)
- **TEST-9**: A test runs the suite on Python 3.10 before release, and on macOS and Linux. The tests give no coverage percentage target; they are measured by the cases above, not a number. (NFR-3, NFR-6, F13, F15; assumption: no coverage figure was requested)

### Completeness and ambiguity

- **DEV-1**: No `TODO`, `FIXME`, `pass`-only function bodies, `NotImplementedError` stubs or commented-out code in a finished change. (completeness)
- **DEV-2**: Behavior the PRD or FEATURES.md leaves open is implemented as the assumption written there, and the code cites it with a short comment naming the open question (for example `# assumption: PRD Open Question 6, exit codes`). The implementer does not pick a different behavior silently. (PRD Open Questions)
- **DEV-3**: Nothing in v1 adds a feature listed as Won't Have: due dates, priorities, tags, colors, multiple lists, accounts, sync, server, or locking. A change that adds one needs a PRD change first. (D-7, F17 to F23)
- **DEV-4**: Public functions and `main` have a one-line docstring saying what they do and what they return or raise. Code comments explain why, not what. (assumption: single file, one maintainer, so the habit is cheap and keeps the single file navigable)

## Agent configuration

If the project uses an AI coding agent, wire RULES.md into its config so the rules stay in context. This run wrote `CLAUDE.md` and `AGENTS.md` in the project folder, each pointing at RULES.md, PRD.md and FEATURES.md.

## Open Questions

Every item here is an assumption made because nobody could be asked (non-interactive run). `/implement-rfc` should put them in front of the user before code depends on them. None of them weakens a requirement.

1. **Concurrent runs vs goal G2 (High, for PRD.md).** These rules implement atomic replace only (SAFE-1) and no lock (DEV-3, F17). Two overlapping `td add` runs can drop one task, which contradicts G2 "never lose tasks". PRD.md must either add a locking requirement (then add a LOCK rule category here, and note the dependency on `fcntl`/`msvcrt`) or reword G2 to "never lose tasks to a crash". The rules do not settle this.
2. **Environment variable `TD_FILE` and default file `~/.td.json`** (NAME-3, CLI-7).
3. **Exit codes 0 / 1 / 2** (OUT-2). Only zero vs non-zero was specified.
4. **List line format.** Rules fix one task per line, ascending id order, and the `[ ]` / `[x]` marker (CLI-5); the exact column layout and the line printed by `add` are open (PRD Open Question 5, review F-12). The RFC must give one worked example per command.
5. **Bare `td` runs `list`; `done` is idempotent** (CLI-3, CLI-4).
6. **Input rules for `add` and for ids** (CLI-1, CLI-2).
7. **Control-character and output-encoding handling, closed-pipe behavior** (OUT-4 to OUT-6). The mechanisms (strip vs replace; `errors="replace"`) are choices, not stated requirements.
8. **Data file schema details**: top-level key names, the future-version rule and the permissions behavior (DATA-1, DATA-6, SEC-3).
9. **Tests use `unittest`, not `pytest`** (STACK-4), because "nothing to install" is read to include the test run.
10. **Python 3.10 floor is unverified**: the observed interpreter is 3.13 and no 3.10 run was possible (Technology stack).
11. **Existing prototype**: none assumed (PRD Open Question 7); if one exists, naming and structure rules above should be re-derived from it.
12. **`td clear` is Should-have** and only built if time allows (CLI-6).

## Rule index

| Category | Count | IDs |
|---|---|---|
| STACK | 4 | STACK-1 to STACK-4 |
| ARCH | 2 | ARCH-1 to ARCH-2 |
| NAME | 3 | NAME-1 to NAME-3 |
| DATA | 7 | DATA-1 to DATA-7 |
| SAFE | 7 | SAFE-1 to SAFE-7 |
| CLI | 7 | CLI-1 to CLI-7 |
| OUT | 7 | OUT-1 to OUT-7 |
| SEC | 3 | SEC-1 to SEC-3 |
| PERF | 2 | PERF-1 to PERF-2 |
| TEST | 9 | TEST-1 to TEST-9 |
| DEV | 4 | DEV-1 to DEV-4 |
| **Total** | **55** | |
