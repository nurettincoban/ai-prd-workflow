# PRD: td, a tiny command-line to-do list

## Overview

`td` is a command-line to-do list for developers who live in the terminal. Every to-do app the author has tried is "too much"; `td` does four things (add, list, done, remove) and nothing else in v1. It is a Python program using only the standard library, stores tasks in one local JSON file, and prints plain text that pipes into grep.

Value proposition: capture and check off tasks without leaving the terminal, with no accounts, no sync, no server, and no risk of losing data.

## Product Type

**Type: CLI.**

Checks that apply (from the CLI row): command and flag design, exit codes, stdout vs stderr, piping and scripting, config and environment precedence, cross-platform paths and shells, install and upgrade.

Checks skipped:

- UI design: the output is plain text with no colors or layout beyond lines of text (colors are out of scope for v1).
- Accessibility: there is no graphical interface; plain text works with screen readers and terminals as-is.
- SEO: there are no web pages.
- Sessions: there are no accounts, logins or server.

Also not applicable, beyond the standard CLI skips: scalability, regulatory and business model (single user, single machine, personal tool).

## Goals and Objectives

- G1: Let the user add, list, complete and remove tasks with one short command each.
- G2: Never lose tasks, including when the process crashes or is killed partway through saving.
- G3: Run anywhere Python 3.10+ is installed with nothing to install from a package index.
- G4: Produce output that is easy to script: plain text on stdout, errors on stderr, meaningful exit codes.
- G5: Ship v1 in one weekend.

## Scope

In scope for v1:

- Commands to add, list, mark done, and remove tasks.
- Optionally (the user said "maybe"): a command to clear all done tasks. Included as a lower-priority requirement (FR-5).
- One JSON data file in the home directory, relocatable via an environment variable.
- Crash-safe saving.

Explicitly out of scope for v1:

- Due dates
- Priorities
- Tags
- Colors
- Multiple lists
- Accounts, sync, a server, multi-user use or multi-machine use

## User Personas or Target Audience

**The terminal-native developer** (the author and people like them). Works in a terminal all day, uses shell pipelines and grep, runs macOS or Linux, has Python 3.10+ available. Wants a to-do list that adds no context switch and no setup. Uses one machine, one list. Is comfortable with command-line conventions and does not want a TUI, a GUI or a configuration step.

## Functional Requirements

Priority: must-have first, then should-have.

Must-have:

- **FR-1**: `td add <text>` appends a new task with the given text and a unique id, and prints the new task's id and text to stdout.
- **FR-2**: `td list` prints all tasks, one per line, as plain text including the task id, its done/not-done state and its text. Running `td` with no command behaves as `td list` (assumption).
- **FR-3**: `td done <id>` marks the task with that id as done. It is not an error to mark an already-done task done (assumption).
- **FR-4**: `td rm <id>` removes the task with that id permanently.
- **FR-6**: Task ids stay stable for the life of the task: completing or removing other tasks never changes an existing task's id (assumption: ids are never reused or renumbered, so a command copied from earlier output still refers to the same task). Because removing the highest-numbered task must not free its id, the data file stores the next id to hand out alongside the tasks; "highest existing id plus one" is not enough (finding F-2).
- **FR-7**: The data file location defaults to a single JSON file in the user's home directory and can be overridden by an environment variable (name is an open question, see below).
- **FR-8**: If the data file does not exist, `td` treats it as an empty list and creates it on the first write.
- **FR-9**: Every error (unknown id, missing argument, unreadable or corrupt data file) is written to stderr, nothing is written to stdout for that failure, and the process exits non-zero.

Should-have:

- **FR-5**: `td clear` removes all done tasks. The user said "maybe"; build it only if time allows in the weekend.

## Non-Functional Requirements

- **NFR-1**: Data safety. A crash, kill or power loss at any point during a save must leave either the complete previous file or the complete new file on disk, never a partial one. Implementation approach is for the RFC or implementation step (for example write to a temporary file in the same directory, flush, then fsync it, then atomically replace; also fsync the directory where the platform allows, since a power loss can otherwise leave the replace undone or the new file empty) (finding F-3).
- **NFR-2**: Corrupt data is never overwritten. If the data file exists but cannot be parsed, `td` exits non-zero with an error on stderr and leaves the file untouched (assumption: this follows from "never lose my tasks").
- **NFR-3**: Dependencies. Python standard library only; supports Python 3.10 and newer; no third-party packages.
- **NFR-4**: Output is plain text: no ANSI color codes or other escape sequences, one task per line in `td list`, so the output pipes cleanly into grep and other tools.
- **NFR-5**: Stream and exit-code discipline. Normal output goes to stdout, errors to stderr. Exit code 0 on success, non-zero on any failure (the specific non-zero codes are an open question).
- **NFR-6**: Platforms. macOS and Linux are supported and tested. Windows is nice to have but untested and not a release criterion; paths use `pathlib`/`os.path` rather than hard-coded separators so Windows is not needlessly blocked.
- **NFR-7**: Performance. Commands respond with no perceptible delay for a personal list (assumption: up to a few thousand tasks; no explicit budget was given).
- **NFR-8**: Privacy. All data stays on the local machine; the tool makes no network calls and sends no telemetry.
- **NFR-9**: Text encoding. Task text is stored and printed as UTF-8 (assumption).

## User Journeys

1. **Capture a task.** The user is mid-work, types `td add "write release notes"`, sees the new id echoed, and goes back to work.
2. **Review the list.** The user runs `td list` (or `td list | grep release`) and sees every task with its id and state.
3. **Finish a task.** The user runs `td done 3`; the task shows as done in the next `td list`.
4. **Drop a task.** The user runs `td rm 5` and the task is gone.
5. **Tidy up (optional).** The user runs `td clear` to remove all done tasks at once.
6. **Mistake.** The user types an id that does not exist; `td` prints a clear message on stderr and exits non-zero, and no data changes.
7. **Crash.** The process is killed during a save; the next `td list` shows the list as it was before or after that command, never a broken file.
8. **Relocate data.** The user sets the environment variable to another path (for example inside a synced folder or a project directory) and `td` uses that file instead.

## Success Metrics

- **Primary (stated by the user):** the user uses `td` every day for a month and never opens the JSON file by hand.
- Supporting checks for release (derived from the requirements, not stated by the user): no task loss in a test that kills the process during save; all four core commands work on macOS and Linux with Python 3.10+.

## Timeline

- Target: one weekend for v1 (stated by the user).
- Finer milestones were not given. Suggested order, not a commitment: core storage with atomic save, then add/list/done/rm, then error handling and tests, then `clear` if time allows. (assumption)

## Decisions

- **D-1: Command-line only, plain text output.** Reason: the user lives in the terminal and wants to pipe output into grep. Rejected: TUI, GUI, colored output (colors are explicitly out of v1).
- **D-2: Python 3.10+, standard library only.** Reason: runs anywhere Python is installed with nothing to pip install. Rejected: third-party CLI or storage libraries, other languages.
- **D-3: Single JSON file in the home directory, overridable by an environment variable.** Reason: simple, inspectable, relocatable. Rejected: SQLite, multiple files, a config file (none were requested).
- **D-4: Never lose tasks, including on a crash mid-save.** Reason: stated requirement and the core trust issue for a personal tool. Rejected: simple in-place overwrite of the file.
- **D-5: Errors go to stderr with a non-zero exit code; normal output goes to stdout.** Reason: scripting and piping.
- **D-6: Single user, single machine; no accounts, sync or server.** Reason: stated by the user. Rejected: any sync or multi-user design.
- **D-7: v1 feature set is add, list, done, remove (clear-done optional).** Due dates, priorities, tags, colors and multiple lists are deferred. Reason: the user finds other apps "too much".
- **D-8: macOS and Linux are the supported platforms; Windows is best effort and untested.** Reason: stated by the user.

## Open Questions/Assumptions

Open questions (not answered by the user):

1. **Environment variable name.** The user wants one but did not name it. Placeholder: `TD_FILE`. **(assumption)**
2. **Default data file name.** Placeholder: `~/.td.json`. **(assumption)**
3. **Task id scheme.** Sequential integers that are never reused is assumed; short hashes or positional numbers are alternatives. **(assumption)**
4. **Whether `td clear` is in v1.** The user said "maybe". Treated as should-have (FR-5). **(assumption)**
5. **`td list` format and filters.** Exact line format, whether done tasks are shown by default, and whether a filter flag (for example only open tasks) is wanted. Placeholder: show all tasks, with a `[x]` / `[ ]` marker. **(assumption)**
6. **Exit codes.** Only zero versus non-zero was specified; distinct codes for usage errors, not-found and data-file errors are undecided. **(assumption: 0 success, 1 runtime error, 2 usage error)**
7. **Existing prototype or code to extract from.** IDEA.md mentions none, so the project is assumed to start from scratch. Confirm no prior version exists. **(assumption)**
8. **Distribution and install (finding F-9).** How `td` is installed (copy a single script onto PATH, a package, an entry point) and upgraded was not discussed, and the release check "works on macOS and Linux" cannot be run without it. Assumed: a single Python file with a `#!/usr/bin/env python3` shebang, runnable as `td` once on PATH; upgrading means replacing the file, and the data file format must stay readable across versions. **(assumption)**
9. **Concurrent runs. (High, finding F-1)** G2 says tasks are never lost, but with atomic replace only and last-writer-wins, two overlapping `td add` runs (two terminals) silently drop one task. The user must say whether a lock around the read-modify-write is wanted. **(assumption: atomic replace only; last writer wins, which contradicts G2 for overlapping writes. Changing it to an advisory lock would add a requirement and a non-portable dependency on `fcntl`/`msvcrt`.)**
10. **Behavior on `td add` with empty text, multi-word text without quotes, or very long text.** Assumed: arguments after `add` are joined with spaces; empty text is an error. **(assumption)**
11. **Backup of the data file.** Not requested; atomic writes are the only protection assumed. **(assumption)**
12. **Timeline detail.** Only "a weekend" was given; no milestones or owner dates. **(assumption: none needed for a one-person weekend project; finding F-13)**
13. **Newlines and control characters in task text (finding F-4).** NFR-4 promises one task per line with no escape sequences, but `td add $'a\nb'` or text containing ANSI escapes would break that. **(assumption: `td add` rejects text containing a newline; other control characters are stored but printed with escapes stripped or replaced)**
14. **Corrupt-file recovery (finding F-5).** NFR-2 refuses to touch a corrupt file, so the only recovery is editing the file by hand, which the success metric says should never be needed. **(assumption: the error message names the file path and the parse error so the user can fix or move it; no automatic backup, see 11)**
15. **Invalid id arguments (finding F-6).** `td done abc`, `td done -1`, `td done 1 2`. **(assumption: a non-integer id is a usage error, exit 2; a well-formed id that does not exist is a runtime error, exit 1; one id per command)**
16. **Environment variable edge cases (finding F-7).** Empty value, relative path, `~` in the value, a parent directory that does not exist, and the target being a symlink (an atomic replace swaps the symlink itself for a regular file). **(assumption: an empty value counts as unset; `~` is expanded; a missing parent directory is an error; the temporary file is created next to the resolved target so a symlink keeps working)**
17. **Output encoding (finding F-8).** NFR-9 covers the file, but stdout under a non-UTF-8 locale (for example `LANG=C` on older systems) can raise `UnicodeEncodeError` on non-ASCII task text. **(assumption: the data file is always read and written as UTF-8 explicitly, and output falls back to replacement characters rather than crashing)**
18. **Closed pipe (finding F-10).** `td list | head -1` or `grep -q` closes stdout early; Python by default prints a `BrokenPipeError` traceback. **(assumption: a closed stdout exits quietly and is not treated as an error)**

Assumptions made in requirements above (each also tagged inline): bare `td` runs `list` (FR-2); marking done is idempotent (FR-3); ids are stable and never reused (FR-6); corrupt files are never overwritten (NFR-2); performance target of a few thousand tasks (NFR-7); UTF-8 text (NFR-9); suggested build order (Timeline).
