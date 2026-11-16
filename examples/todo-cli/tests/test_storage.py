import ast
import json
import os
import pathlib
import stat
import subprocess
import sys
import unittest
from unittest import mock

import helpers

td = helpers.load_td()
FIXTURE = pathlib.Path(__file__).resolve().parent / "fixtures" / "v1.json"


def store_of(*tasks, next_id=None):
    ids = [t["id"] for t in tasks]
    return {"version": 1, "next_id": next_id or (max(ids, default=0) + 1), "tasks": list(tasks)}


def task(i, text="t", done=False):
    return {"id": i, "text": text, "done": done}


def write(path, data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    with open(path, "wb") as f:
        f.write(data)


class EnvTest(unittest.TestCase):  # criterion 1, 15
    def test_resolve_path(self):
        with helpers.temp_env() as tmp:
            os.environ.pop("TD_FILE")
            self.assertEqual(td.resolve_path(), pathlib.Path(tmp, ".td.json"))
            os.environ["TD_FILE"] = "/x/y.json"
            self.assertEqual(td.resolve_path(), pathlib.Path("/x/y.json"))
            os.environ["TD_FILE"] = ""
            self.assertEqual(td.resolve_path(), pathlib.Path(tmp, ".td.json"))
            os.environ["TD_FILE"] = "~/z.json"
            self.assertEqual(td.resolve_path(), pathlib.Path(tmp, "z.json"))
            os.environ["TD_FILE"] = "rel.json"
            self.assertEqual(td.resolve_path(), pathlib.Path("rel.json"))
            os.environ["TD_FILE"] = "/other.json"
            self.assertEqual(td.resolve_path(), pathlib.Path("/other.json"))

    def test_temp_env_restores(self):
        for home, tdfile in (("/h", "/f"), (None, None)):
            with mock.patch.dict(os.environ):
                for key, val in (("HOME", home), ("TD_FILE", tdfile)):
                    if val is None:
                        os.environ.pop(key, None)
                    else:
                        os.environ[key] = val
                with helpers.temp_env():
                    self.assertIn("TD_FILE", os.environ)
                self.assertEqual(os.environ.get("HOME"), home)
                self.assertEqual(os.environ.get("TD_FILE"), tdfile)

    def test_tests_import_only_stdlib(self):
        here = pathlib.Path(__file__).parent
        for src in list(here.glob("*.py")) + [helpers.TD_PATH]:
            for node in ast.walk(ast.parse(src.read_text(encoding="utf-8"))):
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    names = [node.module]
                for name in names:
                    top = name.split(".")[0]
                    self.assertTrue(top in sys.stdlib_module_names or top == "helpers", (src.name, name))


class ConstantsTest(unittest.TestCase):  # criterion 2
    def test_names_defined_once(self):
        tree = ast.parse(helpers.TD_PATH.read_text(encoding="utf-8"))
        hits = [n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)
                and ("TD_FILE" in n.value or ".td.json" in n.value)]
        self.assertEqual(sorted(hits), ["TD_FILE", "~/.td.json"])
        self.assertEqual(td.ENV_VAR, "TD_FILE")
        self.assertEqual(td.DEFAULT_FILE, "~/.td.json")


class ParentTest(unittest.TestCase):  # criterion 3, 4
    def test_bad_locations(self):
        with helpers.temp_env() as tmp:
            blocker = os.path.join(tmp, "plain")
            write(blocker, "x")
            os.mkdir(os.path.join(tmp, "adir"))
            cases = {
                "missing parent": os.path.join(tmp, "nodir", "f.json"),
                "parent is file": os.path.join(blocker, "f.json"),
                "path is dir": os.path.join(tmp, "adir"),
            }
            for name, path in cases.items():
                for fn in (lambda p: td.load_store(p), lambda p: td.save_store(p, store_of())):
                    with self.subTest(name):
                        with self.assertRaises(td.TdError) as cm:
                            fn(path)
                        self.assertEqual(cm.exception.exit_code, 1)
                        self.assertIn(path, str(cm.exception))
            self.assertFalse(os.path.exists(os.path.join(tmp, "nodir")))

    def test_missing_file_is_empty_and_creates_nothing(self):
        with helpers.temp_env() as tmp:
            before = os.listdir(tmp)
            self.assertEqual(td.load_store(os.path.join(tmp, "tasks.json")),
                             {"version": 1, "next_id": 1, "tasks": []})
            self.assertEqual(os.listdir(tmp), before)

    def test_dangling_symlink(self):
        with helpers.temp_env() as tmp:
            link = os.path.join(tmp, "link.json")
            os.symlink(os.path.join(tmp, "gone", "t.json"), link)
            self.assertEqual(td.load_store(link)["tasks"], [])
            with self.assertRaises(td.TdError) as cm:
                td.save_store(link, store_of())
            self.assertIn(link, str(cm.exception))


class RoundTripTest(unittest.TestCase):  # criterion 5, 7
    def test_round_trip(self):
        with helpers.temp_env() as tmp:
            path = os.path.join(tmp, "tasks.json")
            s = store_of(task(1, "naïve café"), task(2, "a\nb", True))
            td.save_store(path, s)
            self.assertEqual(td.load_store(path), s)
            raw = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
            self.assertEqual(set(raw), {"version", "next_id", "tasks"})
            for t in raw["tasks"]:
                self.assertEqual(set(t), {"id", "text", "done"})

    @unittest.skipUnless(os.name == "posix", "umask modes are posix only")
    def test_mode_follows_umask(self):
        with helpers.temp_env() as tmp:
            for mask, mode in ((0o022, 0o644), (0o077, 0o600)):
                path = os.path.join(tmp, f"m{mask}.json")
                old = os.umask(mask)
                try:
                    td.save_store(path, store_of())
                finally:
                    os.umask(old)
                self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), mode)

    def test_fixture(self):
        s = td.load_store(FIXTURE)
        self.assertEqual(s, {"version": 1, "next_id": 5, "tasks": [
            task(1, "first", True), task(3, "naïve café"), task(4, "x", True)]})
        self.assertEqual(td.add_task(s, "new")["id"], 5)


class CorruptTest(unittest.TestCase):  # criterion 6
    def test_corrupt_inputs(self):
        good = {"version": 1, "next_id": 3, "tasks": [task(1), task(2)]}

        def j(**kw):
            d = json.loads(json.dumps(good))
            d.update(kw)
            return json.dumps(d)

        def with_task(t):
            return json.dumps({"version": 1, "next_id": 3, "tasks": [t]})

        cases = [
            ("invalid json", b"{not json", None),
            ("empty", b"", None),
            ("bad utf8", b"\xff\xfe\x00", None),
            ("array", b"[]", None),
            ("missing key", json.dumps({"version": 1, "next_id": 1}), "'tasks'"),
            ("extra key", j(extra=1), "'extra'"),
            ("version 2", j(version=2), "'version'"),
            ("version 0", j(version=0), "'version'"),
            ("version true", j(version=True), "'version'"),
            ("next_id str", j(next_id="3"), "'next_id'"),
            ("next_id 0", j(next_id=0), "'next_id'"),
            ("tasks object", j(tasks={}), "'tasks'"),
            ("task missing key", with_task({"id": 1, "text": "a"}), "'done'"),
            ("task extra key", with_task({"id": 1, "text": "a", "done": False, "x": 1}), "'x'"),
            ("text number", with_task({"id": 1, "text": 5, "done": False}), "'text'"),
            ("done int", with_task({"id": 1, "text": "a", "done": 1}), "'done'"),
            ("id bool", with_task({"id": True, "text": "a", "done": False}), "'id'"),
            ("dup ids", json.dumps({"version": 1, "next_id": 3, "tasks": [task(1), task(1)]}), "'id'"),
            ("version -1", j(version=-1), "'version'"),
            ("next_id -1", j(next_id=-1), "'next_id'"),
            ("id 0", with_task({"id": 0, "text": "a", "done": False}), "'id'"),
            ("id -1", with_task({"id": -1, "text": "a", "done": False}), "'id'"),
            ("nesting too deep", "[" * 200000, None),
            # round 3 B3: no tasks, so only the positivity check can reject these (the next_id <= id check cannot fire)
            ("next_id 0, no tasks", json.dumps({"version": 1, "next_id": 0, "tasks": []}), "'next_id'"),
            ("next_id -1, no tasks", json.dumps({"version": 1, "next_id": -1, "tasks": []}), "'next_id'"),
            ("duplicate top-level key", '{"version": 1, "version": 1, "next_id": 1, "tasks": []}', "duplicate key 'version'"),
            ("duplicate task key", '{"version": 1, "next_id": 3, "tasks": [{"id": 1, "id": 2, "text": "a", "done": false}]}', "duplicate key 'id'"),
            ("next_id = max id", json.dumps({"version": 1, "next_id": 2, "tasks": [task(1), task(2)]}), "'next_id'"),
        ]
        with helpers.temp_env() as tmp:
            path = os.path.join(tmp, "tasks.json")
            for name, content, key in cases:
                with self.subTest(name):
                    data = content.encode("utf-8") if isinstance(content, str) else content
                    write(path, data)
                    with self.assertRaises(td.TdError) as cm:
                        td.load_store(path)
                    self.assertEqual(cm.exception.exit_code, 1)
                    self.assertTrue(str(cm.exception).startswith(path))
                    if key:
                        self.assertIn(key, str(cm.exception))
                    if name == "invalid json":
                        try:
                            json.loads(data.decode())
                        except ValueError as exc:
                            self.assertIn(str(exc), str(cm.exception))
                    self.assertEqual(pathlib.Path(path).read_bytes(), data)


class IdTest(unittest.TestCase):  # criterion 8
    def test_ids(self):
        s = store_of(task(1), task(2))
        td.remove_task(s, 2)
        self.assertEqual(td.add_task(s, "n")["id"], 3)
        self.assertEqual(s["next_id"], 4)
        with helpers.temp_env() as tmp:
            path = os.path.join(tmp, "tasks.json")
            td.save_store(path, s)
            self.assertEqual(td.load_store(path)["next_id"], 4)
        s = store_of(task(1), task(2), task(3))
        self.assertEqual(td.add_task(s, "n")["id"], 4)

    def test_remove_all_then_add(self):
        s = store_of(task(1), task(2))
        td.remove_task(s, 1)
        td.remove_task(s, 2)
        self.assertEqual(td.add_task(s, "n")["id"], 3)

    def test_next_id_far_above_highest_after_remove_all(self):  # follow-up F4
        s = store_of(task(1), task(2), next_id=50)
        td.remove_task(s, 1)
        td.remove_task(s, 2)
        self.assertEqual(td.add_task(s, "n")["id"], 50)
        self.assertEqual(s["next_id"], 51)

    def test_missing_id(self):
        s = store_of(task(1))
        for fn in (td.find_task, td.remove_task):
            with self.assertRaises(td.TdError) as cm:
                fn(s, 7)
            self.assertEqual(str(cm.exception), "no task with id 7")
            self.assertEqual(cm.exception.exit_code, 1)

    def test_clear_done(self):
        s = store_of(task(1, done=True), task(2), task(3, done=True), next_id=9)
        self.assertEqual(td.clear_done(s), 2)
        self.assertEqual(s["tasks"], [task(2)])
        self.assertEqual(s["next_id"], 9)
        self.assertEqual(td.clear_done(s), 0)


CHILD = r"""
import importlib.machinery, importlib.util, json, os, stat, sys
loader = importlib.machinery.SourceFileLoader("td", sys.argv[1])
spec = importlib.util.spec_from_loader("td", loader)
td = importlib.util.module_from_spec(spec); loader.exec_module(td)
point = sys.argv[3]
real_fsync, real_replace = os.fsync, os.replace
def fsync(fd):
    is_dir = stat.S_ISDIR(os.fstat(fd).st_mode)
    if not is_dir and point == "before_temp_fsync": os._exit(9)
    if is_dir and point == "after_replace": os._exit(9)
    return real_fsync(fd)
def replace(a, b):
    if point == "before_replace": os._exit(9)
    return real_replace(a, b)
os.fsync, os.replace = fsync, replace
td.save_store(sys.argv[2], json.loads(sys.argv[4]))
"""

POINTS = ("before_temp_fsync", "before_replace", "after_replace")
OLD = store_of(task(1, "old"))
NEW = store_of(task(1, "old"), task(2, "new"))
EMPTY = {"version": 1, "next_id": 1, "tasks": []}


class KillTest(unittest.TestCase):  # criterion 9
    def test_subprocess_kill(self):
        for point in POINTS:
            for had_previous in (True, False):
                with self.subTest(point=point, previous=had_previous), helpers.temp_env() as tmp:
                    path = os.path.join(tmp, "tasks.json")
                    if had_previous:
                        td.save_store(path, OLD)
                    r = subprocess.run([sys.executable, "-c", CHILD, str(helpers.TD_PATH), path, point, json.dumps(NEW)],
                                       capture_output=True)
                    self.assertEqual(r.returncode, 9, r.stderr)
                    previous = OLD if had_previous else EMPTY
                    expected = NEW if point == "after_replace" else previous
                    self.assertEqual(td.load_store(path), expected)
                    if not had_previous and point != "after_replace":
                        self.assertFalse(os.path.exists(path))

    def _inject(self, point, exc):
        real_fsync, real_replace = os.fsync, os.replace

        def fsync(fd):
            is_dir = stat.S_ISDIR(os.fstat(fd).st_mode)
            if (not is_dir and point == "before_temp_fsync") or (is_dir and point == "after_replace"):
                raise exc
            return real_fsync(fd)

        def replace(a, b):
            if point == "before_replace":
                raise exc
            return real_replace(a, b)

        return mock.patch.multiple(os, fsync=fsync, replace=replace)

    def test_injected_errors(self):
        for point in POINTS:
            for had_previous in (True, False):
                for exc in (OSError("boom"), KeyError("boom")):
                    with self.subTest(point=point, previous=had_previous, exc=type(exc).__name__), \
                            helpers.temp_env() as tmp:
                        path = os.path.join(tmp, "tasks.json")
                        if had_previous:
                            td.save_store(path, OLD)
                        before = os.listdir(tmp)
                        with self._inject(point, exc):
                            if point == "after_replace" and isinstance(exc, OSError):
                                td.save_store(path, NEW)  # directory fsync OSError is skipped
                            elif isinstance(exc, OSError):
                                with self.assertRaises(td.TdError) as cm:
                                    td.save_store(path, NEW)
                                self.assertIn(path, str(cm.exception))
                            else:
                                with self.assertRaises(KeyError):
                                    td.save_store(path, NEW)
                        previous = OLD if had_previous else EMPTY
                        expected = NEW if point == "after_replace" else previous
                        self.assertEqual(td.load_store(path), expected)
                        if point != "after_replace":
                            self.assertEqual(sorted(os.listdir(tmp)), sorted(before))  # criterion 10


class TempFileTest(unittest.TestCase):  # follow-up F3: O_EXCL on the temp file
    def test_existing_temp_name_is_not_clobbered(self):
        with helpers.temp_env() as tmp:
            path = os.path.join(tmp, "tasks.json")
            td.save_store(path, OLD)
            fixed = mock.Mock(hex="f" * 32)
            tmp_path = os.path.join(tmp, ".tasks.json." + "f" * 32 + ".tmp")
            write(tmp_path, b"precious")
            with mock.patch.object(td.uuid, "uuid4", return_value=fixed):
                with self.assertRaises(td.TdError) as cm:
                    td.save_store(path, NEW)
            self.assertTrue(str(cm.exception).startswith(path))
            self.assertEqual(td.load_store(path), OLD)


class OversizedSaveTest(unittest.TestCase):  # follow-up F5
    def test_oversized_next_id_is_tderror(self):
        with helpers.temp_env() as tmp:
            path = os.path.join(tmp, "tasks.json")
            big = {"version": 1, "next_id": 10 ** 5000, "tasks": []}
            with self.assertRaises(td.TdError) as cm:
                td.save_store(path, big)
            self.assertTrue(str(cm.exception).startswith(path))
            self.assertFalse(os.path.exists(path))


class StrayAndSymlinkTest(unittest.TestCase):  # criteria 10, 11
    def test_stray_file_untouched(self):
        with helpers.temp_env() as tmp:
            path = os.path.join(tmp, "tasks.json")
            stray = os.path.join(tmp, ".tasks.json.dead.tmp")
            write(stray, "junk")
            self.assertEqual(td.load_store(path), EMPTY)
            td.save_store(path, NEW)
            self.assertEqual(td.load_store(path), NEW)
            self.assertEqual(pathlib.Path(stray).read_bytes(), b"junk")

    def test_symlinks_survive_save(self):
        for kind in ("absolute", "relative", "chain"):
            with self.subTest(kind), helpers.temp_env() as tmp:
                real_dir = os.path.join(tmp, "real")
                os.mkdir(real_dir)
                real = os.path.join(real_dir, "data.json")
                link = os.path.join(tmp, "link.json")
                if kind == "absolute":
                    os.symlink(real, link)
                elif kind == "relative":
                    os.symlink(os.path.join("real", "data.json"), link)
                else:
                    mid = os.path.join(tmp, "mid.json")
                    os.symlink(real, mid)
                    os.symlink("mid.json", link)
                td.save_store(link, NEW)
                self.assertTrue(os.path.islink(link))
                self.assertEqual(td.load_store(real), NEW)
                self.assertEqual(td.load_store(link), NEW)


class FsyncOrderTest(unittest.TestCase):  # criterion 12
    def test_order(self):
        calls = []
        sizes = []  # size of the temp file on disk at the moment it is fsynced (BUG-REPORT-001 item 4)
        real_fsync, real_replace = os.fsync, os.replace

        def fsync(fd):
            is_dir = stat.S_ISDIR(os.fstat(fd).st_mode)
            if not is_dir:
                sizes.append(os.fstat(fd).st_size)
            calls.append("dir_fsync" if is_dir else "temp_fsync")
            return real_fsync(fd)

        def replace(a, b):
            calls.append("replace")
            return real_replace(a, b)

        with helpers.temp_env() as tmp, mock.patch.multiple(os, fsync=fsync, replace=replace):
            path = os.path.join(tmp, "tasks.json")
            td.save_store(path, NEW)
            with open(path, "rb") as f:
                final_size = len(f.read())
        self.assertEqual(calls, ["temp_fsync", "replace", "dir_fsync"])
        # why: an fsync of an empty or half-written file keeps the call order right and protects nothing
        self.assertGreater(final_size, 0)
        self.assertEqual(sizes, [final_size])

    def test_directory_open_failure_skipped(self):
        real_open = os.open
        with helpers.temp_env() as tmp:
            def fake_open(p, flags, *a, **k):
                if os.fspath(p) == os.path.realpath(tmp):
                    raise OSError("no dir open")
                return real_open(p, flags, *a, **k)

            path = os.path.join(tmp, "tasks.json")
            with mock.patch.object(os, "open", fake_open):
                td.save_store(path, NEW)
            self.assertEqual(td.load_store(path), NEW)

    def test_other_exception_from_directory_fsync_propagates(self):
        real_fsync = os.fsync

        def fsync(fd):
            if stat.S_ISDIR(os.fstat(fd).st_mode):
                raise ValueError("x")
            return real_fsync(fd)

        with helpers.temp_env() as tmp:
            with mock.patch.object(os, "fsync", fsync), self.assertRaises(ValueError):
                td.save_store(os.path.join(tmp, "tasks.json"), NEW)


class InvalidSaveTest(unittest.TestCase):  # criterion 13
    def test_invalid_store_rejected(self):
        with helpers.temp_env() as tmp:
            path = os.path.join(tmp, "tasks.json")
            td.save_store(path, OLD)
            raw = pathlib.Path(path).read_bytes()
            before = os.listdir(tmp)
            bad = [dict(OLD, next_id="2"), {"version": 1, "next_id": 5, "tasks": [task(1), task(1)]}]
            for store in bad:
                with self.assertRaises(td.TdError):
                    td.save_store(path, store)
                self.assertEqual(pathlib.Path(path).read_bytes(), raw)
                self.assertEqual(os.listdir(tmp), before)

    def test_invalid_store_reported_before_missing_directory(self):
        with helpers.temp_env() as tmp:
            with self.assertRaises(td.TdError) as cm:
                td.save_store(os.path.join(tmp, "nodir", "f.json"), dict(OLD, next_id="2"))
            self.assertIn("'next_id'", str(cm.exception))


class ErrorClassTest(unittest.TestCase):  # criterion 14
    def test_errors(self):
        self.assertEqual(td.TdError("m").exit_code, 1)
        self.assertEqual(str(td.TdError("m")), "m")
        self.assertEqual(td.TdError("m", 2).exit_code, 2)
        self.assertIsInstance(td.UsageError("m"), td.TdError)
        self.assertEqual(td.UsageError("m").exit_code, 2)


if __name__ == "__main__":
    unittest.main()
