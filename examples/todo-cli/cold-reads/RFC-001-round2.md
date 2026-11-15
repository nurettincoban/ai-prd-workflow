# Cold read: RFC-001 Storage core

## 1. Guesses that change behavior or a shared interface

1. Parent-directory check with a symlinked data file. Section "load_store ... Order of checks": "(1) the parent directory must exist and be a directory". The RFC does not say whether this is the parent of `path` as passed or of `realpath(path)`. `save_store` creates its temp file in the parent of the resolved target (SAFE-4). If `TD_FILE` is a symlink in an existing directory that points into a missing directory, I would have to guess three things.
   - Whether `load_store` reports an error or returns the empty store (a dangling link looks like a "missing file").
   - Whether `save_store` fails at the parent check or later at `os.open`.
   - Which path the message names.
   Criterion 11 covers symlinks that resolve, not dangling ones.
2. Which exceptions `save_store` converts. "Any `OSError` raised before or by `os.replace` becomes `TdError`" and "Only `OSError` from step 3 is skipped". A non-`OSError` raised before or by `os.replace` is never stated. Criterion 9 injects "exceptions in-process" without saying what type. I would assume non-`OSError` propagates unchanged, but a test of "same expectations" could expect either.
3. A failure in `save_store` after the new file is in place. Step 3 non-`OSError` propagates, so the caller sees an exception although the new store is on disk. Criterion 9 expects the new store, which agrees. The RFC does not say whether the in-memory store or the caller's exit code is affected, and RFC-002 must not guess.
4. What `save_store` validates beyond the content rules. "it runs the same validation on the store it is given". `<path>` in the message is `str(path)`. It is not stated whether the parent-directory check also runs before validation. Criterion 3 (missing parent) and criterion 13 (invalid store) never combine, so the precedence between the two errors is a guess.
5. Which key a duplicate-id or `next_id <= max id` error names. Criterion 6 says "for the structure cases the message also contains the name of the offending key". Several listed cases have no obvious key.
   - A JSON array, an empty file and duplicate ids have none or several candidates. Duplicate ids would have to name `id`.
   - It is not stated which cases count as "structure cases".

## 2. Contradictions and inconsistencies

1. The Rules header lists STACK-1 and STACK-2 but not STACK-4 (unittest only). Criterion 15 cites STACK-4 and requires `unittest discover`. Criterion 14 cites F11 and criterion 15 cites F11-adjacent tests, but the Features header omits F11. Traceability is incomplete. Behavior is unaffected.
2. The CLI-7 rule "TD_FILE is read once, at startup" conflicts with "`resolve_path()` ... reads the environment on every call and keeps no cache". The RFC reconciles this by saying `main` calls it once. This is only safe if RFC-002 follows that. Nothing in this RFC can test "once". Criterion 1 does not test it, so CLI-7 is not checked here.

## 3. Criteria a test cannot check, or that pass by luck

1. Criterion 6, "the message also contains the name of the offending key". The key names `id`, `text` and `done` are short substrings that appear in ordinary words. `id` is in "invalid". `str(path)` is also in the message and can contain them. A test using `assertIn("id", msg)` passes for any message starting with "<path>: invalid". The criterion needs the exact expected wording or a quoted-key match, for example `'id'`.
2. Criterion 8, "After removing every task, `add_task` does not return 1". This passes for any id other than 1. State the expected id (it should equal the stored `next_id`).
3. Criterion 9, "wrappers installed around `os.fsync` ... before the temp file's fsync ... after `os.replace` before the directory fsync". Both fsyncs go through `os.fsync`, and the temp file and the directory are both opened with `os.open`. The criterion does not say how the wrapper tells them apart (fd comparison, call count, flags). If the implementer's call count differs from the test's, the kill lands at the wrong point and the test passes for the wrong reason. The same applies to criterion 12, "or opening the directory raises OSError". The criterion does not say how the wrapper recognises the directory open.
4. Criterion 9, "temp data partly written" for kill point 1. The pseudocode flushes before the fsync, so the data is not partly written. Whether it is partial depends on the implementation, and a test cannot force it. The point only shows that a leftover temp file is ignored.
5. Criterion 10, "A temp file left by a killed child does not affect `load_store`". `load_store` never reads other files, so this passes by construction. It does not test SAFE-5 cleanup. The temp name is the implementer's choice and no pattern is pinned, so "no temp file remains" can only be checked as a directory listing before and after. That check works, but only if the test directory holds nothing else.
6. Criterion 15, "every test in the suite uses it, so no test touches the real home directory". A test cannot assert this about itself. It needs a meta-check, for example a guard that fails if `~/.td.json` is touched or a scan of the test sources.
7. Criterion 5, mode checks, "with umask 022 the new file's mode is 0644 and with umask 077 it is 0600". This is fine on POSIX. The criterion does not say whether to skip it on Windows (F15 says Windows is untested), so it is not stated how it is skipped.
