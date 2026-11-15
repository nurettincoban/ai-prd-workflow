# FEATURES: td, a tiny command-line to-do list

## Overview

`td` is a command-line to-do list for developers who work in a terminal. v1 does four things: add, list, mark done and remove tasks, with an optional "clear done". It is a single-user, single-machine Python 3.10+ program using only the standard library. Tasks live in one JSON file, saved crash-safely, and output is plain text that pipes into grep. Source: PRD.md and PRD-REVIEW.md. Every High-impact review finding (F-1, F-2, F-3) is placed below. Feature IDs here (F1, F2, ...) are unrelated to the review's finding IDs (F-1, F-2, ...), which carry a hyphen.

Items marked **(assumption)** come from PRD.md and are listed under Open Questions.

## Summary

| Priority | Count |
|---|---|
| Must | 14 |
| Should | 2 |
| Could | 0 |
| Won't | 7 |
| **Total** | **23** |

| Category | Count |
|---|---|
| Storage and data safety | 5 |
| Commands | 5 |
| Output and errors | 2 |
| Platform and constraints | 4 |
| Out of scope (Won't Have) | 7 |
| **Total** | **23** |

## Storage and data safety

| ID | Feature | Priority | Source | Complexity | Acceptance Criteria |
|---|---|---|---|---|---|
| F1 | Data file location: one JSON file, default `~/.td.json` (assumption), overridable by environment variable `TD_FILE` (assumption) | Must | FR-7 | Low | Without the variable, the file is `~/.td.json`. With `TD_FILE` set, that path is used instead. An empty value counts as unset; `~` is expanded; a relative path is accepted; a missing parent directory is an error (exit 1, message on stderr); if the target is a symlink, it keeps working after a save (the temporary file is created next to the resolved target). |
| F2 | Missing file is an empty list; file is created on first write | Must | FR-8 | Low | With no data file, `td list` prints nothing, exits 0 and does not create the file. The first `td add` creates it. |
| F3 | Crash-safe save: a kill or power loss at any point leaves the complete old file or the complete new file | Must | NFR-1 | High | Save writes a temporary file in the same directory as the target, flushes and fsyncs it, atomically replaces the target, then fsyncs the directory where the platform allows. A test that kills the process at each step of a save leaves a parseable file holding either the previous or the new task list. Data is read and written as UTF-8 explicitly. Addresses review finding F-3 (High). |
| F4 | Corrupt data file is never overwritten | Must | NFR-2, FR-9 | Medium | If the file exists but does not parse as the expected structure, every command (including `add`) exits non-zero, writes an error naming the file path and the parse error to stderr, writes nothing to stdout, and leaves the file byte-for-byte unchanged. |
| F5 | Stable, never-reused task ids, backed by a stored next-id counter and a schema version | Must | FR-6 | Medium | The file stores a format version, a next-id counter and the task list. Ids are sequential integers (assumption). Adding task 3 after tasks 1 and 2 exist gives 3. After removing the highest-numbered task, the next `td add` still gets a new, higher id. Completing or removing other tasks never changes an existing id. A file written by an earlier v1 build stays readable. Addresses review finding F-2 (High). |

## Commands

| ID | Feature | Priority | Source | Complexity | Acceptance Criteria |
|---|---|---|---|---|---|
| F6 | `td add <text>` | Must | FR-1 | Low | Appends a task with a new unique id and prints the id and text to stdout (exact line format is an open question). Arguments after `add` are joined with spaces (assumption). Empty or whitespace-only text is a usage error (exit 2). Text containing a newline is rejected (assumption). Very long text is accepted. Text is stored as UTF-8. |
| F7 | `td list`, and bare `td` behaves as `td list` | Must | FR-2 | Low | Prints every task, one per line, with id, a `[ ]` / `[x]` marker and text (assumption). Done tasks are shown by default (assumption). Tasks are in id order. An empty list prints nothing and exits 0. Bare `td` gives identical output and exit code (assumption). |
| F8 | `td done <id>` | Must | FR-3 | Low | Marks the task done; the next `td list` shows `[x]`. Marking an already-done task succeeds with exit 0 (assumption). An unknown id is a runtime error (exit 1) and no data changes. |
| F9 | `td rm <id>` | Must | FR-4 | Low | Removes the task permanently; it no longer appears in `td list`. An unknown id is a runtime error (exit 1) and no data changes. Other tasks keep their ids (see F5). |
| F10 | `td clear`: remove all done tasks | Should | FR-5 | Low | Removes every done task and leaves open tasks and their ids untouched. With no done tasks it exits 0 and changes nothing. Built only if time allows in the weekend; v1 can ship without it. |

## Output and errors

| ID | Feature | Priority | Source | Complexity | Acceptance Criteria |
|---|---|---|---|---|---|
| F11 | Error handling: stderr, nothing on stdout, exit codes, id validation | Must | FR-9, NFR-5 | Medium | Every error (unknown id, missing argument, unreadable or corrupt data file, invalid id) writes a message to stderr, writes nothing to stdout and exits non-zero. Exit 0 on success; 1 for runtime errors (not found, data-file errors); 2 for usage errors (assumption). A non-integer id (`abc`, `-1`) and more than one id are usage errors, exit 2 (assumption). Unknown commands are usage errors. A failed command never modifies the data file. |
| F12 | Plain, pipe-safe output | Must | NFR-4, NFR-9, G4 | Medium | Output has no ANSI colors or escape sequences and shows one task per line. Control characters in stored task text are stripped or replaced when printed, so a task never spans lines (assumption). If stdout is closed early (`td list \| head -1`, `grep -q`), the process exits quietly with no traceback (assumption). Under a non-UTF-8 locale such as `LANG=C`, non-ASCII text prints with replacement characters and does not raise `UnicodeEncodeError` (assumption). |

## Platform and constraints

| ID | Feature | Priority | Source | Complexity | Acceptance Criteria |
|---|---|---|---|---|---|
| F13 | Standard library only, Python 3.10+, no third-party packages | Must | NFR-3 | Low | Imports are limited to the standard library. The program runs on Python 3.10 and newer with nothing installed from a package index. A test run on 3.10 passes. |
| F14 | Distribution: single Python file with a `#!/usr/bin/env python3` shebang, runnable as `td` once on PATH | Must | NFR-3, NFR-6 | Low | Copying the file onto PATH and making it executable is enough to run `td` on macOS and Linux (assumption: this is the install method). Upgrading means replacing the file, and the data format stays readable across versions (see F5). |
| F15 | Platforms: macOS and Linux supported and tested; Windows best effort | Must | NFR-6 | Medium | Core commands pass the test suite on macOS and Linux. Paths use `pathlib` or `os.path`, with no hard-coded separators. Directory fsync is skipped where the platform does not allow it, without failing the save. Windows is untested and not a release criterion. |
| F16 | Local-only and responsive: no network calls, no telemetry, no perceptible delay | Should | NFR-7, NFR-8 | Low | The code makes no network calls (no `socket`, `urllib` or similar imports). Every command finishes with no perceptible delay with a list of a few thousand tasks (assumption: no explicit budget was given). |

## Won't Have (v1)

| ID | Feature | Priority | Source | Complexity | Acceptance Criteria |
|---|---|---|---|---|---|
| F17 | Locking for concurrent runs: PRD Open Question 9 | Won't | G2, Open Question 9 | Medium | Not built in v1 (assumption: atomic replace only, last writer wins). Known gap: two overlapping `td add` runs can drop one task, which conflicts with G2. This is listed as an open question for PRD.md rather than settled here. Addresses review finding F-1 (High). If the user wants a lock, PRD.md gains a requirement and this row becomes a Must. |
| F18 | Due dates | Won't | PRD Scope | Low | No due-date field, flag or output in v1. |
| F19 | Priorities | Won't | PRD Scope | Low | No priority field, flag or sorting in v1. |
| F20 | Tags | Won't | PRD Scope | Low | No tag field or filtering in v1. |
| F21 | Colors | Won't | PRD Scope, NFR-4 | Low | No color or styling in output in v1. |
| F22 | Multiple lists | Won't | PRD Scope | Medium | One list per data file; no list names or switching. |
| F23 | Accounts, sync, server, multi-user and multi-machine use | Won't | PRD Scope, D-6 | High | No login, network service or sync. One user on one machine. |

## Requirement coverage

| Requirement | Feature(s) |
|---|---|
| FR-1 | F6 |
| FR-2 | F7 |
| FR-3 | F8 |
| FR-4 | F9 |
| FR-5 | F10 |
| FR-6 | F5 |
| FR-7 | F1 |
| FR-8 | F2 |
| FR-9 | F4, F11 |
| NFR-1 | F3 |
| NFR-2 | F4 |
| NFR-3 | F13, F14 |
| NFR-4 | F12 |
| NFR-5 | F11 |
| NFR-6 | F14, F15 |
| NFR-7 | F16 |
| NFR-8 | F16 |
| NFR-9 | F12 |

## Open Questions

All of these are assumptions made because nobody could be asked (non-interactive run). `/implement-rfc` should put them in front of the user before code depends on them.

1. **Concurrent runs (High).** F17 is Won't Have, which leaves last-writer-wins and contradicts PRD goal G2 ("never lose tasks") for overlapping writes. For PRD.md: either add a locking requirement or reword G2 to "never lose tasks to a crash". The user must decide.
2. **Environment variable name** `TD_FILE` and **default file name** `~/.td.json` (F1).
3. **Id scheme**: sequential integers, never reused (F5).
4. **`td clear` timing**: Should, built only if time allows (F10).
5. **List line format and filters**: `[ ]` / `[x]` marker, show all tasks, no filter flag (F7). No worked example output exists yet (review finding F-12); settle one per command before the RFC.
6. **Exit codes**: 0 success, 1 runtime error, 2 usage error (F11).
7. **Bare `td`** runs `list`; **`done` is idempotent** (F7, F8).
8. **`td add` input rules**: arguments joined by spaces, empty text is an error, newline in text is rejected (F6).
9. **Control characters in stored text** are stripped or replaced when printed (F12).
10. **Corrupt-file recovery**: the error names the path and parse error; no automatic backup (F4).
11. **Invalid id arguments** are usage errors, exit 2 (F11).
12. **Environment variable edge cases**: empty value is unset, `~` expanded, missing parent directory is an error, symlink target preserved (F1).
13. **Output encoding** falls back to replacement characters; **closed stdout** exits quietly (F12).
14. **Install method**: single file with shebang on PATH (F14).
15. **Performance target**: a few thousand tasks (F16).
16. **Existing prototype**: none assumed; confirm no prior version exists.
