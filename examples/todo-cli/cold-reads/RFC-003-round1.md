# Cold read: RFC-003 (td add, done, rm)

Question: what would I have to guess to implement this? RFC-001 and RFC-002 are not available, so everything they define counts as unknown.

## 1. Guesses that change observable behavior or an interface

1. Interfaces from other RFCs are not specified here. I would guess:
   - the signatures of `add_task`, `save_store`, `format_task` and `TdError`;
   - the shape of the `COMMANDS` table entry and of the handler (arguments and return);
   - whether `TdError` takes `exit_code` as a keyword with a default (the RFC says both "TdError with exit 1" and "`exit_code=2`").

   Approach: "use the already-loaded store" and "return lines to print" leave open who loads the store, whether `add_task` mutates it in place or returns a new one, and whether "lines" are strings with or without a trailing newline. If `add_task` also validates text, it is unclear whether that duplicates the handler's checks.
2. Order of load versus argument validation. The Approach says "validate arguments, use the already-loaded store", so the store is loaded before the handler runs. For `td done abc` or `td add ""` on a corrupt file, is the exit code 2 (usage) or 1 (corrupt)? Criteria 3 and 11 say 2, and criterion 12 says 1. Neither covers the combination.
3. Strip versus newline check. Approach: "strip leading and trailing whitespace. Empty result, or any `\n` or `\r` in the result" is rejected. Criterion 4 says a "text containing `\r`" exits 2. So `td add $'a\n'` is stripped to `a` and accepted. CLI-1 and F6 say text containing a newline is rejected. I would guess whether the check runs before or after the strip. The RFC picks "after", which contradicts CLI-1 and criterion 4 for a trailing or leading newline.
4. "Whitespace" is undefined. Python `str.strip()` also removes `\x0b`, `\x0c`, `\x1c` to `\x1f`, `\x85` and ` `. Whether those count as whitespace-only (criterion 3) or get stripped (criterion 2) is a guess. After the strip, `\t` and the other control characters (`\x1b` and so on) are stored but printed sanitized (OUT-4). The RFC does not say whether `add`'s printed line is the sanitized text, or whether `format_task` sanitizes.
5. Leading `-` in text and ids. `td add -x` or `td add buy -milk` is treated by argparse as an option, so it exits 2. `td add -- -x` is unspecified. The RFC says nothing about this, and the user loses tasks that start with `-`. Also `td done -1` only reaches the strict check if argparse treats `-1` as a positional. In the criterion 11 text it is listed as a usage error either way, so exit 2 is fine. How the message is worded and whether abbreviated flags (`--h`) are accepted are unspecified.
6. Leading zeros and huge ids. `td done 01` matches "one or more ASCII digits". Does it mean task 1 (int conversion) or an unknown id? On Python 3.11+, `int()` of a digit string over 4300 characters raises `ValueError`. That would give a traceback (OUT-7) or exit 1/2, unspecified. Criterion 10 only says `99` and `0`.
7. Output line format beyond the single example. `1 [ ] buy milk` is the only worked example. Id padding or alignment for ids of 10 or more (`10 [ ] x`) is not stated, and RFC-002 owns it. FEATURES and RULES left the format open and say the RFC must settle it, but this RFC only settles `add`'s line.
8. Does `td add` print the marker? PRD FR-1 and F6 say it prints "the id and text". The RFC prints `1 [ ] buy milk` (id, marker, text). I would treat this as an intentional but unrecorded deviation. Open Questions does not list it.
9. Does `done` on an already-done task save? CLI-3 says "leaves the file's task data unchanged", and criterion 8 only checks `td list`. Whether the file is rewritten (mtime, bytes) is a guess. PERF-1 and SAFE-6 are silent on it.
10. Locale. Criterion 5 says non-ASCII text "round-trips" and prints. OUT-6 says that under `LANG=C` it prints replacement characters. The criterion does not say which locale it holds under.
11. Error message contents. Criterion 10 requires "a message containing the id". Criterion 12 requires "the path". The wording, the `td:` prefix (OUT-7) and what is printed for argparse errors are not given. The id is shown as typed, which is a guess for `007`.

## 2. Contradictions

1. Strip versus reject: see 1.3 (Approach versus criterion 4, CLI-1, F6).
2. The header lists Features F6, F8, F9, F11, but criterion 6 cites F5 and criterion 12 cites F4, which are not listed. The Rules header omits rules the criteria depend on: SAFE-1/SAFE-3 (corrupt file, criterion 12), DATA-1/DATA-6, OUT-4, OUT-7, CLI-7.
3. ARCH-2 says `main` returns an int and no code calls `sys.exit` deep inside. Argparse errors (`td add` with no args, `td done` with no id, `td done 1 2`) call `sys.exit(2)` themselves. The RFC says only "(not from argparse)" for handler errors. Tests that call `main` directly must catch `SystemExit` for criteria 3 and 11, or RFC-002 must override the parser. Not stated here.
4. Approach says `add` "prints `format_task(new_task)`", while FEATURES F6 says "prints the id and text" and "exact line format is an open question". RULES Open Question 4 says the RFC must give one example per command; it gives one for `add` and none for `done` or `rm` (they print nothing, an assumption).
5. Approach says `nargs="+"` or `"*"` "with an empty list handled as a usage error", while criterion 3 requires exit 2 "writes to stderr". Both work, but with `+` argparse prints its own usage text and with `*` the handler's `TdError` does. The stderr wording differs. Only the exit code is testable.

## 3. Acceptance criteria a test cannot check, or that pass by luck

1. Criterion 13 ("each command has at least one success test and one failure test") describes the test suite and not the product. It passes trivially.
2. Criterion 12 points at "RFC-001 criterion 6", which is not in the folder, so the corrupt-file cases cannot be enumerated. It also requires the corrupt file to be tried with `add`, `done` and `rm`, but not with invalid arguments (see 1.2).
3. Criterion 10 requires a message "containing the id". For `0` or `99` this can pass by luck if the path or the message has a digit in it (a temp path often does). The check should be for the id as a separate token.
4. Criterion 8 compares `td list` output before and after. That passes even if the file is rewritten or the done flag is toggled twice in the file. It does not check file bytes (CLI-3 says "task data unchanged").
5. Criterion 2 ("leading or trailing whitespace stores the text stripped") gives no input or expected output, and neither the whitespace set nor whether it is per argument or after the join.
6. Criterion 5 ("100,000-character text is accepted and printed", "round-trips") gives no locale, no check that the printed line equals the full text, and no limit on control characters. A truncating implementation passes if only exit 0 is checked.
7. Criterion 6 is a good test, because max+1 gives 2, not 3. It does not cover a store emptied by `rm`: `rm` of every task, then `add`, must not give id 1.
8. Criteria 7 and 9 rely on RFC-002's `list` format (`[x]`). They are not testable on their own.
9. Criteria 1 and 3 say "stderr empty" or "writes to stderr" without a trailing-newline or exact-output rule. "nothing to stdout" is checkable, but exact stdout (`1 [ ] buy milk\n`) is not stated.
