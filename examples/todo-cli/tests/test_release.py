"""Release checks (RFC-005): whole-program constraints on td, the install, speed and the nested suite run."""
import ast
import json
import os
import pathlib
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
import unittest

import helpers

ROOT = helpers.TD_PATH.parent
TESTS_DIR = ROOT / "tests"
FIXTURE = TESTS_DIR / "fixtures" / "v1.json"
# assumption: RFC-005 "implementer's choice": the nested run sets this so it skips criteria 5 and 6 itself
SKIP_VAR = "TD_RELEASE_NESTED"

BANNED_IMPORTS = {
    "socket", "ssl", "http", "urllib", "ftplib", "smtplib", "xmlrpc", "asyncio", "subprocess",
    "pickle", "importlib", "ctypes", "threading", "multiprocessing",
}
BANNED_NAMES = {"system", "popen", "eval", "exec", "__import__"}


def parse(path):
    return ast.parse(pathlib.Path(path).read_text(encoding="utf-8"), filename=str(path))


def top_imports(tree):
    """Return the top-level module name of every import in tree."""
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.append(node.module.split(".")[0])
    return names


def test_files():
    return sorted(TESTS_DIR.glob("*.py"))


class StaticChecks(unittest.TestCase):
    def test_1_imports_are_stdlib(self):
        for name in top_imports(parse(helpers.TD_PATH)):
            self.assertIn(name, sys.stdlib_module_names, f"td imports non-stdlib {name}")
        local = {p.stem for p in test_files()}
        for path in test_files():
            for name in top_imports(parse(path)):
                self.assertTrue(name in sys.stdlib_module_names or (name in local and name == "helpers"),
                                f"{path.name} imports {name}")
            self.assertNotIn(path.stem, sys.stdlib_module_names, f"{path.name} shadows a stdlib module")

    def test_2_no_banned_imports_or_names(self):
        tree = parse(helpers.TD_PATH)
        for name in top_imports(tree):
            self.assertNotIn(name, BANNED_IMPORTS)
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                self.assertNotIn(node.id, BANNED_NAMES)
            elif isinstance(node, ast.Attribute):
                self.assertNotIn(node.attr, BANNED_NAMES)
            elif isinstance(node, ast.alias):
                self.assertNotIn(node.name.split(".")[-1], BANNED_NAMES)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                self.assertNotIn(node.value, BANNED_NAMES)

    def test_7_syntax_floor(self):
        for path in [helpers.TD_PATH] + test_files():
            source = path.read_text(encoding="utf-8")
            try:
                ast.parse(source, filename=str(path), feature_version=(3, 10))
            except SyntaxError as exc:
                self.fail(f"{path.name} is not valid Python 3.10 syntax: {exc}")

    def test_9_no_path_separators(self):
        tree = parse(helpers.TD_PATH)
        exempt = set()
        default_file = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                body = node.body
                if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                        and isinstance(body[0].value.value, str):
                    exempt.add(id(body[0].value))
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "DEFAULT_FILE"
                                                    for t in node.targets):
                default_file = node.value
        self.assertIsNotNone(default_file, "DEFAULT_FILE not found")
        exempt.add(id(default_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in exempt:
                self.assertNotIn("/", node.value, f"line {node.lineno}")
                self.assertNotIn("\\", node.value, f"line {node.lineno}")
            if isinstance(node, ast.Attribute) and node.attr in ("sep", "altsep"):
                self.fail(f"line {node.lineno}: separator attribute {node.attr}")


class InstalledProgram(unittest.TestCase):
    """Runs a copy of td alone, found by bare name on PATH."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.bin = os.path.join(self.tmp.name, "bin")
        os.mkdir(self.bin)
        installed = os.path.join(self.bin, "td")
        shutil.copyfile(helpers.TD_PATH, installed)
        os.chmod(installed, 0o755)
        self.data = os.path.join(self.tmp.name, "data.json")
        self.env = dict(os.environ)
        self.env.update(TD_FILE=self.data, PYTHONUTF8="1", PYTHONIOENCODING="utf-8",
                        PATH=self.bin + os.pathsep + os.environ.get("PATH", ""))

    def td(self, *args):
        return subprocess.run(["td", *args], env=self.env, capture_output=True, text=True,
                              encoding="utf-8", timeout=60)

    def test_3_install_check(self):
        self.assertEqual(os.listdir(self.bin), ["td"])
        result = self.td("add", "x")
        self.assertEqual((result.stdout, result.returncode), ("1 [ ] x\n", 0), result.stderr)
        result = self.td("list")
        self.assertEqual((result.stdout, result.returncode), ("1 [ ] x\n", 0), result.stderr)

    def test_4_fixture_check(self):
        shutil.copyfile(FIXTURE, self.data)
        original = json.loads(FIXTURE.read_text(encoding="utf-8"))
        result = self.td("list")
        self.assertEqual(result.stdout, "1 [x] first\n3 [ ] naïve café\n4 [x] x\n", result.stderr)
        self.assertEqual(result.returncode, 0)
        result = self.td("add", "y")
        self.assertEqual((result.stdout, result.returncode), ("5 [ ] y\n", 0), result.stderr)
        with open(self.data, encoding="utf-8") as handle:
            stored = json.load(handle)
        self.assertEqual(stored["tasks"][:3], original["tasks"])

    @unittest.skipIf(os.environ.get(SKIP_VAR), "nested run")
    def test_5_speed_check(self):
        store = {"version": 1, "next_id": 5001,
                 "tasks": [{"id": i, "text": f"{i:05d} " + "t" * 35, "done": False} for i in range(1, 5001)]}
        template = os.path.join(self.tmp.name, "template.json")
        with open(template, "w", encoding="utf-8") as handle:
            json.dump(store, handle)
        for args in (("list",), ("add", "x"), ("done", "1"), ("rm", "2")):
            times = []
            for _ in range(3):
                shutil.copyfile(template, self.data)
                start = time.perf_counter()
                result = self.td(*args)
                times.append(time.perf_counter() - start)
                self.assertEqual(result.returncode, 0, f"{args}: {result.stderr}")
            median = statistics.median(times)
            self.assertLess(median, 1.0, f"td {' '.join(args)} median {median:.3f}s")


class NestedRun(unittest.TestCase):
    @unittest.skipIf(os.environ.get(SKIP_VAR), "nested run")
    def test_6_nested_suite_run(self):
        with tempfile.TemporaryDirectory() as home:
            env = dict(os.environ)
            env.pop("TD_FILE", None)
            env.update(HOME=home, **{SKIP_VAR: "1"})
            result = subprocess.run([sys.executable, "-m", "unittest", "discover", "tests"], cwd=ROOT,
                                    env=env, capture_output=True, text=True, timeout=600)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(os.path.exists(os.path.join(home, ".td.json")))


if __name__ == "__main__":
    unittest.main()
