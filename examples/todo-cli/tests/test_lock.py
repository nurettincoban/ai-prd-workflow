"""RFC-006 tests: the lock for concurrent runs (F17, SAFE-8). Holders and runs are real subprocesses."""
import contextlib
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import helpers  # noqa: E402

TD = str(helpers.TD_PATH)
HOLDER = """
import importlib.machinery, importlib.util, sys
loader = importlib.machinery.SourceFileLoader("td", sys.argv[1])
spec = importlib.util.spec_from_loader("td", loader)
td = importlib.util.module_from_spec(spec)
loader.exec_module(td)
with td.data_lock(sys.argv[2]):
    print("ready", flush=True)
    sys.stdin.readline()
"""
FIXTURE = {"version": 1, "next_id": 4, "tasks": [
    {"id": 1, "text": "one", "done": True},
    {"id": 2, "text": "two", "done": False},
    {"id": 3, "text": "three", "done": False}]}


def write_store(path, store):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(store, handle, indent=4)  # non-canonical on purpose


def read_store(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


class Holder:
    """A subprocess that holds data_lock(path) until release() or kill()."""

    def __init__(self, path):
        self.proc = subprocess.Popen([sys.executable, "-c", HOLDER, TD, str(path)], stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, text=True)
        if self.proc.stdout.readline().strip() != "ready":
            raise AssertionError("holder did not get the lock")

    def release(self):
        with contextlib.suppress(OSError):
            self.proc.stdin.write("\n")
            self.proc.stdin.flush()
        self.proc.wait(timeout=10)
        self.proc.stdin.close()
        self.proc.stdout.close()

    def kill(self):
        self.proc.kill()
        self.proc.wait(timeout=10)
        self.proc.stdin.close()
        self.proc.stdout.close()


def spawn(*argv):
    return subprocess.Popen([sys.executable, TD, *argv], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)


def run(*argv, timeout=10):
    proc = spawn(*argv)
    out, err = proc.communicate(timeout=timeout)
    return proc.returncode, out, err


def call_main(td, argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = td.main(argv)
    return code, out.getvalue(), err.getvalue()


@unittest.skipUnless(os.name == "posix", "the lock needs fcntl")
class LockTests(unittest.TestCase):
    def setUp(self):
        cm = helpers.temp_env()
        self.tmp = cm.__enter__()
        self.addCleanup(cm.__exit__, None, None, None)
        self.path = os.environ["TD_FILE"]
        self.td = helpers.load_td()

    def holder(self):
        holder = Holder(self.path)
        self.addCleanup(lambda: holder.proc.poll() is None and holder.release())
        return holder

    def test_1_interface(self):
        self.assertEqual(self.td.MUTATING, frozenset({"add", "done", "rm", "clear"}))
        self.assertEqual(self.td.LOCK_WAIT_SECONDS, 10)
        for value in (self.path, pathlib.Path(self.path)):
            with self.td.data_lock(value):
                pass
        holder = self.holder()
        self.td.LOCK_WAIT_SECONDS = 0.3
        with self.assertRaises(self.td.TdError):
            with self.td.data_lock(self.path):
                pass
        holder.release()
        with self.td.data_lock(self.path):
            pass

    def test_2_held_lock_makes_mutating_commands_wait(self):
        cases = [(("add", "x"), lambda s: s["tasks"].append({"id": 4, "text": "x", "done": False}) or s.update(next_id=5)),
                 (("done", "1"), lambda s: None),
                 (("rm", "2"), lambda s: s["tasks"].remove(s["tasks"][1])),
                 (("clear",), lambda s: s["tasks"].remove(s["tasks"][0]))]
        for argv, apply in cases:
            with self.subTest(argv=argv):
                store = json.loads(json.dumps(FIXTURE))
                store["tasks"][2]["done"] = False
                write_store(self.path, store)
                holder = self.holder()
                proc = spawn(*argv)
                time.sleep(0.5)
                self.assertIsNone(proc.poll(), "ran without the lock")
                self.assertEqual(read_store(self.path), store, "wrote while the lock was held")
                holder.release()
                out, err = proc.communicate(timeout=10)
                self.assertEqual(proc.returncode, 0, err)
                expected = json.loads(json.dumps(store))
                apply(expected)
                self.assertEqual(read_store(self.path), expected)

    def test_3_list_never_waits(self):
        write_store(self.path, FIXTURE)
        before = read_bytes(self.path)
        holder = self.holder()
        for argv in (("list",), ()):
            with self.subTest(argv=argv):
                code, out, err = run(*argv, timeout=5)
                self.assertEqual((code, err), (0, ""))
                self.assertEqual(out, "1 [x] one\n2 [ ] two\n3 [ ] three\n")
        self.assertEqual(read_bytes(self.path), before)
        holder.release()

    def test_4_timeout_exit_1_and_nothing_changed(self):
        write_store(self.path, FIXTURE)
        before = read_bytes(self.path)
        holder = self.holder()
        self.td.LOCK_WAIT_SECONDS = 0.3
        for argv in (["add", "x"], ["done", "1"], ["rm", "2"], ["clear"]):
            with self.subTest(argv=argv):
                start = time.monotonic()
                code, out, err = call_main(self.td, argv)
                self.assertLess(time.monotonic() - start, 3)
                self.assertEqual(code, 1)
                self.assertEqual(out, "")
                self.assertEqual(len(err.splitlines()), 1)
                self.assertTrue(err.startswith("td: "), err)
                self.assertIn(self.path, err)
                self.assertEqual(read_bytes(self.path), before)
                self.assertEqual(os.listdir(self.tmp), ["tasks.json"])
        holder.release()

    def test_5_parallel_adds_lose_nothing(self):
        for round_no in range(5):
            with self.subTest(round=round_no):
                if os.path.exists(self.path):
                    os.remove(self.path)
                procs = [spawn("add", f"task {n}") for n in range(8)]
                for proc in procs:
                    proc.communicate(timeout=30)
                    self.assertEqual(proc.returncode, 0)
                store = read_store(self.path)
                self.assertEqual(sorted(t["id"] for t in store["tasks"]), list(range(1, 9)))
                self.assertEqual(sorted(t["text"] for t in store["tasks"]), sorted(f"task {n}" for n in range(8)))
                self.assertEqual(store["next_id"], 9)

    def test_6_parallel_mixed_commands(self):
        for round_no in range(5):
            with self.subTest(round=round_no):
                write_store(self.path, {"version": 1, "next_id": 5, "tasks": [
                    {"id": 1, "text": "a", "done": True}, {"id": 2, "text": "b", "done": False},
                    {"id": 3, "text": "c", "done": False}, {"id": 4, "text": "d", "done": False}]})
                procs = [spawn("clear"), spawn("done", "3"), spawn("rm", "4"), spawn("add", "y")]
                for proc in procs:
                    proc.communicate(timeout=30)
                    self.assertEqual(proc.returncode, 0)
                store = read_store(self.path)
                by_id = {t["id"]: t for t in store["tasks"]}
                self.assertEqual(len(by_id), len(store["tasks"]))
                self.assertFalse(by_id[2]["done"])
                self.assertNotIn(1, by_id)
                self.assertNotIn(4, by_id)
                self.assertIn(by_id.get(3, {"done": True})["done"], (True,))
                self.assertEqual([t["id"] for t in store["tasks"] if t["text"] == "y"], [5])
                self.assertEqual(store["next_id"], 6)

    def test_7_killed_holder_leaves_no_lock(self):
        holder = self.holder()
        holder.kill()
        code, out, err = run("add", "z", timeout=5)
        self.assertEqual(code, 0, err)
        self.assertEqual([t["text"] for t in read_store(self.path)["tasks"]], ["z"])

    def test_8_nothing_left_behind(self):
        self.assertEqual(run("add", "x")[0], 0)
        self.assertEqual(os.listdir(self.tmp), ["tasks.json"])
        os.remove(self.path)
        for argv, code in ((("done", "99"), 1), (("add", "-x"), 2), (("clear",), 0)):
            with self.subTest(argv=argv):
                self.assertEqual(run(*argv)[0], code)
                self.assertEqual(os.listdir(self.tmp), [])
        write_store(self.path, FIXTURE)
        self.assertEqual(run("clear")[0], 0)
        self.assertEqual(os.listdir(self.tmp), ["tasks.json"])
        missing = os.path.join(self.tmp, "nope", "tasks.json")
        afile = os.path.join(self.tmp, "afile")
        pathlib.Path(afile).write_text("x")
        for bad in (missing, os.path.join(afile, "tasks.json")):
            with self.subTest(parent=bad):
                os.environ["TD_FILE"] = bad
                code, out, err = run("add", "x")
                self.assertEqual((code, out), (1, ""))
                self.assertEqual(len(err.splitlines()), 1)
                self.assertTrue(err.startswith("td: " + bad), err)
        self.assertEqual(sorted(os.listdir(self.tmp)), ["afile", "tasks.json"])

    def test_9_lock_comes_before_load_but_after_argparse(self):
        cases = [(("add", "x"), b"{not json", 1, "invalid JSON"),
                 (("done", "99"), None, 1, "no task with id 99"),
                 (("add", ""), None, 2, "empty")]
        for argv, content, code, text in cases:
            with self.subTest(argv=argv):
                if content is None:
                    write_store(self.path, FIXTURE)
                else:
                    pathlib.Path(self.path).write_bytes(content)
                before = read_bytes(self.path)
                holder = self.holder()
                proc = spawn(*argv)
                time.sleep(0.5)
                self.assertIsNone(proc.poll(), "did not wait for the lock")
                holder.release()
                out, err = proc.communicate(timeout=10)
                self.assertEqual((proc.returncode, out), (code, ""))
                self.assertIn(text, err)
                self.assertEqual(read_bytes(self.path), before)
        holder = self.holder()
        for argv in (("add", "-x"), ("done",)):
            with self.subTest(argv=argv):
                self.assertEqual(run(*argv, timeout=5)[0], 2)
        holder.release()

    def test_10_without_fcntl(self):
        saved = sys.modules.get("fcntl")
        sys.modules["fcntl"] = None
        try:
            td = helpers.load_td()
        finally:
            if saved is None:
                del sys.modules["fcntl"]
            else:
                sys.modules["fcntl"] = saved
        self.assertIsNone(td.fcntl)
        self.assertEqual(call_main(td, ["add", "x"])[0], 0)
        self.assertEqual([t["text"] for t in read_store(self.path)["tasks"]], ["x"])

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root can read any directory")
    def test_11_unreadable_directory(self):
        sub = os.path.join(self.tmp, "d")
        os.mkdir(sub)
        os.environ["TD_FILE"] = os.path.join(sub, "tasks.json")
        os.chmod(sub, 0o300)
        self.addCleanup(os.chmod, sub, 0o700)
        code, out, err = run("add", "x")
        self.assertEqual((code, out), (1, ""))
        self.assertEqual(len(err.splitlines()), 1)
        self.assertTrue(err.startswith("td: "))
        self.assertIn(os.environ["TD_FILE"], err)


if __name__ == "__main__":
    unittest.main()
