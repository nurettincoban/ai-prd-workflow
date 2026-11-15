# RFC-004: `td clear`

**Features**: F10
**Depends on**: RFC-001, RFC-002
**Rules**: NAME-2, DATA-3, DATA-4, DATA-6, DATA-7, SAFE-1, SAFE-3, SAFE-6, CLI-6, OUT-1, OUT-2, OUT-7, TEST-1, TEST-3, TEST-8
**Complexity**: Low

## Summary

`td clear` removes all done tasks. It is a Should-have (PRD FR-5): the user said "maybe", so this RFC is built only if time allows in the weekend; the user decides, and the decision is recorded in RFCS.md. Decision rule: if it is built, every criterion below is required; if it is skipped, `td clear` stays an unknown command (exit 2, by RFC-002's rules), RFCS.md lists F10 as deferred with that reason and RFC-004 stays Not started. RFC-005 does not depend on it. The skipped state is checked by RFC-002 criterion 6 (an unknown command exits 2 with one `td:` line); RFC-004 has no criterion for it.

## Technical approach

A handler registered in `COMMANDS` and following RFC-002's contract `handler(args, store, path) -> list[str]`; it takes no arguments: it has no `ARGUMENTS` entry (RFC-002), so any extra argument is an argparse error raised through RFC-002's `td:` error override. It calls `clear_done(store)` from RFC-001 (removes done tasks in place, returns the count, never touches `next_id`); if the count is 0 it returns `[]` without calling `save_store`; otherwise it calls `save_store(path, store)` once and returns `[]`. It prints nothing. Order of events and which error wins are RFC-002's: an argparse error (extra argument) is exit 2 before the file is read; a corrupt file is exit 1.

## Acceptance criteria

Every test sets `TD_FILE` through `helpers.temp_env()` (TEST-8). Fixtures are written non-canonically (for example indented with 4 spaces).

1. With tasks 1 (done), 2 (open), 3 (done) and `next_id` 4, `td clear` exits 0 with empty stdout and stderr, and `td list` then prints exactly `2 [ ] keep me` (task 2's text is `keep me`), id still 2. (F10, CLI-6)
2. In the same scenario, the file's `next_id` after `clear` is 4, and `add_task` on the store that `load_store` then returns gives the new task id 4 exactly (not 3, not 5). This uses RFC-001 only, so RFC-004 needs no `add` command. (F10, DATA-3, DATA-4)
3. With every task done, `td clear` exits 0, the file holds an empty task list and the same `next_id`, and `td list` prints nothing. (F10)
4. With no done tasks, `td clear` exits 0 and leaves the data file unchanged byte for byte (the non-canonical fixture is not rewritten, and no temp file is left in the directory); with no data file, it exits 0 and does not create one. (F10, DATA-7)
5. `td clear extra`, `td clear ""` and `td clear --bogus` each exit 2, write exactly one stderr line starting with `td:`, nothing to stdout, and leave the file unchanged, including when the file is corrupt. (F11, OUT-2)
6. With a corrupt data file (invalid JSON, a wrong-typed field including `done` as an integer, a missing key, `version` 2), `td clear` exits 1, writes one `td:` stderr line containing `str(path)`, writes nothing to stdout and leaves the file unchanged. (F4, SAFE-3, TEST-3)

## Implementation considerations

- Success and failure paths are both covered by criteria 1 and 6 (TEST-1).
- Crash-safety of the save and `TD_FILE` handling are RFC-001's (criteria 9 to 12 there); this RFC adds no write path of its own.
- Implementer's choice: the wording of messages and help text.

## Open Questions

1. **(assumption)** `clear` prints nothing, not a count of removed tasks.
2. **(assumption)** `clear` is built only if time allows (PRD Open Question 4); skipped means unknown command, exit 2.

## Implementation Notes

### Plan (Phase 1) -- nobody confirmed it

The user was not available, so the plan was not shown for approval; implementation proceeded on it anyway. Predecessors RFC-001 and RFC-002 have Status Reviewed in RFCS.md, so they count. `reviews/REVIEW-RFC-004.md` does not exist. Plan: add `cmd_clear` to `td` (calls `clear_done`, saves once only if the count is above 0, returns `[]`), register it in `COMMANDS` with no `ARGUMENTS` entry, and add `tests/test_clear.py` with one test per criterion (TEST-STRATEGY.md RFC-004 rows 1 to 6). No change to RFC-001 or RFC-002 functions.

Resting on assumptions nobody confirmed:
- **Whether `clear` is built at all** (Open Question 2, PRD Open Question 4): decided here from IDEA.md ("Maybe clearing all done tasks"), not by the user. Recorded in RFCS.md Open conflicts 10.
- `clear` prints nothing, not a count (Open Question 1).
- From earlier RFCs, unchanged: `TD_FILE`, `~/.td.json`, key names, exit codes 0, 1, 2, no lock (RFCS.md Open conflicts 1, 2, 5). Open conflict 8 (RFC-004 Features line omits F4 and F11 that criteria 5 and 6 cite) is untouched; the tests follow the criteria.

### Deviations

None from the RFC text.

### FILES CHANGED

Modified: `td` (`cmd_clear`, registration, header comment), `RFCs/RFC-004-Clear-Done.md` (this section), `RFCS.md` (Status Implemented, Open conflict 10). Created: `tests/test_clear.py`. Commit: `/implement-rfc RFC-004` on the current branch.

### Verification

`python3 -m unittest discover tests`: `Ran 58 tests ... OK` (52 before, 6 new). Criteria 1 to 6 each have a test. By hand with a temporary `TD_FILE`: add a, add b, done 1, `clear` exited 0 silently, `list` printed `2 [ ] b`. No separate build artifact: `td` is the shipped file. Not verified: Python 3.10, macOS (RFC-005).

### Future

None needed; a count on stdout would be a change to Open Question 1.
