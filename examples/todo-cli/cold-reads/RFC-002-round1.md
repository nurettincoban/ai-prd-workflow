# Cold read: RFC-002 (CLI framework, output rules, `td list`)

Question: what would I have to guess to implement this with no one to ask?
Files read: PRD.md, FEATURES.md, RULES.md, RFC-002-CLI-Framework-and-List.md. RFC-001 is not available.

## 1. Guesses that change observable behavior or an interface other code depends on

1. **Who loads the store, and what a handler receives.** "Dispatch: ... load the store once (PERF-1); run the handler" and "a handler takes `(args, path)`" cannot both be right. If dispatch loads the store, the handler has no way to receive it. If the handler loads it, dispatch loading as well is a second read, which breaks PERF-1. RFC-003 and RFC-004 will code against this signature, so a wrong guess breaks them.
2. **Everything borrowed from RFC-001 is only a name.** I would have to guess:
   - the signature and return value of `load_store`;
   - the store's shape and the task keys (DATA-1 leaves the key names "for the RFC");
   - the constructor of `TdError` and the name of its exit-code attribute, including its default;
   - how `path` is produced (a `str` or a `Path`, resolved or not);
   - which function checks the missing parent directory.
   The worked example gives task text and ids but not the on-disk JSON, so I cannot even write a fixture file for criteria 2, 3, 7 and 10.
3. **Handler return format.** "Returns the text to print (a list of lines)" does not say whether the lines carry a trailing `\n` or whether `main` adds one. Nor does it say whether the output ends with a final newline. Criterion 2 says "exactly the two lines", so this matters for exactness and for `td | grep`. An empty list must print nothing, not a blank line.
4. **`--help`/`-h`.** The RFC converts `SystemExit(2)` into a returned 2. `--help` raises `SystemExit(0)` and writes usage to stdout. I would guess that `main` returns `e.code` as is. The RFC does not say, and it does not say whether this conflicts with "no failed command writes to stdout".
5. **Exit codes of `TdError` for usage-style errors.** CLI-1 and CLI-2 (RFC-003/004) need exit 2 from a handler. The RFC says `TdError` "returns its exit code" but never says that codes 1 and 2 are both allowed, or what the default is. OUT-2 says "no other exit code".
6. **`KeyboardInterrupt` and other `BaseException`s.** The RFC catches `Exception` only. OUT-7 says "never lets an uncaught Python exception reach the user as a traceback", and Ctrl-C would. A clean exit would need a code other than 0, 1 or 2, which OUT-2 forbids. I would have to guess.
7. **Where the output setup sits relative to the single error path.** If `sys.stdout.reconfigure` fails, for example when stdout is closed (`td list >&-`, so `sys.stdout` is `None`), it fails before or outside the try block. The result is a traceback or a crash with an unspecified exit code.
8. **Write errors other than `BrokenPipeError`.** Examples are `ENOSPC` and `EBADF`. They fall into "unexpected error" only if the writing happens inside the try. The RFC does not say, and does not say where the flush happens. With `head -1`, `BrokenPipeError` may only surface at interpreter shutdown flush, after `main` has returned 0. The "return 0 with no message" rule then does not control the exit status unless `main` flushes explicitly inside its try. I would guess that it does.
9. **Message content.**
   - "`td: <message>`" gives no wording.
   - Criterion 7 requires the corrupt-file message to name the path. Criterion 8 only says "same stderr format", while CLI-7 says the path is in the message. I would guess that the path is required in both.
   - "Unexpected error ... `<type>`" does not say whether type means `__name__` or the qualified name.
   - It is also unclear whether a multi-line exception message gets flattened. Criterion 9 requires "single-line", but `str(exc)` can contain `\n`. Paths or JSON error text can hold control characters that `format_task` does not sanitize on the stderr path.
10. **Which load failures count as "expected".** Criterion 8 says "any other expected reason (missing parent directory...)". Not specified: the data path is a directory, permission denied, or invalid UTF-8 bytes (`UnicodeDecodeError`). Are these corrupt-file errors, expected errors, or the "unexpected error" path? The exit code is 1 either way, but stderr differs. Criterion 7 and 8 stderr requirements differ from the unexpected-error format.
11. **Missing-file vs missing-parent for `list`.** F2 and criterion 4 say a missing file is an empty list and exit 0. Criterion 8 says a missing parent directory is exit 1 even for read-only `list`. I would guess that this is checked on read; the RFC never states it.
12. **Duplicate or non-ascending stored ids** (criterion 3). It is not said whether unsorted storage is valid, whether duplicate ids are an error, or what the sort tie-break is.
13. **Argparse behavior that is visible to users.**
    - `allow_abbrev` is not specified. NAME-2 says "no abbreviations", so `td list --he` and `td l` need pinning.
    - "extra arguments to `list`" is clear, but `td --bogus` and `td 5` (bare command with junk) are not covered.
    - RFC-002 registers only `list`, so `td --help` or usage text lists one command. Whether the later RFCs' commands appear in help is not addressed.
14. **Control-character set.** "Category `Cc`" leaves U+2028, U+2029 (Zl, Zp) and bidi or format characters (Cf) untouched. These can still break "one line per task" for consumers that use `str.splitlines()` or a terminal that honors them. See 3.8.
15. **Test injection point for criterion 9.** "Injected in a test" is only possible if the test can replace a handler. The RFC says the shape of `COMMANDS` is the implementer's choice, so the injection point is a guess. It may be that the test patches `COMMANDS["list"]`, or `load_store`, or something in argparse.

## 2. Contradictions

1. **Criterion 13 and OUT-7 against criterion 6 and the argparse default.** Argparse writes `usage: ...` and `td list: error: ...` (or `td: error:` for the top-level parser). Neither starts with `td:`; the subparser form starts with `td ` and a space, not `td:`. Criterion 13 says "Every error line on stderr starts with `td:`". The RFC also says usage and help wording is the implementer's choice (Implementation considerations) and that errors are not customized. Satisfying criterion 13 would need an overridden `ArgumentParser.error`, which the RFC never mentions.
2. **Handler signature against the dispatch order** (see 1.1).
3. **"Implementer's choice: the shape of the COMMANDS table" against criterion 9**, which needs a known injection point for tests (see 1.15).
4. **Criterion 1 against TEST-8.** `main(["list"])` with no `TD_FILE` set reads `~/.td.json`. TEST-8 forbids tests from touching the real home file, so the test must set `TD_FILE`, and the criterion does not say that.
5. **Test harness against "reconfigure stdout and stderr at the start of `main`".** The RFC says tests call `main` directly. Under `contextlib.redirect_stdout(io.StringIO())`, `StringIO` has no `reconfigure`, and `os.dup2` on `sys.stdout.fileno()` fails on it. The RFC does not say to guard these calls, so as written, direct-call tests either crash or require a guard the RFC does not specify.
6. **Scope against the Features coverage.** F11 ("Error handling ... id validation") and TEST-3 ("run each command including `add`") are cited as the RFC's scope, but RFC-002 contains no `add`, `done` or `rm`. The RFC does not say that the id-validation and unknown-id parts of F11 are deferred to RFC-003/004.
7. **Rules list omissions.** The RFC's "Rules" header lacks CLI-7, DATA-7 and SAFE-3, which criteria 4, 7 and 8 depend on. It also lacks STACK-2, which the Implementation considerations cite. Header and body are inconsistent. OUT-3, SEC-2 and DEV-1 are listed, but none of them has a criterion (see 3.6).
8. **`PRD` Open Question 18 against "return 0".** Both say the closed stdout is not an error. Not contradictory, but the RFC lists it only as an assumption while F12 in FEATURES also marks it "(assumption)"; no source states the user agreed.

## 3. Acceptance criteria a test cannot check or that pass by luck

1. **Criterion 11 (pipe to `head -1`) passes by luck.** 1000 short tasks is roughly 20 KB, below the usual 64 KB pipe buffer. `td` can finish writing before `head` exits, so the `BrokenPipeError` path never runs and the test passes with a wrong or missing handler. A deterministic test needs output larger than the pipe buffer, or a reader that closes before `td` writes. The criterion also says "`td`'s exit status is 0"; in a shell pipeline `$?` is `head`'s unless `PIPESTATUS` or two `Popen` objects are used.
2. **Criterion 12 (`LANG=C`) passes without the feature.** Python 3.7 and newer coerces the C locale to UTF-8 (PEP 538/540), so stdout is UTF-8 and nothing is unencodable. The test passes even without `errors="replace"`, and "unencodable characters appear as replacement characters" cannot be observed. A real test needs `PYTHONCOERCECLOCALE=0 PYTHONUTF8=0` or `PYTHONIOENCODING=ascii`, which the criterion does not say. It also does not say what "replacement characters" are: `?` (encode replace) or U+FFFD.
3. **Criterion 7 "file is unchanged" is trivially true for `list`.** `list` never writes. The part that is checkable is the exit code, the one `td:` line and the path in it. "one line starting with `td:`" is also ambiguous: exactly one stderr line, or at least one such line.
4. **Criterion 7 refers to "RFC-001 criterion 6 cases"**, which I cannot read. The set of corrupt inputs is unknown, and so is whether they overlap with TEST-3's list (invalid JSON, wrong types, missing key, newer version).
5. **Criterion 5** ("byte-identical stdout and the same exit code") is checkable, but weak: it passes for any two runs that both fail the same way unless it is run on a non-empty list. The criterion does not say on which data.
6. **No criterion for PERF-1** (read once, save once), PERF-2, OUT-3 (no `isatty`, no ANSI in code), SEC-2 (no `subprocess`, `os.system`, `eval`) or DEV-1 (no placeholder handlers). They are stated in Technical approach and listed under Rules. A reviewer cannot tell how they are verified (for example by grep).
7. **Criterion 13 is a universal claim** ("every error line", "no failed command"). A test can only sample some commands, and RFC-002 has only `list`. It adds nothing beyond criteria 6 to 9 and conflicts with the argparse default (2.1).
8. **Criterion 10 "exactly one line per task".** The check depends on how lines are counted. `str.splitlines()` splits on U+2028 and U+2029, which the `Cc`-only rule leaves in place. `split("\n")` does not. `\t` is also `Cc` and becomes a space, which a test might not expect. The criterion lists only three characters.
9. **Criterion 1 "`td` contains no `sys.exit` call except the one in the `__main__` guard"** can only be checked by text search or AST of a file with no `.py` suffix. Importing `td` for `main(["list"])` needs `SourceFileLoader` or similar, and "the file is executable" fails on a copy or checkout that loses the mode bit. This is a test-setup guess, not a behavior one.
10. **Criterion 9's "no `Traceback` text"** can be satisfied by swallowing all errors silently if the single line is not also required to contain `unexpected error`. The criterion does require it, but does not say the full message format `td: unexpected error: <type>: <message>` is checked, nor the exit code 1 for the injected case beyond "yields exit 1".
11. **Criterion 3 "whatever order they are stored in"** has no stated way to build an unsorted file when the schema is unknown (1.2), and no statement that RFC-001 accepts unsorted storage (1.12).
12. **Criterion 6 and 8's "nothing to stdout"** cannot cover `--help`, which is not an error.
