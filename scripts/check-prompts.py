#!/usr/bin/env python3
"""Consistency checks for the prompt sources. Run from the repo root:

    python3 scripts/check-prompts.py          # check
    python3 scripts/check-prompts.py --fix    # also rewrite drifted shared sections

Shared sections -- a few sections appear word for word in several prompts,
because each prompt must work on its own when pasted into a chat. Their
canonical text lives in shared/<name>.md, starting with the section's
`## HEADING`. Any prompt section with that heading must match the
canonical text exactly; --fix copies the canonical text in.

Artifact contracts -- CONTRIBUTING.md declares, between the
`contracts:start` / `contracts:end` markers, which artifacts each command
reads and writes. This script fails when:

  * a command reads an artifact that no command writes
  * a command writes an artifact that no command reads (reading only to
    report status, as /workflow-status does, does not count)
  * a prompt does not mention an artifact its row declares
  * the table and install.sh disagree about which commands exist

Each of these has shipped as a real bug at least once: a review record no
command produced, a test plan the implementer never opened, rule IDs that
were cited everywhere and created nowhere.

Versions -- install.sh's VERSION, .claude-plugin/plugin.json and the
CHANGELOG must name the same release.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHARED_DIR = ROOT / "shared"
# Headings replaced by a shared section; a prompt still using one missed a migration.
RETIRED_HEADINGS = {"SCOPE THE CHECKLIST TO THE PRODUCT TYPE"}
STATUS_ONLY = {"/workflow-status"}  # reads everything, consumes nothing
NOT_AN_ARTIFACT = {"code", "—", "-", ""}
NL = "\n"
errors = []


def read(path):
    return path.read_text(encoding="utf-8").replace("\r\n", NL)


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def artifacts(cell):
    return {a.strip().strip("`") for a in cell.split(",")} - NOT_AN_ARTIFACT


def mention(artifact):
    """The string a prompt must contain to count as referring to the artifact."""
    return artifact.rstrip("/") if artifact.endswith("/") else artifact


# ------------------------------------------------------------------ contracts
def load_contracts():
    text = read(ROOT / "CONTRIBUTING.md")
    m = re.search(r"<!-- contracts:start -->(.*?)<!-- contracts:end -->", text, re.S)
    if not m:
        sys.exit("check-prompts: no contracts table in CONTRIBUTING.md")
    rows = {}
    for line in m.group(1).strip().splitlines():
        if not line.strip().startswith("|") or re.match(r"^\s*\|\s*:?-", line):
            continue
        c = cells(line)
        if c[0].lower() == "command":
            continue
        command, prompt, reads, writes = c[0].strip("`"), c[1].strip("`"), c[2], c[3]
        rows[command] = {"prompt": prompt, "reads": artifacts(reads), "writes": artifacts(writes)}
    return rows


def load_install_commands():
    text = read(ROOT / "install.sh")
    block = re.search(r"COMMANDS='\n(.*?)\n'", text, re.S).group(1)
    return {"/" + line.split("|")[0]: line.split("|")[1] for line in block.splitlines() if line.strip()}


def check_contracts():
    rows = load_contracts()
    installed = load_install_commands()
    for cmd in sorted(set(installed) - set(rows)):
        errors.append(f"{cmd} is installed by install.sh but has no row in the CONTRIBUTING.md contracts table")
    for cmd in sorted(set(rows) - set(installed)):
        errors.append(f"{cmd} has a contracts row but install.sh does not install it")
    for cmd in sorted(set(rows) & set(installed)):
        if rows[cmd]["prompt"] != installed[cmd]:
            errors.append(f"{cmd}: contracts table says {rows[cmd]['prompt']}, install.sh says {installed[cmd]}")

    writers, readers = {}, {}
    for cmd, row in rows.items():
        for a in row["writes"]:
            writers.setdefault(a, set()).add(cmd)
        for a in row["reads"]:
            readers.setdefault(a, set()).add(cmd)

    for a, who in sorted(readers.items()):
        if a not in writers:
            errors.append(f"{a} is read by {', '.join(sorted(who))} but no command writes it")
    for a, who in sorted(writers.items()):
        consumers = readers.get(a, set()) - STATUS_ONLY
        if not consumers:
            errors.append(f"{a} is written by {', '.join(sorted(who))} but no command reads it (beyond status reporting)")

    for cmd, row in sorted(rows.items()):
        path = ROOT / row["prompt"]
        if not path.exists():
            errors.append(f"{cmd}: prompt file {row['prompt']} does not exist")
            continue
        text = read(path)
        for a in sorted(row["reads"] | row["writes"]):
            if mention(a) not in text:
                errors.append(f"{row['prompt']} never mentions {a}, which its contracts row declares")


# ------------------------------------------------------------ shared sections
def prompt_files():
    rows = load_contracts()
    return sorted({ROOT / row["prompt"] for row in rows.values() if (ROOT / row["prompt"]).exists()})


def sections(lines):
    """[(HEADING, start, end)] for every level-2 section; end is exclusive."""
    starts = [i for i, line in enumerate(lines) if line.startswith("## ")]
    ends = starts[1:] + [len(lines)]
    return [(lines[s][3:].strip().upper(), s, e) for s, e in zip(starts, ends)]


def check_shared_sections(fix):
    canon = {}
    for path in sorted(SHARED_DIR.glob("*.md")):
        text = read(path).strip()
        if not text.startswith("## "):
            errors.append(f"shared/{path.name} must start with its '## HEADING' line")
            continue
        canon[text.split(NL, 1)[0][3:].strip().upper()] = (path.name, text)

    used = set()
    for path in prompt_files():
        lines = read(path).split(NL)
        changed = False
        for key, start, end in reversed(sections(lines)):
            if key in RETIRED_HEADINGS:
                errors.append(f"{path.name}: still has the retired section '## {key}'")
            if key not in canon:
                continue
            used.add(key)
            name, want = canon[key]
            if NL.join(lines[start:end]).strip() == want:
                continue
            extra = len([l for l in lines[start:end] if l.strip()]) - len([l for l in want.split(NL) if l.strip()])
            if extra > 2:
                # More text than a drifted copy would have: the section is swallowing
                # content that belongs to the prompt. Overwriting it would delete that.
                errors.append(f"{path.name}: section '## {key}' contains {extra} lines beyond shared/{name} -- "
                              f"give that content its own '## ' heading; --fix will not overwrite it")
                continue
            if fix:
                tail = [""] if end < len(lines) else []
                lines[start:end] = want.split(NL) + tail
                changed = True
            else:
                errors.append(f"{path.name}: section '## {key}' differs from shared/{name} (run with --fix)")
        if changed:
            text = NL.join(lines)
            path.write_text(text if text.endswith(NL) else text + NL, encoding="utf-8", newline=NL)
            print(f"fixed shared sections in {path.name}")
    for key, (name, _) in sorted(canon.items()):
        if key not in used:
            errors.append(f"shared/{name} is not used by any prompt")


def check_versions():
    m = re.search(r'^VERSION="([^"]+)"', read(ROOT / "install.sh"), re.M)
    if not m:
        errors.append("install.sh has no VERSION=\"x.y.z\" line")
        return
    version = m.group(1)
    plugin = json.loads(read(ROOT / ".claude-plugin" / "plugin.json")).get("version")
    if plugin != version:
        errors.append(f"plugin.json says version {plugin}, install.sh says {version}")
    if f"## [{version}]" not in read(ROOT / "CHANGELOG.md"):
        errors.append(f"CHANGELOG.md has no '## [{version}]' entry")


def main():
    fix = "--fix" in sys.argv[1:]
    check_contracts()
    check_shared_sections(fix)
    check_versions()
    if errors:
        for e in errors:
            print(f"FAIL  {e}")
        print(f"check-prompts: {len(errors)} problem(s)")
        return 1
    print("check-prompts: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
