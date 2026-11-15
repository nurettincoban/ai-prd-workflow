import ast
import contextlib
import io
import json
import os
import stat
import subprocess
import sys
import unittest
from unittest import mock

import helpers

td = helpers.load_td()
TD_SOURCE = helpers.TD_PATH.read_text(encoding="utf-8")


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = td.main(argv)
    return code, out.getvalue(), err.getvalue()


def write_store(tasks, next_id=None):
    ids = [t[0] for t in tasks]
    store = {"version": 1, "next_id": next_id or (max(ids, default=0) + 1),
             "tasks": [{"id": i, "text": s, "done": d} for i, s, d in tasks]}
    with open(os.environ["TD_FILE"], "w", encoding="utf-8") as f:
        json.dump(store, f)


def write_raw(data):
    with open(os.environ["TD_FILE"], "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))


def read_raw():
    with open(os.environ["TD_FILE"], "rb") as f:
        return f.read()


THREE = [(1, "buy milk", False), (2, "write notes", True), (10, "x", False)]


class Basics(unittest.TestCase):
    def test_c1_shebang_exec_int_exit(self):  # criterion 1
        first = TD_SOURCE.split("\n", 1)[0]
        self.assertEqual(first, "#!/usr/bin/env python3")
        self.assertTrue(os.stat(helpers.TD_PATH).st_mode & stat.S_IXUSR)
        with helpers.temp_env():
            self.assertIsInstance(td.main(["list"]), int)
        tree = ast.parse(TD_SOURCE)
        guard_calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) \
                    and isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__":
                guard_calls.update(id(n) for n in ast.walk(node))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                    and node.func.attr == "exit" and isinstance(node.func.value, ast.Name) \
                    and node.func.value.id == "sys":
                self.assertIn(id(node), guard_calls)

    def test_c2_list_output(self):  # criterion 2
        with helpers.temp_env():
            write_store(THREE)
            self.assertEqual(run(["list"]), (0, "1 [ ] buy milk\n2 [x] write notes\n10 [ ] x\n", ""))

    def test_c3_sorted(self):  # criterion 3
        with helpers.temp_env():
            write_store([(3, "c", False), (1, "a", True), (2, "b", False)])
            self.assertEqual(run(["list"])[1], "1 [x] a\n2 [ ] b\n3 [ ] c\n")

    def test_c4_empty_creates_nothing(self):  # criterion 4
        with helpers.temp_env():
            self.assertEqual(run(["list"]), (0, "", ""))
            self.assertFalse(os.path.exists(os.environ["TD_FILE"]))
            write_store([])
            before = read_raw()
            self.assertEqual(run(["list"]), (0, "", ""))
            self.assertEqual(read_raw(), before)

    def test_c5_bare_equals_list(self):  # criterion 5
        with helpers.temp_env():
            write_store(THREE)
            self.assertEqual(run([]), run(["list"]))
            self.assertEqual(run([])[2], "")
            os.remove(os.environ["TD_FILE"])
            self.assertEqual(run([]), run(["list"]))
            self.assertEqual(run([]), (0, "", ""))


class Usage(unittest.TestCase):
    def test_c6_usage_errors(self):  # criterion 6
        cases = [["frob"], ["li"], ["list", "--bogus"], ["--bogus"], ["5"], ["list", "x"], ["a\nb"]]
        with helpers.temp_env():
            write_store(THREE)
            for argv in cases:
                with self.subTest(argv=argv):
                    code, out, err = run(argv)
                    self.assertEqual(code, 2)
                    self.assertEqual(out, "")
                    self.assertTrue(err.startswith("td:"))
                    self.assertEqual(err.count("\n"), 1)
                    self.assertTrue(err.endswith("\n"))
            code, out, err = run(["--help"])
            self.assertEqual((code, err), (0, ""))
            self.assertIn("list", out)

    def test_c7_corrupt(self):  # criterion 7
        corrupt = [
            b"{not json",
            json.dumps({"version": 1, "next_id": 2, "tasks": [{"id": 1, "text": 5, "done": False}]}).encode(),
            json.dumps({"version": 1, "tasks": []}).encode(),
            json.dumps({"version": 2, "next_id": 1, "tasks": []}).encode(),
        ]
        with helpers.temp_env():
            for data in corrupt:
                for argv in (["list"], []):
                    with self.subTest(data=data, argv=argv):
                        write_raw(data)
                        code, out, err = run(argv)
                        self.assertEqual(code, 1)
                        self.assertEqual(out, "")
                        self.assertTrue(err.startswith("td:"))
                        self.assertEqual(err.count("\n"), 1)
                        self.assertIn(os.environ["TD_FILE"], err)
                        self.assertEqual(read_raw(), data)

    def test_c8_load_failures(self):  # criterion 8
        with helpers.temp_env() as tmp:
            for target in (os.path.join(tmp, "nodir", "t.json"), tmp):
                with self.subTest(target=target):
                    os.environ["TD_FILE"] = target
                    code, out, err = run(["list"])
                    self.assertEqual((code, out), (1, ""))
                    self.assertTrue(err.startswith("td:"))
                    self.assertEqual(err.count("\n"), 1)
                    self.assertIn(target, err)
            os.environ["TD_FILE"] = os.path.join(tmp, "tasks.json")
            write_raw(b"{bad")
            code, out, err = run(["list", "x"])
            self.assertEqual((code, out), (2, ""))
            self.assertEqual(read_raw(), b"{bad")

    def test_c9_error_path(self):  # criterion 9
        def boom(args, store, path):
            raise RuntimeError("boom")

        def usage(args, store, path):
            raise td.TdError("m", 2)

        def newline(args, store, path):
            raise td.TdError("a\nb")

        with helpers.temp_env():
            with mock.patch.dict(td.COMMANDS, {"list": boom}):
                self.assertEqual(run(["list"]), (1, "", "td: unexpected error: RuntimeError: boom\n"))
            with mock.patch.dict(td.COMMANDS, {"list": usage}):
                self.assertEqual(run(["list"]), (2, "", "td: m\n"))
            with mock.patch.dict(td.COMMANDS, {"list": newline}):
                code, out, err = run(["list"])
                self.assertEqual((code, out, err), (1, "", "td: a b\n"))
            with mock.patch.dict(td.COMMANDS, {"list": boom}):
                self.assertNotIn("Traceback", run([])[2])


class Output(unittest.TestCase):
    def test_c10_sanitized(self):  # criterion 10
        texts = ["a\x1b[31mb", "a\nb", "a\rb", "a\tb", "a b"]
        with helpers.temp_env():
            write_store([(i + 1, t, False) for i, t in enumerate(texts)])
            code, out, err = run(["list"])
            self.assertEqual((code, err), (0, ""))
            self.assertNotIn("\x1b", out)
            self.assertEqual(len(out.splitlines()), len(texts))
            self.assertEqual(out.split("\n")[:-1], out.splitlines())
            self.assertEqual(out.split("\n")[-1], "")
            self.assertEqual(out.splitlines()[0], "1 [ ] a [31mb")

    def test_c11_broken_pipe(self):  # criterion 11
        with helpers.temp_env():
            write_store([(i, "x" * 60, False) for i in range(1, 20001)])
            proc = subprocess.Popen([sys.executable, str(helpers.TD_PATH), "list"],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=os.environ.copy())
            first = proc.stdout.readline()
            proc.stdout.close()
            err = proc.stderr.read()
            proc.stderr.close()
            code = proc.wait(timeout=30)
            self.assertTrue(first.startswith(b"1 [ ] "))
            self.assertEqual((code, err), (0, b""))

    def test_c12_ascii_stdout(self):  # criterion 12
        with helpers.temp_env():
            write_store([(1, "café", False)])
            env = os.environ.copy()
            env.update({"LANG": "C", "LC_ALL": "C", "PYTHONIOENCODING": "ascii",
                        "PYTHONUTF8": "0", "PYTHONCOERCECLOCALE": "0"})
            proc = subprocess.run([sys.executable, str(helpers.TD_PATH), "list"], env=env,
                                  capture_output=True, timeout=30)
            self.assertEqual(proc.returncode, 0)
            self.assertNotIn(b"UnicodeEncodeError", proc.stderr)
            self.assertEqual(proc.stdout, b"1 [ ] caf?\n")


class Scans(unittest.TestCase):
    def test_c13_static(self):  # criterion 13
        tree = ast.parse(TD_SOURCE)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                self.assertNotIn(node.id, ("isatty", "NotImplementedError"))
            if isinstance(node, ast.Attribute):
                self.assertNotEqual(node.attr, "isatty")
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.assertNotIn("\x1b", node.value)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                body = [n for n in node.body
                        if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
                self.assertFalse(body and all(isinstance(n, ast.Pass) for n in body))
        for line in TD_SOURCE.splitlines():
            if not line.strip().startswith("#"):
                self.assertNotIn("TODO", line)
                self.assertNotIn("FIXME", line)

    def test_c14_single_load(self):  # criterion 14
        with helpers.temp_env():
            write_store(THREE)
            with mock.patch.object(td, "resolve_path", wraps=td.resolve_path) as rp, \
                    mock.patch.object(td, "load_store", wraps=td.load_store) as ls, \
                    mock.patch.object(td, "save_store", wraps=td.save_store) as ss:
                self.assertEqual(run(["list"])[0], 0)
            self.assertEqual((rp.call_count, ls.call_count, ss.call_count), (1, 1, 0))


if __name__ == "__main__":
    unittest.main()
