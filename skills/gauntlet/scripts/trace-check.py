#!/usr/bin/env python3
"""Deterministic traceability check for an ai-prd-workflow project.

Checks what a script can check reliably -- that IDs exist, that every
requirement and Must-have feature is covered, that RFC dependencies point
backwards, that the index and the review records agree with the files on
disk. Whether a reference points at the RIGHT thing is still a judgement
call for the reviewer; this only guarantees it points at SOMETHING.

Usage:  python3 trace-check.py [project-dir]
Exit:   0 = no failures (warnings allowed), 1 = at least one failure.
Needs:  Python 3.8+, standard library only.
"""
import re
import sys
from pathlib import Path

FAILS = []
WARNS = []


def fail(msg):
    FAILS.append(msg)


def warn(msg):
    WARNS.append(msg)


def read(path):
    return path.read_text(encoding="utf-8", errors="replace")


def split_row(line):
    """Cells of a markdown table row, without the outer pipes."""
    return [c.strip() for c in line.strip().strip("|").split("|")]


def is_separator(line):
    return bool(re.match(r"^\s*\|?\s*:?-{3,}", line))


def tables(text):
    """Yield (header_cells, [row_cells, ...], heading) for every markdown table."""
    lines = text.splitlines()
    heading = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("#"):
            heading = line.lstrip("#").strip()
        if line.strip().startswith("|") and i + 1 < len(lines) and is_separator(lines[i + 1]):
            header = split_row(line)
            rows = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(split_row(lines[i]))
                i += 1
            yield header, rows, heading
            continue
        i += 1


def priority_of(text):
    t = text.lower()
    if t.startswith("must"):
        return "Must"
    if t.startswith("should"):
        return "Should"
    if t.startswith("could"):
        return "Could"
    if t.startswith("won"):
        return "Won't"
    return None


# ---------------------------------------------------------------- PRD.md
def id_definitions(text, pattern):
    """(defined IDs, IDs defined more than once) for IDs matching `pattern`.

    Bullet definitions (`- **SEC-3**: ...`) win when a document has any.
    Otherwise each table's first column defines IDs. An ID repeated in a
    second table -- an index, a coverage table -- is a reference, not a
    second definition; repeated within one table, or among bullets, it is.
    """
    bullets, tables = {}, {}
    table_no, in_table = -1, False
    for line in text.splitlines():
        if line.strip().startswith("|"):
            if not in_table:
                table_no, in_table = table_no + 1, True
            m = re.match(rf"^\s*\|\s*\**({pattern})\**\s*\|", line)
            if m:
                per_table = tables.setdefault(m.group(1), {})
                per_table[table_no] = per_table.get(table_no, 0) + 1
            continue
        in_table = False
        m = re.match(rf"^\s*[-*]\s+\**({pattern})\**\b", line)
        if m:
            bullets[m.group(1)] = bullets.get(m.group(1), 0) + 1
    if bullets:
        return set(bullets), {i for i, n in bullets.items() if n > 1}
    return set(tables), {i for i, per in tables.items() if any(n > 1 for n in per.values())}


def check_prd(root):
    prd = root / "PRD.md"
    if not prd.exists():
        return set()
    text = read(prd)
    defined, duplicated = id_definitions(text, r"(?:FR|NFR)-\d+")
    for rid in sorted(duplicated):
        fail(f"PRD.md: requirement {rid} is defined more than once")
    if not defined:
        warn("PRD.md: no requirement IDs (FR-n / NFR-n), so coverage from PRD to features cannot be checked")
    elif "## Product Type" not in text and "## Product type" not in text:
        warn("PRD.md: no 'Product Type' section; downstream commands will have to re-classify the product")
    return defined


# ---------------------------------------------------------- FEATURES.md
def parse_features(text):
    """Return {feature_id: {"priority", "status", "source"}} from FEATURES.md tables."""
    features = {}
    section_priority = None
    for line in text.splitlines():
        if line.startswith("#"):
            p = priority_of(line.lstrip("#").strip())
            if p:
                section_priority = p
    for header, rows, heading in tables(text):
        cols = {h.lower(): i for i, h in enumerate(header)}
        if "id" not in cols:
            continue
        heading_priority = priority_of(heading)
        for row in rows:
            if len(row) <= cols["id"]:
                continue
            fid = re.sub(r"[*`]", "", row[cols["id"]]).strip()
            if not re.fullmatch(r"F\d+", fid):
                continue
            cell = lambda name: row[cols[name]] if name in cols and cols[name] < len(row) else ""
            prio = priority_of(cell("priority")) or heading_priority
            status = cell("status")
            removed = "[REMOVED]" in " ".join(row)
            if fid in features:
                fail(f"FEATURES.md: duplicate feature ID {fid}")
                continue
            features[fid] = {
                "priority": prio,
                "status": "removed" if removed else status.lower(),
                "source": cell("source"),
                "row": " | ".join(row),
            }
    # Old-style files group features under '## Must Have' headings; tables() already
    # carries the nearest heading, but a category heading can sit in between.
    if section_priority and any(f["priority"] is None for f in features.values()):
        current = None
        for line in text.splitlines():
            if line.startswith("#"):
                current = priority_of(line.lstrip("#").strip()) or current
            m = re.match(r"^\s*\|\s*\**(F\d+)\**\s*\|", line)
            if m and features.get(m.group(1), {}).get("priority") is None:
                features[m.group(1)]["priority"] = current
    return features


def check_features(root, prd_ids):
    path = root / "FEATURES.md"
    if not path.exists():
        return {}
    text = read(path)
    features = parse_features(text)
    if not features:
        fail("FEATURES.md: no feature tables with an ID column found")
        return {}
    for fid, f in sorted(features.items(), key=lambda kv: int(kv[0][1:])):
        if f["priority"] is None and f["status"] != "removed":
            fail(f"FEATURES.md: {fid} has no MoSCoW priority")
    mentioned = set(re.findall(r"\b(?:FR|NFR)-\d+\b", text))
    for rid in sorted(mentioned - prd_ids) if prd_ids else []:
        fail(f"FEATURES.md: cites {rid}, which PRD.md does not define")
    # Coverage counts feature rows only. A summary table listing every requirement
    # would otherwise make each one look covered, and a removed feature covers nothing.
    cited = set()
    for f in features.values():
        if f["status"] != "removed":
            cited |= set(re.findall(r"\b(?:FR|NFR)-\d+\b", f["row"]))
    if prd_ids:
        rules_text = read(root / "RULES.md") if (root / "RULES.md").exists() else ""
        for rid in sorted(prd_ids - cited, key=lambda r: (r.split("-")[0], int(r.split("-")[1]))):
            if rid.startswith("NFR") and re.search(rf"\b{rid}\b", rules_text):
                continue  # non-functional requirements are often carried by rules instead
            fail(f"{rid} (PRD.md) is not covered by any feature -- add one, or list it as Won't Have")
    return features


# -------------------------------------------------------------- RULES.md
def check_rules(root):
    path = root / "RULES.md"
    if not path.exists():
        return set()
    ids, duplicated = id_definitions(read(path), r"[A-Z][A-Z0-9]*-\d+")
    for rid in sorted(duplicated):
        fail(f"RULES.md: rule {rid} is defined more than once")
    if not ids:
        warn("RULES.md: rules have no IDs, so RFCs, reviews and change requests cannot cite them")
    return ids


# ------------------------------------------------------------------ RFCs
def field(text, *names):
    for name in names:
        m = re.search(rf"^\s*(?:[-*]\s+)?\**{name}\**\s*:\**\s*(.*)$", text, re.M | re.I)
        if m:
            return m.group(1)
    return None


def check_rfcs(root, features, rule_ids):
    folder = root / "RFCs"
    if not folder.is_dir():
        return {}
    rfcs = {}
    for path in sorted(folder.glob("RFC-*.md")):
        m = re.match(r"RFC-(\d+)", path.name)
        if not m:
            continue
        num = m.group(1)
        if num in rfcs:
            fail(f"RFCs/: two files claim RFC-{num}")
        text = read(path)
        feat_line = field(text, "Features")
        dep_line = field(text, "Depends on", "Builds upon", "Predecessors")
        rules_line = field(text, "Rules")
        if feat_line is None:
            fail(f"{path.name}: no '**Features**:' line, so its coverage cannot be traced")
        if dep_line is None:
            fail(f"{path.name}: no '**Depends on**:' line, so its predecessors are undeclared")
        rfcs[num] = {
            "file": path.name,
            "features": set(re.findall(r"\bF\d+\b", feat_line or "")),
            "deps": set(re.findall(r"RFC-(\d+)", dep_line or "")),
            "rules": set(re.findall(r"\b[A-Z][A-Z0-9]*-\d+\b", rules_line or "")) - {f"RFC-{n}" for n in re.findall(r"RFC-(\d+)", rules_line or "")},
        }
    for num, r in sorted(rfcs.items()):
        for fid in sorted(r["features"] - set(features)) if features else []:
            fail(f"{r['file']}: cites {fid}, which FEATURES.md does not define")
        for dep in sorted(r["deps"]):
            if dep not in rfcs:
                fail(f"{r['file']}: depends on RFC-{dep}, which does not exist")
            elif int(dep) >= int(num):
                fail(f"{r['file']}: depends on RFC-{dep}, which is not lower-numbered -- numbering must be a valid implementation order")
        for rid in sorted(r["rules"] - rule_ids) if rule_ids else []:
            fail(f"{r['file']}: cites rule {rid}, which RULES.md does not define")
    owners = {}
    for num, r in rfcs.items():
        for fid in r["features"]:
            owners.setdefault(fid, []).append(num)
    for fid, f in sorted(features.items(), key=lambda kv: int(kv[0][1:])):
        if f["status"] in ("removed",) or f["priority"] == "Won't" or "implemented" in f["status"]:
            continue
        if fid not in owners:
            if f["priority"] == "Must":
                fail(f"{fid} (Must have) is not assigned to any RFC")
            elif rfcs:
                warn(f"{fid} ({f['priority']} have) is not assigned to any RFC -- fine if RFCS.md defers it")
        elif len(owners[fid]) > 1:
            warn(f"{fid} is split across {', '.join('RFC-' + n for n in sorted(owners[fid]))}")
    return rfcs


# --------------------------------------------- RFCS.md, reviews, other files
def check_index(root, rfcs):
    if not rfcs:
        return
    for name in ("FEATURES.md", "RULES.md"):
        if not (root / name).exists():
            fail(f"RFCs exist but {name} does not")
    index = root / "RFCS.md"
    if not index.exists():
        fail("RFCs exist but the RFCS.md index does not")
        return
    text = read(index)
    listed = set(re.findall(r"RFC-(\d+)", text))
    for num in sorted(set(rfcs) - listed):
        fail(f"RFCS.md does not list RFC-{num}")
    for num in sorted(listed - set(rfcs)):
        fail(f"RFCS.md lists RFC-{num}, which has no file in RFCs/")
    if not (root / "TEST-STRATEGY.md").exists():
        warn("RFCs exist but TEST-STRATEGY.md does not -- run /test-strategy before implementing")
    # Status column: Implemented / Reviewed must be backed by a review record.
    for header, rows, _ in tables(text):
        cols = {h.lower(): i for i, h in enumerate(header)}
        if "status" not in cols:
            continue
        for row in rows:
            m = re.search(r"RFC-(\d+)", " ".join(row))
            if not m or cols["status"] >= len(row):
                continue
            status = row[cols["status"]].lower()
            review = root / "reviews" / f"REVIEW-RFC-{m.group(1)}.md"
            if ("review" in status or "changes requested" in status) and not review.exists():
                fail(f"RFCS.md marks RFC-{m.group(1)} as {row[cols['status']]}, but {review.relative_to(root).as_posix()} does not exist")
            elif "implemented" in status and not review.exists():
                warn(f"RFC-{m.group(1)} is implemented but not reviewed -- run /review-rfc {m.group(1)}")
    if (root / "FEATURES.md").exists() and not (root / "PRD-REVIEW.md").exists():
        warn("PRD-REVIEW.md does not exist -- was the PRD verified with /verify-prd?")


def main():
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not (root / "PRD.md").exists():
        print(f"trace-check: no PRD.md in {root} -- nothing to check yet")
        return 0
    prd_ids = check_prd(root)
    features = check_features(root, prd_ids)
    rule_ids = check_rules(root)
    rfcs = check_rfcs(root, features, rule_ids)
    check_index(root, rfcs)

    print(f"trace-check: {root}")
    print(f"  {len(prd_ids)} requirements, {len(features)} features, {len(rule_ids)} rules, {len(rfcs)} RFCs")
    for msg in FAILS:
        print(f"  FAIL  {msg}")
    for msg in WARNS:
        print(f"  WARN  {msg}")
    print(f"  {len(FAILS)} failure(s), {len(WARNS)} warning(s)")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
