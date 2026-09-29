#!/usr/bin/env python3
"""Write test outcomes back into the approved test design CSV.

Keeps docs/ut-design/unit-test-design.csv the living record of the suite:

  * a case that passed  -> Actual Output = "Pass",  Automated = "Yes"
  * a case that failed  -> Actual Output = "Fail",  Automated = "Yes"
  * a case skipped with a ``// TC-SKIP: <ID> <reason>`` comment
                        -> Actual Output = "Skipped: <reason>", Automated = "No"

Outcomes come from run_tests.py (invoked unless --results is given) and from
scanning tests/ for TC-SKIP markers. All other columns are preserved verbatim.

Usage:
    python3 update_results.py [--root DIR] [--design PATH] [--results FILE] [--dry-run]

Exit codes: 0 = updated, 1 = input error, 2 = usage error.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_traceability import scan_tests  # noqa: E402

SKIP_RE = re.compile(r"TC-SKIP:\s*(\S+)\s*(.*)")


def skip_reasons(tests_dir: Path) -> dict[str, str]:
    reasons: dict[str, str] = {}
    for path in sorted(tests_dir.glob("*.cpp")):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            m = SKIP_RE.search(line)
            if m:
                reasons[m.group(1)] = m.group(2).strip() or "deferred"
    return reasons


def load_results(root: Path, results_file: Path | None) -> dict:
    if results_file is not None:
        return json.loads(results_file.read_text(encoding="utf-8"))
    script = Path(__file__).resolve().parent / "run_tests.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--root", str(root), "--json"],
        capture_output=True,
        text=True,
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        print("error: could not parse run_tests.py output", file=sys.stderr)
        print(proc.stdout, file=sys.stderr)
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Record test outcomes in the design CSV.")
    parser.add_argument("--root", default=".", help="project root (default: .)")
    parser.add_argument("--design", default=None, help="design CSV path")
    parser.add_argument("--results", default=None, help="run_tests.py --json output file")
    parser.add_argument("--dry-run", action="store_true", help="preview without writing")
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

    results = load_results(root, Path(args.results) if args.results else None)
    passed = set(results.get("passed", []))
    failed = set(results.get("failed", []))
    skipped = skip_reasons(tests_dir)

    with design.open(newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))
    if not rows:
        print("error: design CSV is empty", file=sys.stderr)
        return 1

    header, body = rows[0], rows[1:]
    try:
        actual_idx = header.index("Actual Output")
        auto_idx = header.index("Automated (Yes/No)")
    except ValueError:
        print("error: design CSV is missing the Actual Output / Automated columns", file=sys.stderr)
        return 1

    changed = 0
    for row in body:
        if not row or not row[0].strip():
            continue
        cid = row[0].strip()
        if cid in passed:
            new_actual, new_auto = "Pass", "Yes"
        elif cid in failed:
            new_actual, new_auto = "Fail", "Yes"
        elif cid in skipped:
            new_actual, new_auto = f"Skipped: {skipped[cid]}", "No"
        else:
            continue
        if row[actual_idx] != new_actual or row[auto_idx] != new_auto:
            row[actual_idx] = new_actual
            row[auto_idx] = new_auto
            changed += 1

    if args.dry_run:
        print(f"would update {changed} row(s) in {design}")
        return 0

    with design.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(body)

    print(f"updated {changed} row(s) in {design}")
    return 0


if __name__ == "__main__":
    sys.exit(main())