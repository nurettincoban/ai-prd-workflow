# CHANGE-REQUEST-002: Outside review of `td` (BUG-REPORT-001)

Date: 2026-11-16. Requested by: the person running this example, relaying an outside reviewer's report (`changes/BUG-REPORT-001.md`). The user in IDEA.md has not seen it. Run non-interactively: nobody could be asked to accept or reject, so every change below is **Decision: pending** and no artifact other than this file, the Follow-ups in RFCS.md and the Status of two RFCs was edited.

## Summary

Six items. Two are bugs in Reviewed RFCs (the spec was right, the code or its test is wrong) and went to RFCS.md as blocking Follow-ups, with RFC-001 and RFC-002 set to Changes requested. Four are changes to what the product does, because the spec is silent or explicitly says otherwise; they wait here for the user. Item 3 is the one to read first: the specs as written produce a run that saves a task and then exits 1, which contradicts RULES.md SAFE-6.

| # | Item | Decision on what it is | Where it went |
|---|---|---|---|
| 1 | `td add ... -h` and a middle `--` | Change (Feature Modification of F6) | Change 1, pending |
| 2 | File mode after save | Change (Feature Modification of F3) | Change 2, pending |
| 3 | Exit 1 after the task is saved | Change (the specs themselves say exit 1) | Change 3, pending |
| 4 | fsync test does not check the flush | Bug in Reviewed RFC-001 (test gap) | Blocking Follow-up, RFC-001 Changes requested |
| 5 | Early Ctrl-C prints a traceback | Bug in Reviewed RFC-002 | Blocking Follow-up, RFC-002 Changes requested |
| 6 | `--help` does not name the data file | Change (Feature Modification, F1 and F12) | Change 4, pending |

## Why each item is a bug or a change

1. **Change.** RFC-003 says "How argparse treats other `-` forms (`-1`, `td add a -- b`) is argparse's rule on the running Python and is not pinned", and RFC-002 makes `-h` a help flag for every command. So the code does what the RFCs say; the RFCs never decided what a user who types `-h` or `--` inside a task means. Not a bug: nothing in a Reviewed RFC is contradicted. The reviewer's "gone without an error" is a fair product complaint, so it is a product decision.
2. **Change.** RFC-001 says the opposite in two places: "The file mode of an existing data file is not preserved across a save ... (assumption)" and criterion 5 (the mode follows the umask). SEC-3 only covers creation. The code matches the RFC, so this is a change that reverses an assumption.
3. **Change.** RFC-002 pins "a closed or missing stdout with output pending exits 1 with one `td:` line" (Open Question 3) and runs that write after the handler has saved (step 6 after step 5). RFC-003's `add` prints after saving. The code follows this; the `AttributeError` text is just what `sys.stdout is None` produces under the RFC's "unexpected error" wording. The contradiction is between RFC-002's assumption and RULES.md SAFE-6 / FEATURES F11 (a failed command changes nothing): the specs describe a command that fails and has changed the file. The fix is a decision about which one wins, not a code slip.
4. **Bug (test gap), RFC-001.** SAFE-1 and RFC-001's save algorithm say write, `flush()`, `fsync` the temp file, then `os.replace`; criteria 9 and 12 check order and kill points. The shipped `save_store` does call `flush()`; the reviewer's mutation shows the tests cannot tell. The spec is right and the verification is wrong.
5. **Bug, RFC-002.** OUT-7 ("never lets an uncaught Python exception reach the user as a traceback") and RFC-002's error path say Ctrl-C prints `td: interrupted` and exits 1. The `except KeyboardInterrupt` is inside `main`, so an interrupt before `main`'s `try` (during imports and module load) escapes. The spec is right, the code is not.
6. **Change.** RFC-002 leaves `--help` wording to the implementer and no rule says the help names the data file. Adding it is new behavior. Checked by running the suite on a scratch copy with the line added: RFC-001's `test_names_defined_once` (NAME-3) and RFC-005 criterion 9's `test_9_no_path_separators` fail, which is the reviewer's "two tests" (a third failure is the nested suite run repeating criterion 9).

## 1. Classification

| # | Change | Class | Size | Priority |
|---|---|---|---|---|
| 1 | Words after the first task word in `td add` are text, so `-h` and `--` mid-text are kept | Feature Modification (F6) | Small | Should have |
| 2 | A save keeps the mode of an existing data file; a data file the user cannot write is not replaced | Feature Modification (F3, F1) | Small | Should have |
| 3 | Once a mutating command has saved, a failure to write its output does not change the exit code | Technical Change (F11, F12, SAFE-6) | Small | Must have (G2, F11) |
| 4 | `td --help` says where the data lives | Feature Modification (F1, F12) | Small | Could have |

## 2. Impact analysis

### Conflict check

- **RULES.md.** Change 1: CLI-1 says arguments after `add` are joined; no violation, it sharpens it. Change 2: SEC-3 ("created with the default permissions; does not widen them with chmod") is not violated by preserving a mode, but its wording must say existing files keep their mode; SAFE-1 and SAFE-7 (one write path, no other deletes or renames) are unchanged; TEST-7 gains cases. Change 3: **reconciles SAFE-6 and F11 with RFC-002's assumption**; it needs one new rule (OUT-8, appended, IDs are append-only) and does not weaken OUT-5 (a broken pipe still exits 0) or OUT-7. Change 4: NAME-3 (the names appear as literals in one place only) and RFC-005 criterion 9 (no `/` in strings other than `DEFAULT_FILE`) both bind: the help line must be built from `ENV_VAR` and `DEFAULT_FILE`, not typed in.
- **Decisions and out-of-scope.** D-5 (errors to stderr, nonzero exit) is not reversed; change 3 narrows when "error" applies after a successful save. D-4 (never lose tasks) is served by 3 and, for privacy of the file, by 2. D-7 and the Won't list: none touched. PRD Open Questions 5 and 18 (output, closed stdout) are amended by change 3.
- **Differentiator.** "No risk of losing data" and "scripts" (G4): change 3 is what makes retrying scripts safe.
- **Earlier change requests.** CR-001 (lock): unaffected; change 3 touches the step after the lock is released? No: output is written while the lock is held (CR-001), so the rule must not delay the release; flagged for the RFC.

### Affected artifacts and RFCs

- Change 1: F6 criteria, CLI-1 sentence, RFC-003 criterion 4 and Technical approach (reverses "not pinned"), TEST-STRATEGY rows for RFC-003. RFC-003 is Reviewed, its criteria change: **Spec changed** when accepted.
- Change 2: F3 and F1 criteria, SEC-3 wording, RFC-001 criterion 5, its save algorithm line and Open Question 4 (reverses assumption 4), RFC-001 test rows. RFC-001 is already Changes requested through item 4, so it ends as Spec changed after acceptance, with both sets of edits in one fix round.
- Change 3: new rule OUT-8, PRD Open Question 18, F11 and F12 criteria, RFC-002 step 6 and Open Question 3 and criteria (new case: stdout closed on `list` still exits 1; on `add` it exits 0 with the task saved), RFC-003 criterion for `add`/`done`/`rm`, TEST-STRATEGY. RFC-002 and RFC-003 become Spec changed.
- Change 4: F12 (help names the data file), RFC-002 (help text pinned for this line, reversing "wording is the implementer's choice" for it), RFC-005 criterion 9 and RFC-001 NAME-3 test wording if the line is built by formatting. RFC-002 Spec changed.
- Code named, not edited: `build_parser`, `cmd_add` and argument declaration (1); `save_store` (2); `main` and `_write_lines` (3); `build_parser` description (4).

### Design the RFCs would pin (recommendations, all assumptions)

1. **(assumption)** `td add -h` and `td add --help` with nothing before them stay help. After the first text word, `-h`, `--help`, other flag-looking words and a `--` are text and are kept (`td add fix bug in -- parser` stores `fix bug in -- parser`). A first word that looks like a flag still needs `--` (RFC-003 criterion 4 stands).
2. **(assumption)** `save_store` copies the existing target's permission bits to the new file before the replace, and a new file still follows the umask. If the existing file has no write bit for the user, the command exits 1 with one `td:` line naming the path and the data is untouched, because a user who ran `chmod 444` asked for no changes (reading stays allowed; `list` works). The other option, writing anyway and keeping 444, is rejected below.
3. **(assumption)** After a successful save, a failure to write the output (closed stdout, `/dev/full`, `None`) is ignored for the exit code: exit 0, best-effort one `td:` line on stderr. Commands that save nothing (`list`) keep exit 1 for a closed stdout with output pending. A broken pipe stays exit 0, quiet.
4. **(assumption)** One line in the `--help` description: the data file is `DEFAULT_FILE` unless `ENV_VAR` is set, built from the two constants.

## 3. Implementation strategy

All four: **implemented now**, in the fix round of the affected RFCs (RFC-001, RFC-002, RFC-003), after the two blocking Follow-ups, which touch the same files. Order: RFC-001 (item 4 and change 2 together), RFC-002 (item 5, changes 3 and 4), RFC-003 (changes 1 and 3). Testing: change 1, add and list with `-h` and mid `--`; change 2, modes 600, 640, 444 before and after a save, and a new file under umask 022 and 077; change 3, a real subprocess with `>&-` and `>/dev/full` for `add`, `done`, `rm` (exit 0, task present, no duplicate on retry) and for `list` (exit 1); change 4, the help text, and the two scan tests still green.

## 4. Documentation updates

Listed under affected artifacts. No feature or rule is renumbered; OUT-8 is appended. No new RFC: every change fits an existing one. Nothing was edited for the changes yet.

## 5. Stakeholders

None (one person, no team).

## 6. Risks

| Risk | Mitigation |
|---|---|
| Change 1 makes `td add -h` ambiguous for a user who wanted help | Only a first-position `-h` is help; documented in the add help text |
| Change 2 refusing a read-only file surprises a user who relied on the old overwrite | It is exit 1 with a clear message; the choice is the user's, see Open Questions |
| Change 3 hides a failed write of the output | The task is saved, which is the thing the user asked for; stderr still says what failed when it can |
| Item 5 cannot fully fix the first milliseconds | Part of the window is before any line of `td` runs; see the Follow-up note |
| Not doing it | Scripts that retry on exit 1 double-add (3); private data files become world-readable (2) |

## Alternatives rejected

- **Change 2, write anyway and keep 444.** Honors the bits but defeats the user's intent; also writes through a "read-only" marker. Rejected, but equally valid; the user decides.
- **Change 3, check stdout before saving and fail early.** Cannot work for `/dev/full` (the write fails at flush) and would refuse valid runs where only the pipe closes later.
- **Change 3, keep exit 1 and make the save conditional on output.** Would mean writing before saving, which breaks SAFE-1's order and the atomicity.
- **Change 1, make `-h` text everywhere.** Breaks `td add -h` as help.
- **Item 4, treat as a change to F3.** The spec already requires the flush; only the test is missing.

## Bugs sent to RFCS.md

- **Item 4: RFC-001, blocking Follow-up.** Steps: in `save_store` delete `handle.flush()`; run `python3 -m unittest discover tests`; all 85 pass although fsync now runs on an empty temp file (a probe printed `size at fsync: 0`). Moving the fsync before the write also passes. Expected: the test that covers the fsync records the temp file's size (or reads it) when `os.fsync` is called and fails in both mutations.
- **Item 5: RFC-002, blocking Follow-up.** Steps: run `td` and send SIGINT 5 to 40 ms after start (for example a loop of `python3 td list & sleep 0.02; kill -INT $!`); 31 of 60 runs printed a traceback instead of `td: interrupted`. Expected: `td: interrupted`, exit 1, no traceback. Note for the implementer: an interrupt during interpreter startup, before the first line of `td` runs, cannot be caught by `td`; if the interrupt is still seen after the interrupt handling covers the whole of `td` (imports included, for example a handler installed on the first line, or a `main` wrapper in the `__main__` guard), do not reduce OUT-7 to fit: record it as an open question for the user.

## Open Questions

Assumptions made because nobody could be asked; `/implement-rfc` should put them in front of the user before code depends on them. Cited, not copied: the exit-code and `KeyboardInterrupt` assumption is RFCS.md Open conflict 5.

1. **Every classification above is an assumption** (bug versus change). If the user reads items 1, 2 or 6 as bugs, they go to RFCS.md as blocking Follow-ups instead; the code is the same.
2. **Change 1:** where "text starts" (first word) and that `td add -h` alone is help.
3. **Change 2:** a data file the user cannot write is refused with exit 1 rather than overwritten.
4. **Change 3:** exit 0 and a best-effort stderr line after a save with unwritable stdout.
5. **Change 4:** the exact help wording is the implementer's.
6. **Acceptance:** every change is pending; nobody has accepted or rejected any.

## Decisions

- **Change 1: Decision: pending.**
- **Change 2: Decision: pending.**
- **Change 3: Decision: pending.** Recommended to accept first: until it is decided, SAFE-6 and RFC-002 contradict each other for `add`, `done` and `rm` when stdout is closed.
- **Change 4: Decision: pending.**

Nothing has been applied to PRD.md (no Decisions entry), FEATURES.md, RULES.md, TEST-STRATEGY.md, or the criteria of RFC-002, RFC-003 and RFC-005. When the user answers, record each decision here and in PRD.md Decisions, make the edits listed under section 4, and set RFC-001, RFC-002 and RFC-003 to Spec changed (with a note under `## Implementation Notes`) for each accepted change that alters their criteria.
