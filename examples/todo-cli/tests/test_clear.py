import contextlib
import io
import json
import os
import unittest

import helpers

td = helpers.load_td()


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = td.main(argv)
    return code, out.getvalue(), err.getvalue()


def write_store(tasks, next_id):
    """Write a non-canonical (4-space indent) store so a rewrite is detectable."""
    store = {"version": 1, "next_id": next_id,
             "tasks": [{"id": i, "text": s, "done": d} for i, s, d in tasks]}
    with open(os.environ["TD_FILE"], "w", encoding="utf-8") as f:
        json.dump(store, f, indent=4)


def read_raw():
    with open(os.environ["TD_FILE"], "rb") as f:
        return f.read()


MIXED = [(1, "gone", True), (2, "keep me", False), (3, "gone too", True)]


class Clear(unittest.TestCase):
    def test_c1_clear_done_only(self):
        with helpers.temp_env():
            write_store(MIXED, 4)
            self.assertEqual(run(["clear"]), (0, "", ""))
            self.assertEqual(run(["list"]), (0, "2 [ ] keep me\n", ""))

    def test_c2_next_id_kept(self):
        with helpers.temp_env():
            write_store(MIXED, 4)
            run(["clear"])
            self.assertEqual(json.loads(read_raw())["next_id"], 4)
            store = td.load_store(td.resolve_path())
            self.assertEqual(td.add_task(store, "x")["id"], 4)

    def test_c3_all_done(self):
        with helpers.temp_env():
            write_store([(1, "a", True), (2, "b", True)], 3)
            self.assertEqual(run(["clear"]), (0, "", ""))
            data = json.loads(read_raw())
            self.assertEqual((data["tasks"], data["next_id"]), ([], 3))
            self.assertEqual(run(["list"]), (0, "", ""))

    def test_c4_nothing_to_clear(self):
        with helpers.temp_env() as tmp:
            write_store([(1, "a", False)], 2)
            before = read_raw()
            self.assertEqual(run(["clear"]), (0, "", ""))
            self.assertEqual(read_raw(), before)
            self.assertEqual(os.listdir(tmp), ["tasks.json"])
        with helpers.temp_env() as tmp:
            self.assertEqual(run(["clear"]), (0, "", ""))
            self.assertEqual(os.listdir(tmp), [])

    def _check_error(self, argv, code):
        out_code, out, err = run(argv)
        self.assertEqual(out_code, code, argv)
        self.assertEqual(out, "")
        self.assertEqual(len(err.splitlines()), 1, err)
        self.assertTrue(err.startswith("td:"), err)
        return err

    def test_c5_bad_arguments(self):
        for corrupt in (False, True):
            for argv in (["clear", "extra"], ["clear", ""], ["clear", "--bogus"]):
                with helpers.temp_env():
                    if corrupt:
                        with open(os.environ["TD_FILE"], "w") as f:
                            f.write("{not json")
                    else:
                        write_store(MIXED, 4)
                    before = read_raw()
                    self._check_error(argv, 2)
                    self.assertEqual(read_raw(), before)

    def test_c6_corrupt_file(self):
        base = {"version": 1, "next_id": 2, "tasks": [{"id": 1, "text": "a", "done": True}]}
        bad = ["{not json",
               json.dumps({**base, "tasks": [{"id": 1, "text": "a", "done": 1}]}),
               json.dumps({"version": 1, "tasks": []}),
               json.dumps({**base, "version": 2}),
               "[" * 200000]
        for text in bad:
            with helpers.temp_env():
                with open(os.environ["TD_FILE"], "w") as f:
                    f.write(text)
                before = read_raw()
                err = self._check_error(["clear"], 1)
                self.assertIn(os.environ["TD_FILE"], err)
                self.assertEqual(read_raw(), before)


if __name__ == "__main__":
    unittest.main()
