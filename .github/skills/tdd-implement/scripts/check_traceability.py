#!/usr/bin/env python3
"""Traceability check for the tdd-implement skill.

Verifies that the implemented test suite and the approved test design agree:

  * every case in docs/ut-design/unit-test-design.csv is either implemented as
    a TEST_CASE with that ID, or explicitly skipped with a
    ``// TC-SKIP: <ID> <reason>`` comment;
  * no TEST_CASE in tests/ uses an ID the design does not list.

Usage:
    python3 check_traceability.py [--root DIR] [--design PATH] [--json]

Exit codes: 0 = design and suite agree, 1 = missing or extra cases, 2 = usage error.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

TEST_CASE_RE = re.compile(r'TEST_CASE\s*\(\s*"([^"]+)"')
SKIP_RE = re.compile(r"TC-SKIP:\s*(\S+)")


def read_design_ids(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return []
    ids = []
    for row in rows[1:]:
        if row and row[0].strip():
            ids.append(row[0].strip())
    return ids


def scan_tests(tests_dir: Path) -> tuple[set[str], set[str]]:
    implemented: set[str] = set()
    skipped: set[str] = set()
    for path in sorted(tests_dir.glob("*.cpp")):
        text = path.read_text(encoding="utf-8", errors="replace")
        implemented.update(TEST_CASE_RE.findall(text))
        skipped.update(SKIP_RE.findall(text))
    return implemented, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check design/test traceability.")
    parser.add_argument("--root", default=".", help="project root (default: .)")
    parser.add_argument("--design", default=None, help="design CSV path")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    design = Path(args.design) if args.design else root / "docs" / "ut-design" / "unit-test-design.csv"
    tests_dir = root / "tests"

    if not design.is_file():
        print(f"error: design CSV not found: {design}", file=sys.stderr)
        return 2
    if not tests_dir.is_dir():
        print(f"error: tests directory not found: {tests_dir}", file=sys.stderr)
        return 2

    designed = read_design_ids(design)
    implemented, skipped = scan_tests(tests_dir)

    designed_set = set(designed)
    missing = [cid for cid in designed if cid not in implemented and cid not in skipped]
    extra = sorted(implemented - designed_set)
    both = sorted(implemented & skipped)

    ok = not missing and not extra and not both
    result = {
        "status": "ok" if ok else "mismatch",
        "designed": len(designed),
        "implemented": len(implemented),
        "skipped": len(skipped),
        "missing": missing,
        "extra": extra,
        "implemented_and_skipped": both,
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"designed={len(designed)} implemented={len(implemented)} skipped={len(skipped)}")
        for cid in missing:
            print(f"MISSING  {cid} (no TEST_CASE and no TC-SKIP)")
        for cid in extra:
            print(f"EXTRA    {cid} (test not in the design)")
        for cid in both:
            print(f"CONFLICT {cid} (both implemented and skipped)")
        print("OK" if ok else "MISMATCH")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())