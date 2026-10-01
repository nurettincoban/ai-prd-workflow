"""Tests for trace-check.py. Run from the repo root:  python3 -m unittest discover scripts"""
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent / "trace-check.py"


def project(files):
    root = Path(tempfile.mkdtemp())
    for name, content in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(content).lstrip(), encoding="utf-8")
    return root


def run(root):
    result = subprocess.run([sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True, encoding="utf-8")
    return result.returncode, result.stdout


CLEAN = {
    "PRD.md": """
        # PRD
        ## Product Type
        service/API -- skipped: accessibility, responsive design (no UI)
        ## Functional Requirements
        - **FR-1**: Create a short link
        - **FR-2**: Redirect to the original URL
        ## Non-Functional Requirements
        - **NFR-1**: Redirect p95 below 100 ms
        - **NFR-2**: Validate all input
        """,
    "PRD-REVIEW.md": "# Review\n",
    "FEATURES.md": """
        # Features
        ## Links
        | ID | Feature | Priority | Source | Complexity | Acceptance Criteria |
        |----|---------|----------|--------|------------|---------------------|
        | F1 | Create link | Must | FR-1 | Low | returns a code |
        | F2 | Redirect | Must | FR-2, NFR-1 | Low | p95 < 100 ms |
        | F3 | QR codes | Won't | -- | Low | -- |
        """,
    "RULES.md": """
        # Rules
        - **SEC-1**: Validate all input (NFR-2)
        - **ARCH-1**: Layered architecture
        """,
    "RFCs/RFC-001-Core.md": """
        # RFC-001: Core
        **Features**: F1
        **Depends on**: none
        **Rules**: ARCH-1, SEC-1
        """,
    "RFCs/RFC-002-Redirect.md": """
        # RFC-002: Redirect
        **Features**: F2
        **Depends on**: RFC-001
        **Rules**: SEC-1
        """,
    "RFCS.md": """
        | RFC | Title | Depends on | Status |
        |-----|-------|------------|--------|
        | RFC-001 | Core | none | Reviewed -- PASS |
        | RFC-002 | Redirect | RFC-001 | Not started |
        """,
    "TEST-STRATEGY.md": "## RFC-001: Core\n",
    "reviews/REVIEW-RFC-001.md": "# Review of RFC-001\n",
}


class TraceCheckTest(unittest.TestCase):
    def test_consistent_project_passes(self):
        code, out = run(project(CLEAN))
        self.assertEqual(code, 0, out)
        self.assertIn("0 failure(s), 0 warning(s)", out)

    def test_no_prd_is_not_an_error(self):
        code, out = run(project({"README.md": "hi"}))
        self.assertEqual(code, 0, out)
        self.assertIn("nothing to check", out)

    def test_every_seeded_defect_is_reported(self):
        files = dict(CLEAN)
        files["PRD.md"] += "- **FR-3**: List links\n- **FR-3**: Duplicate definition\n"
        files["FEATURES.md"] += "| F4 | Orphan | Must | FR-1 | Low | x |\n| F5 | Bad source | Should | FR-9 | Low | x |\n| F2 | Duplicate | Could | FR-2 | Low | x |\n"
        files["RULES.md"] += "- **ARCH-1**: Duplicate rule\n"
        files["RFCs/RFC-001-Core.md"] = "**Features**: F1, F9\n**Depends on**: RFC-002\n**Rules**: SEC-7\n"
        files["RFCs/RFC-003-Nodeps.md"] = "**Features**: F2\n"
        files["RFCS.md"] = "| RFC | Status |\n|---|---|\n| RFC-001 | Reviewed |\n| RFC-002 | Implemented |\n| RFC-004 | Not started |\n"
        del files["reviews/REVIEW-RFC-001.md"]
        code, out = run(project(files))
        self.assertEqual(code, 1, out)
        for expected in [
            "FAIL  PRD.md: requirement FR-3 is defined 2 times",
            "FAIL  FR-3 (PRD.md) is not covered by any feature",
            "FAIL  FEATURES.md: duplicate feature ID F2",
            "FAIL  FEATURES.md: cites FR-9, which PRD.md does not define",
            "FAIL  RULES.md: rule ARCH-1 is defined 2 times",
            "FAIL  RFC-001-Core.md: cites F9, which FEATURES.md does not define",
            "FAIL  RFC-001-Core.md: cites rule SEC-7, which RULES.md does not define",
            "FAIL  RFC-001-Core.md: depends on RFC-002, which is not lower-numbered",
            "FAIL  RFC-003-Nodeps.md: no '**Depends on**:' line",
            "FAIL  F4 (Must have) is not assigned to any RFC",
            "FAIL  RFCS.md does not list RFC-003",
            "FAIL  RFCS.md lists RFC-004, which has no file in RFCs/",
            "FAIL  RFCS.md marks RFC-001 as Reviewed, but reviews/REVIEW-RFC-001.md does not exist",
            "WARN  RFC-002 is implemented but not reviewed",
        ]:
            self.assertIn(expected, out)

    def test_changes_requested_needs_a_review_record(self):
        files = dict(CLEAN)
        files["RFCS.md"] = CLEAN["RFCS.md"].replace("| RFC-002 | Redirect | RFC-001 | Not started |",
                                                    "| RFC-002 | Redirect | RFC-001 | Changes requested |")
        code, out = run(project(files))
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL  RFCS.md marks RFC-002 as Changes requested, but reviews/REVIEW-RFC-002.md does not exist", out)

    def test_scripts_parse_on_the_oldest_supported_python(self):
        import ast
        for name in ("trace-check.py", "check-prompts.py"):
            source = (SCRIPT.parent / name).read_text(encoding="utf-8")
            ast.parse(source, filename=name, feature_version=(3, 8))

    def test_removed_wont_and_implemented_features_need_no_rfc(self):
        files = dict(CLEAN)
        files["FEATURES.md"] = """
            # Features
            | ID | Feature | Priority | Source | Complexity | Acceptance Criteria | Status |
            |----|---------|----------|--------|------------|---------------------|--------|
            | F1 | Create link | Must | FR-1 | Low | returns a code | Planned |
            | F2 | Redirect | Must | FR-2, NFR-1 | Low | p95 < 100 ms | Planned |
            | F3 | QR codes | Won't | -- | Low | -- | -- |
            | F6 | Old idea [REMOVED] | Must | FR-1 | Low | -- | -- |
            | F7 | Admin page | Must | FR-1 | Low | exists | Implemented |
            """
        code, out = run(project(files))
        self.assertEqual(code, 0, out)
        for fid in ("F3", "F6", "F7"):
            self.assertNotIn(fid, out)

    def test_heading_based_priorities_from_older_feature_lists(self):
        code, out = run(project({
            "PRD.md": "# PRD\n",
            "FEATURES.md": """
                ## Must Have
                ### API
                | ID | Feature | Complexity |
                |----|---------|------------|
                | F1 | Create | Low |
                | F2 | Rate limiting | Low |
                ## Could Have
                | ID | Feature | Complexity |
                |----|---------|------------|
                | F3 | Docs | Low |
                """,
            "RULES.md": "- Use TypeScript\n",
            "RFCs/RFC-001-Core.md": "**Features**: F1\n**Builds upon**: None\n",
            "RFCS.md": "RFC-001\n",
        }))
        self.assertEqual(code, 1, out)
        self.assertIn("FAIL  F2 (Must have) is not assigned to any RFC", out)
        self.assertIn("WARN  F3 (Could have) is not assigned to any RFC", out)


if __name__ == "__main__":
    unittest.main()
