# Review: RFC-003 `td add`, `td done`, `td rm`

Reviewer context: fresh session, did not write the code. Commit reviewed: `e3a3497 /implement-rfc RFC-003`. Files changed per Implementation Notes: `td`, the RFC file, `RFCS.md`, `tests/test_commands.py`. The commit matches that list.

## Round 1 -- 2026-11-15

**Overall verdict: PASS with non-blocking findings. Overall risk: Low. Status set: Reviewed.**

Product type (PRD.md): CLI. Applied: command and flag design, exit codes, stdout/stderr separation, scripting, encoding, environment handling. Skipped: UI, accessibility, SEO, sessions, auth, scalability, caching (PRD records them as skipped; plain-text single-user tool). Security reduced to input validation, terminal-escape sanitizing on output, and no shell/eval.

Open conflicts in RFCS.md: conflict 1 (no lock) means two overlapping `add` runs can lose a task; the code follows it (no lock) and it is not RFC-003's to fix. Conflict 2 (assumed names/formats), 5 (Ctrl-C) were followed as written. Conflict 8 does not touch RFC-003. No new conflicts found. Predecessors RFC-001 and RFC-002 are Reviewed. The Implementation Notes record no deviations; I found none that matter.

### Step 0: run it

No build step (single Python file `td`). Test run:

```
$ python3 -m unittest discover tests
....................................................
Ran 52 tests in 0.901s

OK
```

Hand runs of `./td` with a temporary `TD_FILE`: `add buy milk` -> `1 [ ] buy milk`, exit 0; `add -- -x` -> `2 [ ] -x`; `add "  "` -> `td: task text is empty`, exit 2; `add $'a\nb'` -> exit 2; `done 01` marks task 1, silent; `done 1` again silent, file unchanged; `rm 007` -> `td: no task with id 007`, exit 1; after `rm 2`, `add z` gets id 3; `done " 1"` and `done ٣` -> `td: invalid id: ...`, exit 2; `add $'a\tb\x1b[31m'` prints `a b [31m` (tab and ESC replaced) while the file keeps the raw text; `add $'\xff'` -> `td: task text is not valid UTF-8`, exit 2; `done` with 5000 nines -> exit 1, `no task with id <as typed>`; `add` with no args exit 2; `done 1 2` exit 2. Every result matches the RFC. Only Python 3.13 was available; 3.10 and macOS are RFC-005's.

Regression check (mutation): I changed `td` temporarily, ran the suite, and restored it (`git status` clean afterwards).

| Mutation | Suite result |
|---|---|
| `done` saves even when already done | fails (caught) |
| `rm` also raises `next_id` to max+1 (id reuse) | fails (caught) |
| `strip()` removed | fails (caught) |
| newline check drops `\r` | fails (caught) |
| `\d` instead of `[0-9]` in the id check | passes (not caught) |
| `lstrip("0")` removed before the length check | passes (not caught) |

### Acceptance criteria and tests

All 13 criteria have a test in `tests/test_commands.py`, as TEST-STRATEGY.md RFC-003 plans (13 of 13). The mutations above show criteria 3, 4, 6, 8, 9 would fail on regression. Two guards are not pinned (see N1, N2).

### 1. RFC adherence: PASS
All 13 criteria are met in behavior. Handler contract, `ARGUMENTS`, single `save_store` after validation, the `done`-already-done no-write rule, the 4000-digit cut-off (`MAX_ID_DIGITS`), id echoed as typed, and nothing printed by `done`/`rm` all match. No extra features. Deviations: none recorded, none found. The plan was not confirmed by the user; the notes say so openly.

### 2. Rules compliance: PASS
NAME-2 (only three commands), DATA-4 (`next_id` untouched by `rm`), SAFE-6 (validation before save), PERF-1 (one load, one save), CLI-3 (idempotent `done`), OUT-7 (`td:` one-line errors) hold. Comments say why. Tests use `helpers.temp_env()` (TEST-8).

### 3. Security: PASS
Ids are validated with an ASCII-only regex before `int`, with a length cap that avoids Python's int-conversion limit. Text is checked for newlines and encodability before it is stored. Control characters are stored raw and replaced on output, so a stored escape sequence cannot reach the terminal. No shell, eval or path built from user input.

### 4. Performance: PASS
One load and one save per command; `done` of a done task skips the write. Linear scans are fine for a single-user list.

### 5. Maintainability: PASS
Small handlers, one shared `_find`, no dead code. Tests are one method per criterion with subtests-like loops, as planned.

### Findings

**Blocking issues:** none.

**Non-blocking:**
- N1. No test pins ASCII-only ids. Replacing `[0-9]` with `\d` passes the suite, and then `td done ٣` would mark task 3 (since `int("٣")` is 3), against the RFC ("ASCII digits only"). Suggest adding `"٣"` to the bad-id list in `test_c11_bad_id` (`tests/test_commands.py`).
- N2. No test pins that leading zeros are dropped before the length check. With the `lstrip("0")` removed, `td done 000...0099` (5000 zeros then a real id 99) reports "no task with id" instead of marking task 99; criterion 10's over-long case only uses an id that does not exist. Suggest a test where task 99 exists.
- N3. The error for an over-long id echoes the whole id as typed (a 5000-character stderr line). This is what the RFC asks ("the id as typed"); noted only because it is long.
- N4. The tests call `main` in-process, so the real `./td` entry point (shebang, `sys.exit`) is covered only by my hand runs and, later, RFC-005.

### Overall

**Overall risk: Low.** The implementation satisfies all 13 criteria, follows RULES.md, and my hand runs found no behavior the RFC does not cover. Two guards are not caught by tests (N1, N2), which is worth a small test addition but does not block. Merge-ready.

### FEATURES.md

FEATURES.md has no Status column, so nothing to update there.
