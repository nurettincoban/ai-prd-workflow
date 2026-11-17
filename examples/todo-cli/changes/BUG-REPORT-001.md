# Bug report on td, filed after an outside review

Filed by the person running this example, from an outside reviewer's report on the code as of the last /workflow-status. Every item below was reproduced by the reviewer on Linux, Python 3.13, with TD_FILE pointing at a scratch file. The user in IDEA.md has not seen this report.

1. `td add call mom -h` prints add's help, saves nothing and exits 0. The task the user typed is gone without an error. Similar: `td add fix bug in -- parser` stores `fix bug in parser`, silently dropping the `--`.
2. After `chmod 600` on the data file, the next `td add` leaves it at mode 644. A read-only (444) data file is also replaced by `td add` and ends up 644.
3. `td add x >&-` (stdout closed) saves the task, then prints `td: unexpected error: AttributeError: ...` and exits 1. `td add x >/dev/full` also saves and exits 1. A script that retries on exit 1 adds the task twice. RULES.md SAFE-6 says a failed command never modifies the data file.
4. Deleting the `handle.flush()` call in `save_store` makes `td` fsync an empty temp file before the rename (a probe saw `size at fsync: 0`), and all 85 tests still pass. Moving the fsync before the write also passes. The test that covers the fsync does not check what was on disk when fsync ran.
5. Pressing Ctrl-C within the first 5 to 40 ms of a run printed a Python traceback in 31 of 60 tries, instead of `td: interrupted`.
6. `td --help` does not say where the data lives (`~/.td.json` or `TD_FILE`), and adding that line to the description fails two tests.
