# RFC-003: `td add`, `td done`, `td rm`

**Features**: F6, F8, F9, F11
**Depends on**: RFC-001, RFC-002
**Rules**: NAME-2, DATA-1, DATA-3, DATA-4, DATA-5, DATA-6, SAFE-1, SAFE-3, SAFE-6, CLI-1, CLI-2, CLI-3, CLI-7, OUT-1, OUT-2, OUT-4, OUT-7, PERF-1, TEST-1, TEST-3, TEST-4, TEST-8, DEV-3
**Complexity**: Medium

## Summary

The three commands that change tasks. They register in the `COMMANDS` table from RFC-002 and follow its handler contract exactly: `handler(args, store, path) -> list[str]`, with the store already loaded once by `main`, lines returned without newlines, `save_store(path, store)` called by the handler. They use `add_task`, `find_task`, `remove_task`, `TdError` and `UsageError` from RFC-001 ("Interfaces exposed") and `format_task` from RFC-002; none of these is redefined here.

## Technical approach

Order of events is RFC-002's: argparse errors (exit 2) come first, then the store is loaded (corrupt file or missing directory is exit 1), then the handler runs. So `td done` with no id on a corrupt file exits 2 (argparse), but every check made in the handler loses to a corrupt file and exits 1: `td add` with no arguments, `td add ""`, `td done abc`, `td done -1`, a missing parent directory likewise. Each handler validates, then changes the store in memory, then calls `save_store` once (PERF-1); validation and lookup happen before `save_store`, so a failed command cannot modify the file (SAFE-6).

- Arguments are declared through `ARGUMENTS` (RFC-002): `add` gets `text`, `done` and `rm` get `id`.
- `add`: positional `text` with `nargs="*"`, so an empty list reaches the handler and is rejected there as a usage error with the same `td:` line format. Join the strings with single spaces. If the joined text contains `\n` or `\r` anywhere (checked before stripping, so a leading or trailing newline is rejected too, CLI-1), raise `UsageError`. Then, if the text cannot be encoded as UTF-8 (for example argv bytes that are not valid UTF-8, which Python surfaces as lone surrogates), raise `UsageError`, so `add` never stores text that `save_store` cannot write. Then strip it with `str.strip()` (all Unicode whitespace, applied once to the joined text). If the result is empty, raise `UsageError`. Call `add_task(store, text)`, save, return `[format_task(new_task)]`. Worked example: `td add buy milk` prints `1 [ ] buy milk`. Text that starts with `-` must follow `--` (`td add -- -x`); without `--`, argparse reads a flag-like word such as `-x` as a flag and the command exits 2. How argparse treats other `-` forms (`-1`, `td add a -- b`) is argparse's rule on the running Python and is not pinned. Control characters other than newlines (tab, `\x1b`) are stored as given and sanitized only when printed (OUT-4).
- `done`: positional `id`, exactly one, taken as a string. It is well-formed only if `re.fullmatch(r"[0-9]+", id)` matches (ASCII digits only; no sign, no spaces, no decimal point); otherwise raise `UsageError(f"invalid id: {id}")`. Leading zeros are allowed and mean the same task (`01` is 1). The id is converted with `int` after dropping leading zeros, unless more than 4000 digits remain (Python limits `int` on longer strings); such an id is treated as an unknown id without calling `int` or `find_task`. Any size below that is a real id, since RFC-001 accepts any positive integer. Unknown id: exit 1 with the message `no task with id <id as typed>`, leading zeros included (`td rm 007` says `no task with id 007`); the handler calls `find_task` and re-raises its `TdError` with this message, or raises the same `TdError` itself for the over-long case. Otherwise set `done = True`. If the task was already done, do not call `save_store` (the file is untouched, CLI-3). Otherwise save. Prints nothing (returns `[]`).
- `rm`: same id parsing and lookup via `remove_task`; does not change `next_id`; saves; prints nothing.
- A usage error in a handler is `UsageError` (exit 2); a runtime error is `TdError` (exit 1). Both reach the user through `main`'s single error path as `td: <message>`.

## Acceptance criteria

Every test sets `TD_FILE` through `helpers.temp_env()` (TEST-8). "Unchanged" means byte for byte, and fixtures are written non-canonically (for example indented with 4 spaces) so a command that rewrites the file is detected.

1. On an empty store, `td add buy milk` and `td add "buy milk"` each store the text `buy milk`, print exactly `1 [ ] buy milk\n` to stdout, exit 0 with empty stderr, and the data file now exists. (F6, CLI-1)
2. `td add "  buy milk  "` stores `buy milk` and prints `1 [ ] buy milk`; `td add "  a" "b  "` stores `a b`. (F6)
3. `td add` with no arguments, with `""`, with `"   "`, and with `"  \t "` each exit 2, write exactly one stderr line starting with `td:`, write nothing to stdout, and do not create or change the data file. (F6, CLI-1)
4. `td add $'a\nb'`, `td add $'a\r'`, `td add $'\nabc'` and `td add $'abc\n'` each exit 2 with nothing on stdout and the data file unchanged (or still missing). `td add -x` exits 2; `td add -- -x` stores `-x`. `main(["add", "\udcff"])` (a lone surrogate, as non-UTF-8 argv gives) exits 2 and leaves the file unchanged. (F6, CLI-1, DATA-5)
5. A 100,000-character ASCII text is accepted, and `td list` prints the full 100,000 characters on its line. Non-ASCII text (`naïve café`) round-trips through `add` then `list` in a UTF-8 environment. A text containing a tab is stored with the tab and printed with a space. (F6, DATA-5, OUT-4)
6. After `add` of two tasks, `rm 2`, then `add`, the new task's id is 3 and `td list` shows 1 and 3; after `rm 1` the other tasks' ids are unchanged in `td list`; after `rm` of every task (two added, both removed), the next `add` gets id 3 exactly. (F6, F9, DATA-3, DATA-4, TEST-4)
7. `td done 1` exits 0 with empty stdout and stderr, and the next `td list` shows `[x]` for task 1 and no change for the others. `td done 01` marks task 1. A task with id `10**20` in the file (written by the test) is marked by `td done 100000000000000000000`. (F8)
8. `td done 1` on an already-done task exits 0 with empty stdout and stderr and leaves the data file unchanged. (F8, CLI-3)
9. `td rm 1` exits 0 with empty stdout and stderr, and task 1 no longer appears in `td list`; the other tasks keep their ids and `next_id` in the file is unchanged. (F9, DATA-4)
10. `td done 99`, `td rm 99`, `td done 0`, `td rm 0` and `td done 99999999999999999999` and `td rm 007` (no such task) exit 1, write one stderr line equal to `td: no task with id <id as typed>` (`td: no task with id 007` for the last one), nothing to stdout, and leave the file unchanged; on a missing data file, no file is created. (F8, F9, F11, CLI-2)
11. `td done abc`, `td done -1`, `td done 1.5`, `td done +1`, `td done " 1"`, `td done ""`, `td done` (no id) and `td done 1 2` exit 2, write exactly one stderr line starting with `td:`, nothing to stdout, and leave the file unchanged. The same eight for `rm`. (F11, CLI-2)
12. With a corrupt data file (invalid JSON, a wrong-typed field, a missing key, `version` 2), `add x`, `done 1` and `rm 1` each exit 1, write one `td:` stderr line containing `str(path)`, nothing to stdout, and leave the file unchanged; `td add` (no argument), `td add ""`, `td done abc` and `td done -1` on the same file exit 1 as well, and `td done` and `td rm` with no argument exit 2. (F11, SAFE-3, TEST-3)
13. With `load_store` and `save_store` replaced by counting wrappers, a successful `add`, `rm` and `done` of an open task each call `load_store` once and `save_store` once; a failed command and `done` of an already-done task call `save_store` zero times. The test patches the attributes on the loaded module, so handlers and `main` call both by bare name. (PERF-1, SAFE-6)

## Implementation considerations

- Only the three commands above are registered here. No flags or subcommands beyond them (NAME-2, DEV-3).
- Implementer's choice: the exact wording of messages (apart from `no task with id <id>`), how the id regex is expressed, the wording of the help text, and where the shared id-parsing code lives.

## Open Questions

1. **(assumption)** `done` and `rm` print nothing on success; only `add` prints. PRD FR-3 and FR-4 specify no output. `add` prints the formatted line `<id> [ ] <text>`, which includes the id and the text that FR-1 asks for, plus the marker.
2. **(assumption)** Text is stripped of leading and trailing whitespace after the newline check, and text starting with `-` needs `--`.
3. **(assumption)** Rules for `add` input and for ids (PRD Open Questions 10 and 15); `done` is idempotent and does not rewrite the file (PRD FR-3).
4. **(assumption)** When arguments are bad and the file is corrupt, the winner follows RFC-002's order: argparse errors first, then the load, then handler checks.

## Implementation Notes

### Plan (Phase 1) -- nobody confirmed it

The user was not available, so the plan was not shown for approval; implementation proceeded on it anyway. Predecessors RFC-001 and RFC-002 both have Status Reviewed in RFCS.md, so they count. `reviews/REVIEW-RFC-003.md` does not exist. `reviews/REVIEW-RFC-002.md` has no blocking issues; its non-blocking N1 to N7 belong to RFC-002 and are not changed here. Plan: edit `td` only (add `cmd_add`, `cmd_done`, `cmd_rm`, an id-parsing helper, register them in `COMMANDS` and `ARGUMENTS`; no change to RFC-001 or RFC-002 functions), and add `tests/test_commands.py` with one test per criterion (TEST-STRATEGY.md RFC-003 rows 1 to 13). Order: handlers, then tests.

Resting on assumptions nobody confirmed (all taken as written in the RFC):
- `done` and `rm` print nothing on success; only `add` prints `<id> [ ] <text>` (Open Question 1).
- `add` text is stripped after the newline check; text starting with `-` needs `--` (Open Question 2).
- Rules for `add` input and ids (PRD Open Questions 10 and 15); `done` is idempotent and does not rewrite the file (Open Question 3).
- Bad arguments beat a corrupt file, a corrupt file beats handler-level checks (Open Question 4; RFC-002 Open Question 5).
- From earlier RFCs, unchanged: `TD_FILE`, `~/.td.json`, key names, exit codes 0, 1, 2 (RFCS.md Open conflicts 1, 2, 5; the lock came later, in RFC-006). RFCS.md Open conflict 8 does not touch RFC-003.

### Deviations

1. None from the RFC text.
2. Over-long ids: the cut-off is 4000 digits after dropping leading zeros, as the RFC says; `MAX_ID_DIGITS` names it in `td`.
3. Extra tests beyond the listed inputs: criterion 10 also covers `0` * 5000 + `99` and 4001 nines (the over-long path), and criterion 13 also counts `add ""` and `done abc`.

### FILES CHANGED

Modified: `td` (handlers, registration), `RFCs/RFC-003-Add-Done-Remove.md` (this section), `RFCS.md` (Status Implemented). Created: `tests/test_commands.py`. Commit: `/implement-rfc RFC-003` on the current branch.

### Verification

`python3 -m unittest discover tests`: `Ran 52 tests ... OK` (39 before, 13 new). Criteria 1 to 13 each have a test. Also run by hand against the real `td` file with a temporary `TD_FILE`: `add buy milk`, `add -- -x`, `done 1`, `rm 2`, `list` printed `1 [x] buy milk`, and `done 9` exited 1 with `td: no task with id 9`. There is no separate build artifact, since `td` is the shipped file. Not verified: Python 3.10 (only 3.13 here), macOS (RFC-005).

### Fix round after review round 2 (Changes requested)

No plan was approved (non-interactive run); no open High conflict touches the work: RFCS.md Open conflict 1 is CLOSED by CR-001, so the plan went ahead. Plan: tests only, `td` unchanged.

- **B1 (G2 against no lock): not fixable here.** Open conflict 1 is closed in RFCS.md by CR-001 (accepted by the person running the example, not by the user in IDEA.md). The lock itself is RFC-006, since implemented: overlapping `add`, `done` and `rm` runs now take turns, so no write is lost. The reviewer's condition (a written decision on PRD.md) is met by CR-001; a re-review should cite it.
- **B2 fixed (tests only):** `test_c10_unknown_id` now covers `9`*4301 and `9`*5000 (past Python's 4300-digit `int` limit, so a missing cut-off reports `unexpected error`) and `0`*5001; new `test_c10_leading_zeros_dropped_before_length_check` marks and removes a real task 99 with `0`*5000+`99`, and marks a real 4000-digit id (so the limit cannot be lowered).
- **B3 fixed (tests only):** `test_c11_bad_id` adds Arabic-Indic `\u0663`, full-width `\uff11`, Devanagari `\u0969` and `1\u0663` for `done` and `rm`.
- Deliberate breaks, each restored (suite 74 tests, failures=2 each time; `td` is byte-identical to before): regex widened to Unicode digits; cut-off removed (`if False:`); `lstrip("0")` removed; `MAX_ID_DIGITS` 5000; `MAX_ID_DIGITS` 3000.
- Deviation: none from the RFC text; the criteria 10 and 11 inputs in the RFC are a subset of what the tests now run. Follow-up RFC-003 (round 2, F1) (echo of a long id) stays open: the RFC and criterion 10 require the id as typed, so truncating is an RFC change, not a cheap fix.
- Verification: `python3 -m unittest discover tests` went from `Ran 73 tests ... OK` before to `Ran 74 tests ... OK` after (RFC-003 file: 13 tests before the round, 14 after).
- FILES CHANGED this round: `tests/test_commands.py`, `RFCs/RFC-003-Add-Done-Remove.md`, `RFCS.md`. `td` unchanged. Commit: `/implement-rfc RFC-003 (fix round)`.

### Future

`done` and `rm` share `_find`; RFC-004 (`clear`) needs no id parsing. The lock for concurrent runs is RFC-006's: `main` now holds `data_lock` around the load and the handler for `add`, `done` and `rm`, and these handlers are unchanged (RFCS.md Open conflict 1 is closed).
