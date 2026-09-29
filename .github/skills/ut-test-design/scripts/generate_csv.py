#!/usr/bin/env python3
"""Regenerate the consolidated unit-test design CSV deterministically.

The checked-in CSV is the current case source. This script re-serializes every
row with csv.writer and validates the result, preventing hand-quoting drift.
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import tempfile
from pathlib import Path

EXPECTED_HEADER = [
    "Testcase ID",
    "Testcase Name",
    "Test Description",
    "Input",
    "Testcase Type",
    "Expected Output",
    "Actual Output",
    "Automated (Yes/No)",
    "Comments",
]


def load_rows(source: Path) -> list[list[str]]:
    with source.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    if not rows or rows[0] != EXPECTED_HEADER:
        raise ValueError(f"source header must be exactly {EXPECTED_HEADER!r}")
    if any(len(row) != len(EXPECTED_HEADER) for row in rows[1:]):
        raise ValueError("source contains a row with the wrong number of columns")
    if not rows[1:]:
        raise ValueError("source contains no test cases")
    return rows[1:]


def write_csv(destination: Path, rows: list[list[str]]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(EXPECTED_HEADER)
        writer.writerows(rows)


def validate(validator: Path, destination: Path) -> None:
    result = subprocess.run(
        [sys.executable, str(validator), "--check-only", str(destination)],
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main() -> int:
    root = Path(__file__).resolve().parents[4]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=root / "docs/ut-design/unit-test-design.csv",
        help="CSV containing the test-case rows (default: generated CSV)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=root / "docs/ut-design/unit-test-design.csv",
        help="destination CSV (default: docs/ut-design/unit-test-design.csv)",
    )
    args = parser.parse_args()

    rows = load_rows(args.source)
    if args.source.resolve() == args.output.resolve():
        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8",
            suffix=".csv",
            dir=args.output.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        try:
            write_csv(temporary_path, rows)
            temporary_path.replace(args.output)
        finally:
            temporary_path.unlink(missing_ok=True)
    else:
        write_csv(args.output, rows)

    validate(root / ".github/skills/ut-test-design/scripts/validate_csv.py", args.output)
    print(f"generated {len(rows)} test cases in {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
