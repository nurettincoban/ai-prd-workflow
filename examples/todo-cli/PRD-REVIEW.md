# PRD Review: td

Product type: CLI (see Product Type section in PRD.md). Run non-interactively; nobody could be asked, so every gap that needs the user is recorded in Open Questions marked (assumption). No new entries were added to Decisions: no user answers were available, and none of the fixes settle a choice the PRD's text had not already made.

## Overall assessment

The PRD is faithful to IDEA.md, correctly scoped and honest about its assumptions. Its main weakness is that the headline promise, never lose a task, is stated but not carried all the way through: concurrent runs, power-loss durability and id reuse each leave a way to lose or corrupt a task. Remaining gaps are small edge cases in input handling and output.

## Step 0: grounding

- No existing implementation, prototype or "extracted from" source is named (IDEA.md mentions none), so there was nothing to diff. Open Question 7 stays.
- Technology claims checked from knowledge of Python, not by running anything: `os.replace` is atomic on POSIX and on Windows within one volume, so the NFR-1 approach works; it is not durable across power loss without fsync (F-3); `argparse` exits 2 on usage errors, which matches the exit-code assumption.
- Unverified: that the target machines have `python3` on PATH at 3.10+; that fsync of a directory is possible on every supported platform (works on macOS and Linux; not on Windows); behavior under non-UTF-8 locales (F-8). No claim was tested by running code, as there is no code yet.

## Findings

| ID | Impact | Finding | PRD change |
|---|---|---|---|
| F-1 | High | G2/D-4 say tasks are never lost, but Open Question 9 accepts last-writer-wins: two overlapping writes (two terminals) silently drop a task. Contradiction; only the user can say if a lock is wanted. | Open Question 9 rewritten, still an assumption. No requirement added. |
| F-2 | High | FR-6 says ids are never reused, but nothing says where that is remembered. Max id plus one reuses the id of a removed last task. The file must hold a next-id counter. | FR-6 now says so. Follows from FR-6's own text. |
| F-3 | High | NFR-1 promises survival of power loss, but its example (write, flush, replace) does not guarantee it; without fsync the replace can persist with empty content. | NFR-1 example now includes fsync of the file and, where possible, the directory. |
| F-4 | Medium | NFR-4 (one task per line, no escapes) is broken by task text containing newlines or ANSI escapes. | Open Question 13 |
| F-5 | Medium | NFR-2 leaves a corrupt file untouched, so recovery means editing the file by hand, which the success metric says should never happen. | Open Question 14 |
| F-6 | Medium | Behavior for non-integer, negative or multiple ids is unspecified; not-found vs usage error exit codes only partly assumed. | Open Question 15 |
| F-7 | Medium | Environment variable edge cases: empty value, `~`, relative path, missing parent directory, symlinked target (atomic replace replaces the symlink). | Open Question 16 |
| F-8 | Medium | NFR-9 covers storage only; stdout under a non-UTF-8 locale can crash on non-ASCII text. | Open Question 17 |
| F-9 | Medium | Install and upgrade are not defined, yet the release check "works on macOS and Linux" needs them; file format compatibility across versions is not mentioned. | Open Question 8 extended |
| F-10 | Medium | Closing the pipe early (`| head`, `grep -q`) makes Python print a BrokenPipeError traceback; piping is a core goal (G4). | Open Question 18 |
| F-11 | Low | Priorities use only Must and Should; Could and Won't are not labelled (the out-of-scope list is the Won't). FR-5 is listed after FR-6. IDs are fine and unchanged. | None; harmless, and renumbering is forbidden. |
| F-12 | Low | G4 says "meaningful exit codes" while NFR-5 only fixes zero vs non-zero; line formats and list order are open (Open Questions 5, 6). Requirements have no concrete example outputs, so no acceptance test can be written for `td list`. | None; already open, to be settled before RFC. |
| F-13 | Low | Open Question 12 lacked the assumption tag. D-3's "Rejected: SQLite, multiple files, a config file" lists alternatives the user never named; they are the PRD author's own, not user decisions. | Open Question 12 tagged. D-3 left as is. |

Counts: High 3, Medium 7, Low 3 (13 total).

## Recommendations

1. Ask the user one question before RFCs: do overlapping `td` runs need a lock (F-1)? If yes, add a requirement and a portability note; if no, change G2's wording to say "never lose tasks to a crash" so the PRD stops contradicting itself.
2. Fix the data file schema early in the RFC: a version number, a next-id counter and the task list (F-2, F-9).
3. Give each command one worked example of stdout, stderr and exit code, for instance `td add "x"` printing `1  x`, so FR-1 to FR-4 become testable (F-12).
4. Decide the newline and control-character rule and the error message wording for a corrupt file (F-4, F-5).
5. Add tests for: kill during save, corrupt file untouched, id not reused after removing the last task, closed stdout, non-UTF-8 locale.

## Scores (1-10)

- Completeness: 7. Core behavior and non-functionals are covered; durability, concurrency and edge cases were thin.
- Clarity: 8. Short, with consistent IDs and visible assumptions.
- Feasibility: 9. Standard library only, small scope, a weekend is realistic.
- User-Focus: 9. Directly reflects the stated user and constraints.

## Self-check

- Recounted the findings table: 3 High, 7 Medium, 3 Low = 13.
- Cross-references: every F-ID cited in PRD.md (F-1 to F-10, F-13) exists here and points at the matching finding; FR-5 to FR-9 and NFR-1 to NFR-9 are unchanged and unrenumbered.
- Ran `trace-check.py` on the project before and after the edits: 0 failures, 0 warnings (18 requirements; no features or RFCs exist yet, so coverage checks have nothing to test).
