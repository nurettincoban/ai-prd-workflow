# Review: RFC-004 `td clear`

Reviewer context: fresh session, did not write the code. Commit reviewed: `34df97d /implement-rfc RFC-004`. Files changed per Implementation Notes: `td`, the RFC file, `RFCS.md`, `tests/test_clear.py`. The commit matches that list.

## Round 1 -- 2026-11-15

**Overall verdict: PASS with non-blocking findings. Overall risk: Low. Status set: Reviewed.**

Product type (PRD.md): CLI. Applied: command and flag design, exit codes, stdout/stderr separation, scripting, environment handling. Skipped: UI, accessibility, SEO, sessions, auth, scalability, caching (PRD records them as skipped; plain-text single-user tool). Security reduced to input validation and no shell/eval.

Open conflicts in RFCS.md: 1 (no lock) is not RFC-004's to fix; 2 and 5 followed as written; 8 (RFC-004's Features line omits F4 and F11, which criteria 5 and 6 cite) was followed (tests follow the criteria) and still needs the RFC header corrected. 10 (`clear` built without the user's decision) stands: it is a Should-have built from IDEA.md; the user may still ask to remove it. No new conflicts. Predecessors RFC-001 and RFC-002 are Reviewed.

### Step 0: run it

No build step (single Python file `td`).

```
$ python3 -m unittest discover tests
..........................................................
Ran 58 tests in 0.782s

OK
```

Hand runs of `./td` with a temporary `TD_FILE`: add a, b, c; done 1; done 3; `clear` -> silent, exit 0; `list` -> `2 [ ] b`; file has `next_id` 4; then `add d` -> `4 [ ] d` (id not reused); `clear` with nothing done -> exit 0, silent. `clear x`, `clear --bogus`, `clear ""` -> `td: unrecognized arguments: ...`, exit 2. Corrupt file: `clear` -> `td: <path>: invalid JSON: ...`, exit 1; `clear x` on the corrupt file -> exit 2. No data file: `clear` exits 0 and creates nothing. `clear -h` prints usage, exit 0.

Regression check (mutation; `td` restored after each, `git status` clean):

| Mutation | Suite result |
|---|---|
| `clear` saves even when nothing was removed | fails (caught, criterion 4) |
| `next_id` recomputed to max+1 after clearing | fails (caught, criteria 1 to 3) |
| `clear_done` keeps done tasks instead of open ones | fails (caught) |

### 1. RFC adherence -- PASS
All 6 criteria have a test in `tests/test_clear.py` (6 of 6, as TEST-STRATEGY.md RFC-004 plans). The handler is what the RFC describes: calls `clear_done`, saves once only when the count is above 0, returns `[]`, has no `ARGUMENTS` entry. No extra features. No deviations recorded and none found. Fixtures are non-canonical (4-space indent) as required.

### 2. Rules compliance -- PASS
Handler contract, `COMMANDS` registration, no new write path (DATA-7 honoured by skipping the save), single file (ARCH-1), no printing from the handler. Header comment updated.

### 3. Security -- PASS
Takes no input. No new file or process access.

### 4. Performance -- PASS
One pass over the task list; at most one save.

### 5. Maintainability -- PASS
Eleven lines of code, one docstring, tests are one per criterion. No dead code.

### Overall
**Overall Risk Level: Low.** The implementation matches the RFC, the tests fail when behavior regresses, and the edge cases (nothing to clear, no file, corrupt file, bad arguments) behave as specified.

**Blocking issues:** none.

**Improvement suggestions (non-blocking):**
- N1. `td --help` lists `clear     clear tasks`, which does not say that only done tasks are removed (`td` near the command table, the `help=` for `clear`). Wording is the implementer's choice per the RFC; "remove all done tasks" would be clearer.
- N2. The RFC's `**Features**` line should add F4 and F11 (RFCS.md Open conflict 8). Not changed here.
- N3. `td clear ""` reports `td: unrecognized arguments: ` with an empty tail, so the message does not show what was wrong. This comes from RFC-002's argparse error wrapper and meets the criterion (one `td:` line, exit 2).
- N4. Not verified: Python 3.10 and macOS (RFC-005).
