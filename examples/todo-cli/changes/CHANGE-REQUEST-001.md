# CHANGE-REQUEST-001: Lock so overlapping runs never lose a task

Date: 2026-11-15. Requested by: the person running this example (the user in IDEA.md is not available). Input: "Overlapping `td` runs must never lose a task. Add a lock so that concurrent `add`, `done`, `rm` and `clear` runs on the same data file serialize, and resolve RFCS.md Open conflict 1 (goal G2 against no locking) in favour of G2." Reviews of RFC-001 and RFC-003 (round 2) are blocked on that conflict.

## Summary

One change: add a lock. It reverses an assumption (PRD Open Question 9, FEATURES F17, RULES DEV-3: no lock), not a user decision, and settles the High finding F-1 of PRD-REVIEW.md. Recommended: accept. It costs one new RFC and edits to five documents; it changes no existing acceptance criterion, so no implemented RFC loses its Reviewed or Implemented status.

## 1. Classification

| # | Change | Class | Size | Priority |
|---|---|---|---|---|
| 1 | Lock around the read-modify-write of `add`, `done`, `rm`, `clear` | Technical Change that adds a requirement (FEATURES F17 moves from Won't to Must) | Small to medium | Must have (G2) |

## 2. Impact analysis

### Conflict check

- **RULES.md.** Violates DEV-3 ("nothing in v1 adds ... locking; a change that adds one needs a PRD change first"). That is the rule's own exit: this change is the PRD change. DEV-3 is edited to drop "locking". Also touches SAFE-1 (every write goes through one function): unchanged, the lock wraps the load-and-save, it adds no second write path. PERF-1 (read once, save once): unchanged. STACK-1 and STACK-3: `fcntl` is standard library and makes no network call. PERF-2 (no background threads, no caches written to disk): a lock held by an open descriptor creates no thread and writes nothing, so it holds; RFC-005 criterion 2 bans `threading`, which this does not use.
- **Decisions and out-of-scope.** PRD.md Decisions: D-4 ("never lose tasks") is served, not reversed. D-6 (single user, single machine) is not contradicted: two terminals of one user on one machine is the case. The out-of-scope list has no "locking". PRD Open Question 9 and FEATURES F17 recorded "no lock" as an **(assumption)** because nobody could be asked; the original rationale was "a lock adds a requirement and a non-portable dependency on `fcntl`/`msvcrt`". That rationale does not hold against G2: the dependency is small and standard library, and the alternative is a tool whose headline promise is false for two terminals. PRD-REVIEW.md F-1 asked exactly this question.
- **Differentiator.** The value proposition says "no risk of losing data". Without the lock it is false; with it, it is true on macOS and Linux.
- **Earlier change requests.** None (`changes/` did not exist).

### Affected artifacts and RFCs

- PRD.md: Scope, a new NFR-10, Decisions D-9, Open Question 9 (settled) and Open Questions 19 and 20 (new assumptions), a user journey. G2 is not reworded (it already says "never lose tasks").
- FEATURES.md: F17 becomes a Must and moves to "Storage and data safety"; counts and the requirement coverage table follow.
- RULES.md: DEV-3 loses "locking"; a new SAFE-8 states the lock rule (IDs are append-only, so it is appended to the SAFE category).
- RFCS.md: new RFC-006; Open conflict 1 closed; index, graph, coverage and finding F-1 lines updated.
- TEST-STRATEGY.md: new RFC-006 section; "Gaps" item 4 closed; totals.
- RFC-001: its "Lock-free by decision" note is now wrong and is replaced by a pointer to RFC-006. No criterion changes.
- RFC-002: its "order of events" in `main` gains one step for mutating commands, owned by RFC-006. No criterion changes (`list` takes no lock; criterion 14 counts for `list` are unchanged).
- RFC-003 and RFC-004: no text change. Their criteria hold as written (each command still loads once and saves once, and the data file and directory listing are unchanged because the lock creates no file, see the design below). Their code is not edited.
- RFC-005: no change. `fcntl` is in `sys.stdlib_module_names` (criterion 1), is not on criterion 2's ban list, and the import is guarded so a platform without it still imports `td`.
- Code (named, not edited here): `main` in `td` (the new step), a new lock helper. `/implement-rfc RFC-006` writes it.

### Design the RFC will pin

- Lock the **directory** that holds the data file (the directory of `os.path.realpath` of the path, the same one `save_store` writes into) with `fcntl.flock`, exclusive, blocking. The data file cannot be the lock target because every save replaces it, so a second run would lock the old inode. A separate `.lock` file would sit beside the data file and break RFC-004 criterion 4 (`os.listdir` equals `["tasks.json"]`) and RFC-001's exact directory listings, and would never be safe to delete. A directory descriptor leaves nothing behind and the OS drops the lock if the process is killed, so a crashed run never leaves a stuck lock. Cost: two data files in one directory share a lock, which only makes them wait for each other.
- Held from before `load_store` until after the save and the output are written: the whole read-modify-write, for the four commands only. `list` takes no lock: a save is an atomic replace, so a read sees the old file or the new file.
- Wait at most 10 seconds, then exit 1 with one `td:` line naming the data file: an interrupted process or a stuck holder must not hang the next run forever. (assumption)
- Without `fcntl` (Windows): no lock, and `td` still runs. Windows is best effort and untested (PRD D-8, NFR-6), so the guarantee is stated for macOS and Linux. (assumption)

## 3. Implementation strategy

**Implemented now**, as a new RFC-006 (next unused number), after RFC-001 to RFC-003 are Reviewed (they are Changes requested today, so `/implement-rfc RFC-006` must wait for them). Refactoring of finished code: none beyond the one added step in `main`. Testing: a two-process test that starts overlapping `add` runs on one data file and checks every task is present with distinct ids; the same for each of `done`, `rm` and `clear` against a concurrent `add`; a test that holds the lock from a helper process and checks the wait, the timeout message and the exit code; a kill test that the lock is released when the holder is killed; a check that `list` does not wait.

## 4. Documentation updates

Listed above under affected artifacts. Feature and rule IDs: none renumbered; F17 keeps its ID and changes priority, SAFE-8 is new.

## 6. Risks

| Risk | Mitigation |
|---|---|
| A run waits on a stuck holder | 10 second limit and a clear error; the OS releases the lock when the holder dies |
| Overlap tests are flaky | Use a helper process that holds the lock and signals through a pipe, not timing races, for the deterministic cases; use many parallel `add` runs only as a stress check |
| Directory lock on a network filesystem may not be honoured | Out of scope: one machine, local disk (PRD D-6) |
| No lock on Windows | Stated; Windows is best effort (D-8) |
| Not doing it | The headline promise of the product is false for two terminals |

## Alternatives rejected

- **Reword G2 to "never lose tasks to a crash".** Safe to write, but it weakens a goal the user stated ("never lose my tasks") to fit the code, which is the drift this process exists to stop. It was the other option offered; the person running the example chose the lock.
- **Optimistic concurrency: re-read the file at save time and fail if it changed.** Needs no OS lock but turns a lost task into a failed command the user must retry, and still has a window between the check and the replace.
- **Lock the data file or a `.lock` file beside it.** Rejected for the reasons under Design.
- **A `msvcrt` fallback for Windows.** Untestable here (D-8); not built.

## Decisions

- **Change 1: Decision: ACCEPTED**, 2026-11-15, by the person running this example, on the user's behalf, as the safer of the two options. **Not accepted by the user in IDEA.md**, who was not available; the user has not seen it. If the user later prefers the other option (reword G2 to "never lose tasks to a crash"), reverse D-9, set F17 back to Won't, and retire RFC-006 and SAFE-8 (mark them [REMOVED], do not renumber).
- What changed, why, what it replaced: see PRD.md D-9. It replaced the assumption "atomic replace only, last writer wins" (PRD Open Question 9, F17, DEV-3).
