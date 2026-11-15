# Cold read: RFC-004 (td clear)

Question: what would I have to guess to implement this?

## 1. Guesses that change observable behavior or a shared interface

1. The `COMMANDS` registry (Technical approach) is defined in RFC-002, and the load and save functions and data model come from RFC-001. I was given neither. I have to guess the handler signature (args in? returns exit code per ARCH-2?), how the registry maps names to handlers, and the names of the load and save functions. Other code depends on all of these.
2. Data file key names. DATA-1 says "exact key names are for the RFC", and RFC-004 never states them. "keep tasks where `done` is false" assumes the field is literally `done` and holds a real boolean. DATA-2 says "boolean done state" without naming the key. I would also guess how a wrong-typed `done` (such as `0` or `"false"`) is treated. It could count as open, or it could be a corrupt-file error.
3. The `td list` line format. Criterion 1 writes `2 [ ] ...`, which implies "id, space, marker, space, text". PRD Open Question 5, FEATURES F7 and RULES Open Question 4 all say the line format is unsettled and that "the RFC must give one worked example per command". No worked example is given here. The criterion also depends on RFC-002's format.
4. Whether `clear` is built at all. The RFC says "build it only if time allows", yet it carries six acceptance criteria and a complexity rating. I cannot tell whether the criteria are mandatory. If it is skipped, `td clear` is an unknown command (exit 2), and nothing says so. Open Question 2 repeats the optionality without resolving it.
5. Extra-argument handling in `clear`. Criterion 4 says `td clear extra` exits 2. No rule covers positional arguments to a no-argument command. CLI-2 covers only `done` and `rm`, and F11 covers unknown commands and ids. Unspecified cases:
   - flags such as `td clear --help` or `-x`;
   - `td clear ""`;
   - whether the usage text goes to stderr only.
6. Precedence between errors. If the file is corrupt and the arguments are also bad (`td clear extra` with a corrupt file), is the result exit 1 or exit 2? Criteria 4 and 5 each assume the other condition is absent. SAFE-6 says validation runs before saving, but it does not say whether arguments are parsed before the file is loaded.
7. Criterion 5 inputs. "A corrupt data file" is only one variety here (presumably invalid JSON). TEST-3 requires invalid JSON, wrong types, a missing key, and a newer version. The RFC does not say whether all four are in scope for `clear` or what the message must contain. F4 requires "path and the parse error", while the criterion says only "names the path".
8. The `td clear` result when every task is done. This should save an empty list with `next_id` kept. Criterion 1 does not cover it, and "if nothing was removed" is ambiguous only if the file already had no tasks.
9. Exact stderr for a successful run. Criterion 1 requires empty stderr, so no "removed N" message and no warning. This is consistent with Open Question 1, but it deliberately differs from `add`, which echoes. That is an assumption, not a requirement. PRD Journey 5 gives no feedback.

## 2. Contradictions and inconsistencies

1. The RFC is optional ("v1 ships without it") while RULES NAME-2 and CLI-6 say "if built". FEATURES F10 is "Should", and the PRD calls it should-have. The RFC's "Complexity: Low" and mandatory-sounding criteria sit awkwardly with that status.
2. The RFC's Rules header omits rules the criteria depend on:
   - DATA-7 (missing file is not created, criterion 3);
   - SAFE-3 and DATA-6 (corrupt file, criterion 5);
   - OUT-7 (single catch point for `td:` messages);
   - SAFE-1 (single save function);
   - TEST-8 (tests use a temp `TD_FILE`).
   It cites TEST-3, which requires four corrupt-file variants and tests every command, but criterion 5 covers only one.
3. Criterion 2 cites DATA-4, but DATA-4 covers only `rm` and completing a task. `clear` is not mentioned. DATA-3 and F5 are the relevant ones.
4. Criterion 4 cites F11, but F11 does not define extra arguments for a no-argument command. The nearest rule is CLI-2, for `done` and `rm`.
5. Criterion 1 expects `td list` to show `2 [ ] ...`. That is right for F7, but the format is still an "open question" in the PRD and FEATURES. The RFC is the document that was supposed to settle it.
6. Open Question 1 repeats the PRD without conflict. The "exit 0 and empty stdout and stderr" claim in criterion 1 is consistent with OUT-1.
7. The RFC says "return without saving" when nothing was removed. F10 and CLI-6 say "changes nothing", and criterion 3 requires bytes unchanged. These agree. However, the "no done tasks" case is checked after a successful load, so a file that is valid but formatted differently on disk must not be rewritten. That is correct, but unstated.

## 3. Criteria a test cannot check, or that pass by luck

1. Criterion 2, "an id higher than any id ever issued". A test cannot know what was "ever issued" except from the fixture. An implementation that jumped to `max+100`, or one that computes `max(id)+1`, would pass if the removed task was not the highest, because the scenario is not pinned. The setup is not stated. The test needs a concrete setup, for example tasks 1 (open) and 2 (done) with `next_id` 3, then `clear`, then `add` giving exactly 3. As written, "higher than" passes by luck on wrong implementations, such as one that bumps the counter, or one that sets `next_id = max+1`, when the removed task is not the last. The criterion also says "after `td clear` has removed the highest-numbered task" without saying a specific next id is required (DATA-3 says it comes from the counter).
2. Criterion 6 tests the tests: "at least one success and one failure test". It is a process criterion, not behavior. It is checkable only by counting test functions. It does not say which failure (extra argument, corrupt file, or both).
3. Criterion 3, "byte for byte unchanged". It is checkable, but only if the fixture is not already in canonical form. If the fixture matches what the save function would write, a buggy always-save implementation still passes. The test must use a non-canonical but valid fixture (for example different indentation) or check the mtime or inode.
4. Criterion 3, "with no data file ... does not create one". It passes if the directory is empty, but a test also needs to rule out a stray temp file left behind.
5. Criterion 1, "empty stdout and stderr", combined with `td list` "shows only `2 [ ] ...`". The `...` is unspecified text, so an exact-match assertion needs the format from RFC-002.
6. Criterion 4, "nothing on stdout, file unchanged". It does not require anything on stderr. A silent exit 2 would pass, although F11 requires a message on stderr.
7. Criterion 5, "names the path on stderr". It is checkable, but "exits 1" with the other rules (OUT-7 prefix `td:`, parse error text) is unspecified, so any message containing the path passes.
8. No criterion covers the crash-safety of the single save (TEST-2), the `TD_FILE` handling, or a failed save leaving the file intact. These are delegated implicitly to RFC-001 without saying so.
