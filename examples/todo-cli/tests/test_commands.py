import contextlib
import io
import json
import os
import unittest
from unittest import mock

import helpers

td = helpers.load_td()


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = td.main(argv)
    return code, out.getvalue(), err.getvalue()


def write_store(tasks, next_id=None):
    """Write a non-canonical (4-space indent) store so a rewrite is detectable."""
    ids = [t[0] for t in tasks]
    store = {"version": 1, "next_id": next_id or (max(ids, default=0) + 1),
             "tasks": [{"id": i, "text": s, "done": d} for i, s, d in tasks]}
    with open(os.environ["TD_FILE"], "w", encoding="utf-8") as f:
        json.dump(store, f, indent=4)


def read_raw():
    with open(os.environ["TD_FILE"], "rb") as f:
        return f.read()


def read_store():
    return json.loads(read_raw().decode("utf-8"))


def exists():
    return os.path.exists(os.environ["TD_FILE"])


THREE = [(1, "one", False), (2, "two", False), (3, "three", True)]


class Add(unittest.TestCase):
    def test_c1_add(self):  # criterion 1
        for argv in (["add", "buy", "milk"], ["add", "buy milk"]):
            with helpers.temp_env():
                self.assertEqual(run(argv), (0, "1 [ ] buy milk\n", ""))
                self.assertTrue(exists())
                self.assertEqual(read_store()["tasks"][0]["text"], "buy milk")

    def test_c2_strip(self):  # criterion 2
        with helpers.temp_env():
            self.assertEqual(run(["add", "  buy milk  "]), (0, "1 [ ] buy milk\n", ""))
            self.assertEqual(run(["add", "  a", "b  "])[0], 0)
            self.assertEqual([t["text"] for t in read_store()["tasks"]], ["buy milk", "a b"])

    def test_c3_empty(self):  # criterion 3
        for argv in (["add"], ["add", ""], ["add", "   "], ["add", "  \t "]):
            with helpers.temp_env():
                code, out, err = run(argv)
                self.assertEqual((code, out), (2, ""), argv)
                self.assertTrue(err.startswith("td:") and err.count("\n") == 1, argv)
                self.assertFalse(exists())
            with helpers.temp_env():
                write_store(THREE)
                before = read_raw()
                self.assertEqual(run(argv)[0], 2)
                self.assertEqual(read_raw(), before)

    def test_c4_newlines_and_flags(self):  # criterion 4
        bad = [["add", "a\nb"], ["add", "a\r"], ["add", "\nabc"], ["add", "abc\n"],
               ["add", "-x"], ["add", "\udcff"]]
        for argv in bad:
            with helpers.temp_env():
                code, out, err = run(argv)
                self.assertEqual((code, out), (2, ""), argv)
                self.assertTrue(err.startswith("td:") and err.count("\n") == 1, argv)
                self.assertFalse(exists())
            with helpers.temp_env():
                write_store(THREE)
                before = read_raw()
                self.assertEqual(run(argv)[0], 2, argv)
                self.assertEqual(read_raw(), before, argv)
        with helpers.temp_env():
            self.assertEqual(run(["add", "--", "-x"]), (0, "1 [ ] -x\n", ""))
            self.assertEqual(read_store()["tasks"][0]["text"], "-x")

    def test_c5_long_unicode_tab(self):  # criterion 5
        with helpers.temp_env():
            big = "x" * 100000
            self.assertEqual(run(["add", big])[0], 0)
            self.assertEqual(run(["add", "naïve café"])[0], 0)
            self.assertEqual(run(["add", "a\tb"])[0], 0)
            code, out, err = run(["list"])
            self.assertEqual((code, err), (0, ""))
            lines = out.split("\n")
            self.assertEqual(lines[0], "1 [ ] " + big)
            self.assertEqual(lines[1], "2 [ ] naïve café")
            self.assertEqual(lines[2], "3 [ ] a b")
            self.assertEqual(read_store()["tasks"][2]["text"], "a\tb")

    def test_c6_ids_never_reused(self):  # criterion 6
        with helpers.temp_env():
            run(["add", "a"]); run(["add", "b"])
            self.assertEqual(run(["rm", "2"])[0], 0)
            self.assertEqual(run(["add", "c"])[1], "3 [ ] c\n")
            self.assertEqual(run(["list"])[1], "1 [ ] a\n3 [ ] c\n")
            self.assertEqual(run(["rm", "1"])[0], 0)
            self.assertEqual(run(["list"])[1], "3 [ ] c\n")
        with helpers.temp_env():
            run(["add", "a"]); run(["add", "b"])
            run(["rm", "1"]); run(["rm", "2"])
            self.assertEqual(run(["add", "c"])[1], "3 [ ] c\n")


class Done(unittest.TestCase):
    def test_c7_done(self):  # criterion 7
        with helpers.temp_env():
            write_store(THREE[:2])
            self.assertEqual(run(["done", "1"]), (0, "", ""))
            self.assertEqual(run(["list"])[1], "1 [x] one\n2 [ ] two\n")
        with helpers.temp_env():
            write_store(THREE[:2])
            self.assertEqual(run(["done", "01"]), (0, "", ""))
            self.assertEqual(run(["list"])[1], "1 [x] one\n2 [ ] two\n")
        with helpers.temp_env():
            write_store([(10 ** 20, "big", False)])
            self.assertEqual(run(["done", "100000000000000000000"]), (0, "", ""))
            self.assertTrue(read_store()["tasks"][0]["done"])

    def test_c8_done_twice(self):  # criterion 8
        with helpers.temp_env():
            write_store(THREE)
            before = read_raw()
            self.assertEqual(run(["done", "3"]), (0, "", ""))
            self.assertEqual(read_raw(), before)


class Rm(unittest.TestCase):
    def test_c9_rm(self):  # criterion 9
        with helpers.temp_env():
            write_store(THREE, next_id=7)
            self.assertEqual(run(["rm", "1"]), (0, "", ""))
            self.assertEqual(run(["list"])[1], "2 [ ] two\n3 [x] three\n")
            self.assertEqual(read_store()["next_id"], 7)


class Errors(unittest.TestCase):
    def test_c10_unknown_id(self):  # criterion 10
        # 4301 and 5000 digits are past Python's int() limit (4300): without the cut-off
        # in _parse_id, int() raises ValueError and main reports "unexpected error"
        ids = ["99", "0", "99999999999999999999", "007", "9" * 4001, "9" * 4301, "9" * 5000,
               "0" * 5000 + "0"]
        for cmd in ("done", "rm"):
            for raw in ids:
                with helpers.temp_env():
                    write_store(THREE)
                    before = read_raw()
                    code, out, err = run([cmd, raw])
                    self.assertEqual((code, out, err), (1, "", f"td: no task with id {raw}\n"), (cmd, raw))
                    self.assertEqual(read_raw(), before)
                with helpers.temp_env():
                    self.assertEqual(run([cmd, raw])[0], 1)
                    self.assertFalse(exists())

    def test_c10_leading_zeros_dropped_before_length_check(self):  # criterion 10
        # 5000 zeros then 99 is well-formed and means task 99; without lstrip("0") before
        # the 4000-digit cut-off it would be reported as an unknown id
        for cmd in ("done", "rm"):
            with helpers.temp_env():
                write_store(THREE + [(99, "ninety-nine", False)])
                self.assertEqual(run([cmd, "0" * 5000 + "99"]), (0, "", ""), cmd)
                tasks = read_store()["tasks"]
                if cmd == "done":
                    self.assertTrue([t for t in tasks if t["id"] == 99][0]["done"])
                else:
                    self.assertNotIn(99, [t["id"] for t in tasks])
        # a real 4000-digit id is still an id (the cut-off is not lower than the RFC says)
        big = 10 ** 3999
        with helpers.temp_env():
            write_store([(big, "huge", False)])
            self.assertEqual(run(["done", str(big)]), (0, "", ""))
            self.assertTrue(read_store()["tasks"][0]["done"])

    def test_c11_bad_id(self):  # criterion 11
        # the last four are non-ASCII digits (Arabic-Indic, full-width, Devanagari, and a mixed id):
        # int() accepts most of them, so only the ASCII-only check keeps them out
        bad = [["abc"], ["-1"], ["1.5"], ["+1"], [" 1"], [""], [], ["1", "2"],
               ["\u0663"], ["\uff11"], ["\u0969"], ["1\u0663"]]
        for cmd in ("done", "rm"):
            for rest in bad:
                with helpers.temp_env():
                    write_store(THREE)
                    before = read_raw()
                    code, out, err = run([cmd] + rest)
                    self.assertEqual((code, out), (2, ""), (cmd, rest))
                    self.assertTrue(err.startswith("td:") and err.count("\n") == 1, (cmd, rest))
                    self.assertEqual(read_raw(), before)

    def test_c12_corrupt(self):  # criterion 12
        corrupt = ["{not json", json.dumps({"version": 1, "next_id": "x", "tasks": []}),
                   json.dumps({"version": 1, "tasks": []}),
                   json.dumps({"version": 2, "next_id": 1, "tasks": []}),
                   "[" * 200000]
        for text in corrupt:
            for argv, code in ((["add", "x"], 1), (["done", "1"], 1), (["rm", "1"], 1),
                               (["add"], 1), (["add", ""], 1), (["done", "abc"], 1),
                               (["done", "-1"], 1), (["done"], 2), (["rm"], 2)):
                with helpers.temp_env():
                    with open(os.environ["TD_FILE"], "w", encoding="utf-8") as f:
                        f.write(text)
                    before = read_raw()
                    got, out, err = run(argv)
                    self.assertEqual((got, out), (code, ""), (text, argv))
                    self.assertEqual(err.count("\n"), 1)
                    self.assertTrue(err.startswith("td:"))
                    if code == 1:
                        self.assertIn(os.environ["TD_FILE"], err)
                    self.assertEqual(read_raw(), before)

    def test_c13_load_save_counts(self):  # criterion 13
        def counted(argv, setup):
            with helpers.temp_env():
                setup()
                loads, saves = [], []
                real_load, real_save = td.load_store, td.save_store
                with mock.patch.object(td, "load_store", lambda p: (loads.append(1), real_load(p))[1]), \
                        mock.patch.object(td, "save_store", lambda p, s: (saves.append(1), real_save(p, s))[1]):
                    code = run(argv)[0]
                return code, len(loads), len(saves)

        seed = lambda: write_store(THREE)
        self.assertEqual(counted(["add", "x"], seed), (0, 1, 1))
        self.assertEqual(counted(["rm", "1"], seed), (0, 1, 1))
        self.assertEqual(counted(["done", "1"], seed), (0, 1, 1))
        self.assertEqual(counted(["done", "3"], seed), (0, 1, 0))
        self.assertEqual(counted(["done", "99"], seed), (1, 1, 0))
        self.assertEqual(counted(["rm", "99"], seed), (1, 1, 0))
        self.assertEqual(counted(["add", ""], seed), (2, 1, 0))
        self.assertEqual(counted(["done", "abc"], seed), (2, 1, 0))


if __name__ == "__main__":
    unittest.main()
