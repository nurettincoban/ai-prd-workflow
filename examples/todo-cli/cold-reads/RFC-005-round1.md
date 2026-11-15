# Cold read: RFC-005 Release checks

Question: what would I have to guess to implement this RFC with nobody to ask?

## 1. Guesses that change observable behavior or a shared interface

1. Criterion 3 pins the `td list` line as `1 [ ] x`. FEATURES F6/F7, RULES Open Question 4 and PRD Open Question 5 all say the line format and the `td add` output line are still open. The RFC's only dependency is RFC-003, which I cannot read, so I do not know whether RFC-003 fixed this format. I would guess the format is `<id> <marker> <text>` with single spaces.
2. Criterion 3: "prints `1 [ ] x`" does not say which command prints it. It could be the `td list` output alone, or `td add` plus `td list` combined. It also does not say whether the match is exact stdout or a substring, or whether a trailing newline counts. `td add x` output is never asserted.
3. Criterion 3: "putting that directory on `PATH`" could mean prepending or replacing PATH. If it replaces PATH, `#!/usr/bin/env python3` cannot find `python3`. If it prepends, the test passes with the real PATH. Nothing says how `td` is invoked: bare `td` through PATH lookup, or by absolute path. Which Python the shebang must resolve to is also unstated.
4. Criterion 4 depends on `tests/fixtures/v1.json`, but nothing says who creates it or what it contains. DATA-1 says "exact key names are for the RFC", and this RFC never names them. I would have to invent the schema (version, next-id and task key names) and the fixture would be tied to my own invention.
5. Criterion 4: "a copy of `td` placed over an older copy". No older build exists, because this is v1. I would guess the test copies `td` onto a copy of itself, which proves nothing about upgrades.
6. Criterion 4: "its tasks are unchanged after a `td add`". `add` changes the file by appending a task and bumping next-id. I would guess this means the pre-existing tasks are still equal and the new id comes from the stored counter. The RFC does not say so.
7. Criterion 5: the fixture needs ids that make `done 1` and `rm 2` valid. Nothing says whether the four commands run in sequence against one file or each against a fresh fixture. Nothing says whether "finishes" means wall time of the whole subprocess, including interpreter start, or only in-process time. `td list` prints 5,000 lines, and whether stdout is captured or discarded is not stated.
8. Criterion 2 lists specific modules, but F16 and STACK-3 say "or similar". I would have to guess whether `ctypes`, `asyncio`, `xmlrpc`, `importlib` or `__import__`, `os.popen`, `os.spawn*` and `os.exec*` are covered. I would also guess how `from os import system` or `import urllib.request` is matched (top-level name versus dotted name).
9. Criterion 1: `tests/` "imports nothing outside the standard library". ARCH-2 says tests call `main` directly, so tests must load `td`, which has no `.py` suffix, through `importlib` by path. A literal reading would flag `td`, a shared `tests.helpers` module or a `tests` package import as non-stdlib. The RFC does not say these are exempt.

## 2. Contradictions

1. Summary says "Nothing here adds behavior". Criterion 2 bans importing `subprocess` at all, which is stricter than SEC-2 ("`subprocess` with `shell=True`"). That is a new restriction on the program, and RFC-003 may already use `subprocess`. It is unlikely to, but it is unverifiable.
2. Criterion 5 sets a 1 second budget at 5,000 tasks. PRD NFR-7 and F16 say "no perceptible delay" at "a few thousand" and give no budget. 1 second is perceptible and 5,000 is more than a few thousand. The RFC admits the budget is an assumption, but F16 is "Should" and the RFC treats it as a hard pass or fail test.
3. "Implementation Notes" is named in Technical approach and criterion 6 as the place to record manual runs, but the RFC has no `## Implementation Notes` section. Only `## Open Questions` exists.
4. The header lists Rules STACK-2, PERF-1, PERF-2 and ARCH-1 as covered. No criterion checks STACK-2 (no post-3.10 syntax), PERF-1 (one read and one save per command) or PERF-2. ARCH-1's "first line is the shebang" is only indirectly exercised by criterion 3.
5. F15 requires "no hard-coded separators" and "directory fsync skipped without failing the save". No criterion tests either. Criterion 6 only runs the suite on two platforms.
6. Dependencies: criteria 3 to 5 need `add`, `list`, `done` and `rm`, but only RFC-003 is listed. `clear` (F10) is never mentioned, and neither is whether the commands may be absent.

## 3. Criteria a test cannot check, or that pass by luck

1. Criterion 4: it passes trivially (same file over itself) as described in 1.5, so it can pass with no upgrade logic at all.
2. Criterion 5: the 1 second timing depends on the machine and on load, so it can be flaky on a slow CI runner. It also passes on a fast laptop regardless of algorithmic cost. The RFC does not say how to handle slow machines (retry, median, or skip).
3. Criterion 6: the criterion is manual and cannot be tested. "At least one newer version" is vague. Open Question 3 admits Python 3.10 has never been run, so the criterion may never be satisfiable. The macOS run is also manual.
4. Criterion 7: "All tests run without touching `~/.td.json`" has no stated check. Options are to set `HOME` to a temp dir and assert nothing is created, or to snapshot the real file. If a dev has no `~/.td.json`, a leak into it is not detected by luck. If the test sets `TD_FILE` everywhere, the criterion is satisfied by construction and checks nothing.
5. Criterion 1: `sys.stdlib_module_names` is a name list, so it cannot tell a stdlib module from a local file that shadows it (a local `json.py` in `tests/`).
6. Criterion 2: an AST import scan can be bypassed by dynamic imports, so it passes while a banned call exists.
