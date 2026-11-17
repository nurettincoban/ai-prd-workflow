# RFC-001: Storage core (data file, schema, crash-safe save)

**Features**: F1, F2, F3, F4, F5, F15
**Depends on**: none
**Rules**: STACK-1, STACK-2, STACK-4, ARCH-1, NAME-1, NAME-3, DATA-1, DATA-2, DATA-3, DATA-4, DATA-5, DATA-6, DATA-7, SAFE-1, SAFE-2, SAFE-3, SAFE-4, SAFE-5, SAFE-7, CLI-7, TEST-2, TEST-3, TEST-4, TEST-7, TEST-8
**Complexity**: High

## Summary

Everything that touches the data file: where it lives, what it contains, how it is read, and how it is saved without ever leaving a partial file. This RFC creates the single program file `td` (repo root) containing only library-style functions for now, and the test helper that lets tests import it. No command exists yet; RFC-002 adds `main`. It also settles review findings F-2 (never-reused ids) and F-3 (fsync) from PRD-REVIEW.md, both High impact.

## Technical approach

Files:

- `td`: the one shipped Python file (ARCH-1). Importing it runs nothing: no I/O, no `main` call. (RFC-002 adds the shebang line, `main` and the `__main__` guard.) Constants `ENV_VAR = "TD_FILE"` and `DEFAULT_FILE = "~/.td.json"` appear here once and nowhere else as literals (NAME-3, assumption). Docstrings and messages count as literals for this rule: they refer to the constants, never spell the strings out. Only comments may.
- `tests/helpers.py`: `load_td()` loads `td` (found as the parent of `tests/`) as a module named `td` with `importlib.machinery.SourceFileLoader`, because the file has no `.py` extension; and `temp_env()`, a context manager that creates a temp directory, sets `HOME` and `TD_FILE` (to `<tmp>/tasks.json`) inside it, yields the directory, and restores both variables (including "was unset") on exit (TEST-8). Tests do `import helpers` (`unittest discover tests` puts `tests/` on `sys.path`); there is no `tests/__init__.py`.
- `tests/test_storage.py`: the tests for this RFC. `tests/fixtures/v1.json`: see criterion 7.

Interfaces exposed to later RFCs. These names, signatures and behaviors are fixed; RFC-002 to RFC-005 refer to this section and must not redefine them.

- `class TdError(Exception)`: constructor `TdError(message: str, exit_code: int = 1)`; `str(e) == message`; attribute `e.exit_code`. Only exit codes 1 and 2 are ever used (OUT-2). `class UsageError(TdError)`: constructor `UsageError(message)`, `exit_code` is 2. Every expected failure raises one of these.
- `resolve_path() -> pathlib.Path`: reads the environment on every call and keeps no cache; `main` (RFC-002) calls it exactly once per run, which is what CLI-7's "read once" means. `TD_FILE` unset or empty gives `Path(os.path.expanduser("~/.td.json"))`; otherwise `Path(os.path.expanduser(value))`. A relative value stays relative (`Path("rel.json")`, resolved by the OS against the working directory at use); nothing makes it absolute.
- `load_store(path) -> dict` and `save_store(path, store) -> None` accept `str` or `pathlib.Path`. `load_store` returns `{"version": 1, "next_id": int, "tasks": [{"id": int, "text": str, "done": bool}, ...]}`. Task order in the file is not significant and is preserved as stored; consumers sort. Order of checks in `load_store`: (1) the parent directory of `path` as passed (not of its resolved target) must exist and be a directory, else `TdError`; (2) a missing file returns `{"version": 1, "next_id": 1, "tasks": []}` and creates nothing; (3) read as UTF-8 and validate. `save_store` is the only function that writes the data file (SAFE-1); it runs the same validation on the store it is given and raises `TdError` without touching the disk if the store is invalid, so no caller can write a file that `load_store` would call corrupt. Order in `save_store`: validate the store first, then the target's directory (the parent of the resolved target must exist and be a directory, else `TdError` naming `str(path)`). So an invalid store with a missing directory reports the invalid store. A dangling symlink whose target directory is missing therefore loads as a missing file (empty store) and fails on save with a `TdError` naming `str(path)`.
- `add_task(store, text) -> dict`: mutates `store` in place: appends `{"id": store["next_id"], "text": text, "done": False}`, increments `store["next_id"]`, returns the new task. Never computes an id from the list (DATA-3). It does not validate `text`; the `add` handler does (RFC-003).
- `find_task(store, task_id: int) -> dict`: returns the task with that id, or raises `TdError(f"no task with id {task_id}")` (exit 1).
- `remove_task(store, task_id: int) -> None`: `find_task`, then removes that task from the list in place. Never touches `next_id` (DATA-4).
- `clear_done(store) -> int`: removes every task whose `done` is true in place, returns how many it removed. Never touches `next_id`.

Save algorithm (pseudocode). It calls `os.open`, `os.fsync` and `os.replace` through the `os` module (never `from os import ...`) so tests can wrap them:

```
target = realpath(path)
dir = dirname(target)
tmp = os.open(unique name in dir, O_WRONLY|O_CREAT|O_EXCL, 0o666)   # umask decides the mode (SEC-3); same filesystem
try:
    write utf-8 json to tmp; flush; os.fsync(tmp)          # step 1
    os.replace(tmp, target)                                # step 2
finally:
    if tmp still exists: remove it                         # SAFE-5
os.fsync(open(dir, O_RDONLY)); on OSError (including failing to open dir) skip   # step 3: SAFE-2, F15
```

The file mode of an existing data file is not preserved across a save: the new file gets what the umask gives (assumption). Any `OSError` raised before or by `os.replace` becomes `TdError` (exit 1) whose message names the path. Any other exception type raised in steps 1 and 2 propagates unchanged (the temp file is still removed); `main` reports it as an unexpected error, exit 1 (RFC-002). Only `OSError` from step 3 is skipped; any other exception from it also propagates unchanged, although the new store is already in place on disk (the caller gets an exception, not a changed store). A process killed mid-save may leave a temp file next to the data file; nothing ever reads such a file (the data file is only ever the target path).

Validation. The error message is `<path>: <problem>`, where `<path>` is `str(path)` exactly as passed in (not the realpath). For invalid JSON the problem is the text of the `json.JSONDecodeError` (F4 asks for the parse error); for a structure problem it names the offending key or field in single quotes, for example `key 'next_id' must be a positive integer`. Structure problems are all corrupt cases except invalid JSON, invalid UTF-8, an empty file and a non-object top level (those say `invalid JSON`-style text, `empty file` or `not a JSON object`); duplicate ids name `'id'`, and `next_id` not above every id names `'next_id'`. Corrupt means any of: invalid JSON or invalid UTF-8; an empty file; not an object; a key other than `version`, `next_id`, `tasks` missing or extra; `version` not an integer, or not 1 (so 0, negative, or 2 and above are all corrupt, DATA-6); `next_id` not an integer of at least 1; `tasks` not a list; a task that is not an object with exactly `id`, `text`, `done`; `id` not an integer of at least 1; `text` not a `str`; `done` not a `bool`; duplicate task ids; `next_id` not greater than every task id; a duplicate key in any JSON object (added in the fix round, follow-up F2: `invalid JSON: duplicate key '<key>'`); nesting so deep that the parser hits Python's recursion limit (`invalid JSON: nesting too deep`, SAFE-3, review round 2 B2). `bool` is never accepted where an integer is required. Newlines and control characters inside `text` are valid; printing sanitizes them (RFC-002). Key names `version`, `next_id`, `tasks` are an assumption (see Open Questions). Why `next_id` is validated: a hand-edited or damaged counter would silently reuse ids and defeat F5. A future build that adds fields must bump `version`; extra fields in a version 1 file are corrupt (DATA-2).

Other read failures (the path is a directory, permission denied, any other `OSError`) are `TdError` with exit 1 and a message naming the path. The data file is never created by a read, never deleted or truncated by any code (SAFE-7). Reading and writing use `encoding="utf-8"` always (DATA-5).

Scope hand-off: this RFC has no commands, so command-level parts of TEST-3 and SAFE-3 (every command exits non-zero on a corrupt file) are tested in RFC-002, RFC-003 and RFC-004. F15 here means only the directory-fsync skip (criterion 12); platform runs and the separator check are RFC-005.

## Acceptance criteria

1. With `TD_FILE` unset and `HOME` set to a temp dir, `resolve_path()` returns `Path(<HOME>/.td.json)`; with `TD_FILE=/x/y.json` it returns `Path("/x/y.json")`; `TD_FILE=""` counts as unset; `TD_FILE=~/z.json` returns `Path(<HOME>/z.json)`; `TD_FILE=rel.json` returns `Path("rel.json")`. (F1, CLI-7, TEST-7)
2. `ENV_VAR` and `DEFAULT_FILE` are each defined once in `td`. A test parses `td` with `ast` and finds the strings `TD_FILE` and `.td.json` in no string constant (docstrings and messages included) except the two definitions. (NAME-3)
3. If the data file's parent directory does not exist, `load_store` and `save_store` raise `TdError` (exit code 1) whose message contains `str(path)`; the directory is not created. This holds although the file is also missing, so the parent check comes first. A data path that is a directory, and a parent that is a regular file, raise the same way. (F1, CLI-7)
4. `load_store` on a missing file in an existing directory returns the empty store and does not create the file or anything else in the directory. (F2, DATA-7)
5. `save_store` followed by `load_store` returns an equal store, including non-ASCII text and a task text containing a newline; the file on disk is a JSON object with exactly the keys `version`, `next_id`, `tasks`, each task having exactly `id`, `text`, `done`; with umask 022 the new file's mode is 0644 and with umask 077 it is 0600 (no chmod, SEC-3; this mode check is skipped with `unittest.skipUnless(os.name == "posix", ...)`, F15 leaves Windows untested). (F3, F5, DATA-1, DATA-2)
6. For each of these inputs, `load_store` raises `TdError` (exit code 1) whose message starts with `str(path)`, and the file is byte for byte unchanged: invalid JSON (the message also contains the `JSONDecodeError` text), an empty file, invalid UTF-8 bytes, a JSON array, a missing top-level key, an extra top-level key, `version` 2, `version` 0, `version` `true`, `next_id` as a string, `next_id` 0, `tasks` as an object, a task missing a key, a task with an extra key, `text` as a number, `done` as an integer, an id as a boolean, duplicate ids, `next_id` equal to the highest id, `version` -1, `next_id` -1, an id of 0, an id of -1, a duplicate object key (top level and inside a task), and 200000 `[` characters (the message says `nesting too deep`). For the structure cases (see Validation) the message also contains the offending key in single quotes, for example `'next_id'`, `'tasks'`, `'done'`, `'id'` (duplicate ids); a test asserts the quoted form, since bare `id` also occurs in the word `invalid`. (F4, DATA-6, SAFE-3, TEST-3)
7. `tests/fixtures/v1.json` holds exactly: `version` 1, `next_id` 5, and three tasks: id 1 done `"first"`, id 3 open `"naïve café"`, id 4 done `"x"`. `load_store` on it returns that literal dict, and `add_task` on the loaded store then gives the new task id 5. This is the compatibility fixture later builds must keep loading (its absent id 2 stands for a removed task). (F5)
8. With a store holding tasks 1 and 2: `remove_task(store, 2)` then `add_task` returns id 3, and `store["next_id"]` is then 4 (also after `save_store` and `load_store`). With tasks 1, 2, 3 and no removal, `add_task` returns 4. After removing every task, `add_task` returns exactly the store's `next_id` from before the add (never 1 unless `next_id` is 1). `find_task` and `remove_task` on a missing id raise `TdError` (exit 1) whose message is `no task with id <n>`; `clear_done` raises nothing, removes exactly the done tasks, returns their count, and leaves `next_id` unchanged. (F5, DATA-3, DATA-4, TEST-4)
9. Real-subprocess kill test, deterministic: a child process runs `save_store` with wrappers installed around `os.fsync` and `os.replace` that call `os._exit(9)` at a chosen point: before the temp file's fsync (step 1; a temp file may exist, its content is not specified), after the temp fsync and before `os.replace`, and after `os.replace` before the directory fsync. After each kill, `load_store` on the target succeeds and returns the previous store for the first two points and the new store for the third. When no previous file existed, the first two points leave no target file and `load_store` returns the empty store. The same three points are also run as injected `OSError`s in-process, with the same expectations (an injected non-`OSError` propagates unchanged and leaves the same files). The wrapper tells the temp file's fsync from the directory's by `stat.S_ISDIR(os.fstat(fd).st_mode)` on the descriptor, not by call count. (F3, TEST-2)
10. After a failed save (injected exception before `os.replace`) no temp file remains in the data file's directory, compared by directory listing before and after. The test directory holds nothing else, so the listing check is exact. A stray extra file in the directory, such as a killed child leaves (criterion 9), does not affect `load_store` or a later `save_store`, and neither deletes it (a save removes only its own temp file). (SAFE-5)
11. The temp file is created in the same directory as the resolved target: if `TD_FILE` points at a symlink (absolute, relative, and a chain of two), after a save the symlink is still a symlink and the file it points to holds the new store. (F1, SAFE-4, TEST-7)
12. With `os.fsync` and `os.replace` wrapped to record calls, `save_store` records: fsync of the temp file, then `os.replace`, then fsync of the containing directory, in that order. When the directory fsync raises `OSError`, or an `os.open` wrapper that raises `OSError` for the directory's path (and passes every other call through) is installed, the save still succeeds; when it raises any other exception that exception propagates. The wrapper also records the temp file's size (`os.fstat(fd).st_size`) when it is fsynced, and the test asserts that size is greater than zero and equals the size of the saved file: an fsync before the write, or before the flush, passes the order check and protects nothing (added in fix round 3, BUG-REPORT-001 item 4). (F3, F15, SAFE-1, SAFE-2)
13. `save_store` given an invalid store (for example `next_id` as a string, or a duplicate id) raises `TdError` and leaves the existing file byte for byte unchanged, and creates no temp file. (F4, SAFE-1)
14. `TdError("m")` has `exit_code` 1 and `str` equal to `"m"`; `TdError("m", 2).exit_code` is 2; `UsageError("m")` is a `TdError` with `exit_code` 2. (DEV-1; the error path built on it is RFC-002's F11)
15. `helpers.temp_env()` leaves `HOME` and `TD_FILE` as they were (including unset) after it exits, and `python3 -m unittest discover tests` runs the suite with the standard library only. That no test touches the real home directory is checked for the whole suite by RFC-005 criterion 6, not here. (TEST-8, STACK-1, STACK-4)

## Implementation considerations

- This RFC builds no lock: `save_store` and `load_store` stay as specified. Overlapping runs are serialized by RFC-006 (F17, SAFE-8, CR-001) around the load and the save, so this RFC's criteria do not change. Before RFC-006 is built, two overlapping runs can drop a task.
- Third-party dependencies: none.
- Implementer's choice: temp file naming, JSON indentation and key order, how the directory is opened for fsync, the exact wording of messages beyond the pinned parts, whether `ensure_ascii` is on, the exact helper function names beyond `load_td` and `temp_env`, whether `save_store` validates through the same function `load_store` uses (it must behave the same).

## Open Questions

1. **(assumption)** Environment variable `TD_FILE`, default `~/.td.json` (PRD Open Questions 1 and 2).
2. **(assumption)** Key names `version`, `next_id`, `tasks`, and the extra corruption checks in criterion 6 (duplicate ids, `next_id` at or below the highest id, ids and `next_id` below 1, `version` 0).
3. **(assumption)** A `version` above 1 is corrupt, not silently read; extra fields in a version 1 file are corrupt.
4. **(assumption)** The data file's mode after a save follows the umask; an existing file's mode is not preserved (SEC-3 sets no permission requirement).
5. **(assumption)** A kill during a save may leave a stale temp file; it is never read, and cleanup of it is not attempted.

## Implementation Notes

### Plan (Phase 1) -- nobody confirmed it

The user was not available, so the plan below was not shown for approval; implementation proceeded on it anyway. Predecessors: none. Plan: create `td` (library functions only, no `main`), `tests/helpers.py`, `tests/test_storage.py`, `tests/fixtures/v1.json`; order: constants and errors, validation, `load_store`, `save_store`, task helpers, tests. No `reviews/REVIEW-RFC-001.md` exists.

Resting on assumptions nobody confirmed (all taken as written in the RFC, none changed):
- `TD_FILE` and `~/.td.json` (PRD Open Questions 1 and 2; RULES.md Open Questions 2).
- Key names `version`, `next_id`, `tasks`, and the extra corruption checks (duplicate ids, `next_id` not above every id, ids and `next_id` below 1, version 0); a version above 1 and extra fields are corrupt.
- File mode after a save follows the umask; an existing file's mode is not preserved.
- A killed save may leave a stale temp file, never read and never cleaned.
- RFCS.md Open conflicts 1 (no lock; concurrent runs can drop a task, so G2 is only met for crashes), 4 (docstrings and messages must not spell the two literals; followed) and 9 (criterion 14 cites F11; only the exception classes are tested).
- Exit codes 0/1/2 (RULES.md OUT-2) and the 1 second budget do not touch this RFC beyond `TdError.exit_code`.

### Deviations

1. Criterion 15 says the suite runs with `python3 -m unittest discover tests`. That works (25 tests). A bare `python3 -m unittest` or `python3 -m unittest discover` from the repo root finds 0 tests, because `tests/` has no `__init__.py` (the RFC forbids one). Not changed; later RFCs and TEST-STRATEGY.md's baseline command should say `discover tests`. Not approved by anyone (nobody was available); it follows the RFC text.
2. Criterion 15's "runs with the standard library only" is tested by an `ast` scan of every test file and `td` for non-stdlib imports (`sys.stdlib_module_names`), not by a nested `discover` run, which would recurse into itself.
3. `td` starts with a comment line, not a shebang; RFC-002 adds the shebang as the RFC says.
4. Added `.gitignore` (`__pycache__/`): loading `td` through `SourceFileLoader` writes a `__pycache__` folder at the repo root. Not in the RFC.
5. Messages for structure problems quote the offending key, for example `key 'next_id' must be a positive integer`, `task is missing field 'done'`, `duplicate task 'id' 1`. Wording beyond the pinned parts is the implementer's choice per the RFC.

### FILES CHANGED

Created: `td`, `tests/helpers.py`, `tests/test_storage.py`, `tests/fixtures/v1.json`, `.gitignore`. Modified: `RFCs/RFC-001-Storage-Core.md` (this section), `RFCS.md` (Status). Commit: `/implement-rfc RFC-001` on the current branch.

### Verification

`python3 -m unittest discover tests`: `Ran 25 tests ... OK`. Criteria 1 to 15 each have a test (criterion 6: 19 subtests; criterion 9: real-subprocess kills at 3 points with and without a previous file, plus injected OSError and KeyError at the same points). Not verified: Python 3.10 (only 3.13 available), macOS, real power loss. There is no build artifact for this RFC (no `main` yet), so no end-to-end run against built output was possible.

### Future

`json.dumps` output is indented and uses `ensure_ascii` (default); fine for v1. Locking: CR-001 settled it and RFC-006 built it (`data_lock` in `td`, taken in `main` for `add`, `done`, `rm` and `clear`), so overlapping runs no longer lose a write; this RFC's functions are unchanged by it.

### Fix round (after review round 2) -- plan not approved, non-interactive

Plan not approved: nobody was available. No open High conflict touches this RFC (conflict 1 was closed by CR-001), so work proceeded. Predecessors: none.

Blocking issues from `reviews/REVIEW-RFC-001.md` round 2:
- **B1** (open High conflict 1, no lock): not this round's work. CR-001 closed the conflict in favour of G2 and RFC-006 builds the lock. No change here; the re-review should cite CR-001. Note that CR-001 was accepted by the person running the example, not by the user.
- **B2** (SAFE-3, deeply nested JSON): fixed. `load_store` now catches `RecursionError` and raises `TdError("<path>: invalid JSON: nesting too deep")`. Tests: criterion 6 subtest (200000 `[`), plus the same file in the command-level corrupt tests of RFC-002 (`test_cli.py`), RFC-003 (`test_commands.py`) and RFC-004 (`test_clear.py`).

Follow-ups closed (also marked in RFCS.md): F1 (id 0, id -1, `version` -1, `next_id` -1 added to criterion 6), F2 (duplicate keys are corrupt, via `object_pairs_hook`), F3 (new test pre-creates the temp name; dropping `O_EXCL` now fails it), F4 (new test: `next_id` 50 after removing every task, next id is 50), F5 (`save_store` converts the `ValueError` from `json.dumps` to `TdError`, with a test). F6 (wording of Python's 4300-digit text) left open: wording only.

Deviation, not approved by anyone: F2 adds a corrupt case the RFC did not list (duplicate keys); the Validation section and criterion 6 above were updated to match. A file with duplicate keys that used to load now fails with exit 1.

Break-it checks run after the fixes, each caught by the suite: `except RecursionError` disabled, `O_EXCL` dropped, `id < 1` loosened to `< 0`, the `json.dumps` conversion disabled.

Files changed in the fix round: `td`, `tests/test_storage.py`, `tests/test_cli.py`, `tests/test_commands.py`, `tests/test_clear.py`, `RFCs/RFC-001-Storage-Core.md`, `RFCS.md`. Commit: `/implement-rfc RFC-001 (fix round)`.

Verification: before, `python3 -m unittest discover tests` gave `Ran 66 tests ... OK`; after, `Ran 69 tests ... OK`. No build artifact exists beyond the `td` script. Python 3.10 and macOS were not run (RFC-005's job).

### Fix round 2 (after review round 3) -- plan not approved, non-interactive

Plan not approved: nobody was available. No open High conflict touches this RFC (conflict 1 was closed by CR-001). Predecessors: none. RFC-006 (the lock) was not touched.

Blocking issue from `reviews/REVIEW-RFC-001.md` round 3:
- **B3** (criterion 6's `next_id` 0 case did not exercise the positivity check): fixed. Two criterion 6 cases added to `test_corrupt_inputs`: `{"version":1,"next_id":0,"tasks":[]}` and the same with `-1`. With no tasks, the `next_id <= id` check cannot fire, so only the `next_id < 1` check rejects them; each asserts exit code 1, the path, `'next_id'` in the message, and bytes unchanged. No change to `td`.

Break-it check: `store["next_id"] < 1` loosened to `< 0` in `td` now fails 2 tests (it passed all 74 before); `td` was restored and diffs clean.

Follow-ups: none from the RFC-001 list were closable and in scope this round. F6 (wording of Python's 4300-digit text) stays open: wording only, and the only fix is matching Python's message text. F7 (stale "Future" line) must wait until RFC-006 lands, so the line above is left as is. F8 (user confirmation of D-9) needs the user.

Deviations: none from the RFC.

Files changed in fix round 2: `tests/test_storage.py`, `RFCs/RFC-001-Storage-Core.md`, `RFCS.md`. Commit: `/implement-rfc RFC-001 (fix round 2)`.

Verification: before, `python3 -m unittest discover tests` gave `Ran 74 tests ... OK`; after, `Ran 74 tests ... OK` (the two new cases are subtests inside `test_corrupt_inputs`, so the test count is unchanged). Python 3.10 and macOS were not run (RFC-005's job).

### Fix round 3 (after BUG-REPORT-001 item 4) -- plan not approved, non-interactive

Plan not approved: nobody was available. No open High conflict touches this RFC. Predecessors: none. Pending CHANGE-REQUEST-002 was not acted on (nobody accepted it).

Blocking follow-up fixed: RFCS.md `(blocking) RFC-001 (BUG-REPORT-001 item 4)`, now `[CLOSED in the RFC-001 fix round 3]`. `FsyncOrderTest.test_order` (criterion 12) now records the temp file's size when `os.fsync` is called on it and asserts it is non-zero and equals the saved file's size. No change to `td`; `reviews/REVIEW-RFC-001.md` round 4 listed no blocking issue.

Break-it check: (a) deleting `handle.flush()` in `save_store` -- `test_order` fails (it passed all 85 before); (b) moving `os.fsync` before the write and flush -- `test_order` fails. `td` was restored after each and `git diff td` is empty.

Other follow-ups: F9 (empty-file wording) and F6 (4300-digit text) left open, out of scope for this fix round (not blocking). F8 needs the user.

Deviations: none from the RFC; criterion 12's text was extended to describe the new assertion.

Files changed in fix round 3: `tests/test_storage.py`, `RFCs/RFC-001-Storage-Core.md`, `RFCS.md`. Commit: `/implement-rfc RFC-001 (fix round 3)`.

Verification: before, `python3 -m unittest discover tests` gave `Ran 85 tests ... OK (skipped=1)`; after, see the commit's final run (same count, 85, OK, skipped=1: the assertions were added to an existing test). Python 3.10 and macOS were not run (RFC-005's job).
