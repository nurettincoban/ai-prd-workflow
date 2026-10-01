#!/usr/bin/env python3
"""Consistency checks for the prompt sources. Run from the repo root:

    python3 scripts/check-prompts.py

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
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUS_ONLY = {"/workflow-status"}  # reads everything, consumes nothing
NOT_AN_ARTIFACT = {"code", "—", "-", ""}
errors = []


def read(path):
    return path.read_text(encoding="utf-8")


def cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def artifacts(cell):
    return {a.strip().strip("`") for a in cell.split(",")} - NOT_AN_ARTIFACT


def mention(artifact):
    """The string a prompt must contain to count as referring to the artifact."""
    return artifact.rstrip("/") if artifact.endswith("/") else artifact


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


def main():
    check_contracts()
    if errors:
        for e in errors:
            print(f"FAIL  {e}")
        print(f"check-prompts: {len(errors)} problem(s)")
        return 1
    print("check-prompts: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
